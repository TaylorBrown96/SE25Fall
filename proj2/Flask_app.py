import os
import re
import math
from sqlQueries import *
from datetime import timedelta
from sqlite3 import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template, url_for, redirect, request, session


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')

# Home route
@app.route('/')
def index():
    if session.get('Username') is None:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['Username'])

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = create_connection(db_file)
        user = fetch_one(conn, "SELECT * FROM User WHERE email = ?", (email,))
        close_connection(conn)
        
        if user and check_password_hash(user[5], password):
            session['Fname'] = user[1]
            session['Lname'] = user[2]
            session['Username'] = user[1] + ' ' + user[2]
            session['Email'] = user[3]
            session['Phone'] = user[4]
            session['Wallet'] = user[6]
            session['Preferences'] = user[7]

            session.permanent = True
            app.permanent_session_lifetime = timedelta(minutes=30)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('Username', None)
    session.pop('Fname', None)
    session.pop('Lname', None)
    session.pop('Email', None)
    session.pop('Phone', None)
    session.pop('Wallet', None)
    session.pop('Preferences', None)
    return redirect(url_for('login'))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # ---- Gather form fields ----
        fname = request.form.get('fname', '').strip()
        lname = request.form.get('lname', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        # Hidden CSV fields set by the page JS
        allergies = (request.form.get('allergies') or '').strip()       # e.g., "Peanuts,Milk"
        preferences = (request.form.get('preferences') or '').strip()   # e.g., "Vegan,Budget,Spicy"

        # ---- Basic validations ----
        if not fname or not lname:
            return render_template('register.html', error="First and last name are required")
        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return render_template('register.html', error="Please enter a valid email address")
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        if len(password) < 6:
            return render_template('register.html', error="Password must be at least 6 characters")

        # Normalize phone to digits only; store as-is if you prefer original formatting
        digits_only = re.sub(r"\D+", "", phone)
        if len(digits_only) < 7:  # very light sanity check
            return render_template('register.html', error="Please enter a valid phone number")

        # ---- Check existing user and insert ----
        conn = create_connection(db_file)
        try:
            existing_user = fetch_one(conn, "SELECT 1 FROM User WHERE email = ?", (email,))
            if existing_user:
                return render_template('register.html', error="Email already registered")

            password_hashed = generate_password_hash(password)

            # If your User table includes an `allergies` TEXT column (recommended), use this:
            execute_query(
                conn,
                """
                INSERT INTO User
                    (first_name, last_name, email, phone, password_HS, wallet, preferences, allergies)
                VALUES
                    (?,          ?,         ?,     ?,     ?,           ?,      ?,            ?)
                """,
                (fname, lname, email, digits_only, password_hashed, 0.0, preferences, allergies)
            )

        except IntegrityError:
            # In case there is a unique constraint on email and it triggers
            return render_template('register.html', error="Email already registered")
        finally:
            close_connection(conn)

        return redirect(url_for('login'))

    return render_template('register.html')

# Profile route
@app.route('/profile')
def profile():
    if session.get('Username') is None:
        return redirect(url_for('login'))
    return render_template('profile.html', 
                           username=session['Username'], 
                           email=session['Email'], 
                           phone=session['Phone'], 
                           wallet=session['Wallet'], 
                           preferences=session['Preferences'])

# Database viewer route
@app.route('/db')
def db_view():
    if session.get('Username') is None:
        return redirect(url_for('login'))

    # Whitelist of tables the viewer can access
    allowed_tables = {'User', 'Restaurant', 'MenuItem', 'Order', 'Review'}
    table = request.args.get('t', 'User')
    if table not in allowed_tables:
        table = 'User'

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    page = max(page, 1)
    per_page = 10

    conn = create_connection(db_file)
    cur = conn.cursor()

    # total count
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0] or 0

    # pagination
    pages = max(math.ceil(total / per_page), 1)
    page = min(page, pages)
    offset = (page - 1) * per_page

    # columns via PRAGMA
    cur.execute(f"PRAGMA table_info({table})")
    columns = [r[1] for r in cur.fetchall()]

    # fetch the rows
    cur.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (per_page, offset))
    rows = cur.fetchall()

    close_connection(conn)

    start = 0 if total == 0 else offset + 1
    end = min(offset + per_page, total)

    return render_template(
        'db_view.html',
        table=table,
        allowed=sorted(allowed_tables),
        columns=columns,
        rows=rows,
        page=page,
        pages=pages,
        total=total,
        start=start,
        end=end,
    )


if __name__ == '__main__':
    """
    DB column names:

    MenuItem: itm_id,rtr_id,name,description,price,calories,instock,restock,allergens
    Order: ord_id,rtr_id,usr_id,details,status
    Restaurant: rtr_id,name,description,phone,email,password_HS,address,city,state,zip,hours,status
    Review: rev_id,rtr_id,usr_id,title,rating,description
    User: usr_id,first_name,last_name,email,phone,password_HS,wallet,preferences
    """

    app.run(debug=True)