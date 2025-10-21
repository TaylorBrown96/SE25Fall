import os
import math
from sqlQueries import *
from datetime import timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template, url_for, redirect, request, session, jsonify, Blueprint
from flasgger import Swagger, swag_from
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-insecure")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')

Swagger(app)
# --- minimal API blueprint for documentation & testing ---
api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.get("/health")
@swag_from({
    "tags": ["meta"],
    "summary": "Health check",
    "responses": {200: {"description": "OK"}}
})
def health():
    return jsonify(status="ok")

@api_bp.get("/me")
@swag_from({
    "tags": ["user"],
    "summary": "Current user (from session)",
    "responses": {
        200: {"description": "User info"},
        401: {"description": "Not logged in"}
    }
})
def me():
    if "username" not in session:
        return jsonify(error="unauthorized"), 401
    return jsonify({
        "Fname": session.get("Fname"),
        "Lname": session.get("Lname"),
        "Wallet": session.get("Wallet"),
    })

app.register_blueprint(api_bp)

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