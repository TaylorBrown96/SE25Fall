import os
import re
import sys
import argparse
import math
import calendar
from datetime import timedelta, date
from sqlite3 import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template, url_for, redirect, request, session

# Use ONLY these helpers for DB access
from sqlQueries import create_connection, close_connection, fetch_one, fetch_all, execute_query

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')

# ---------------------- Helpers (no LLM generation here) ----------------------

def parse_generated_menu(gen_str):
    """
    New format: [YYYY-MM-DD,ID,(1|2|3)]
    Also supports old format [YYYY-MM-DD,ID] (meal defaults to 3 = Dinner).
    Returns:
      dict: { 'YYYY-MM-DD': [ {'itm_id': int, 'meal': int}, ... ] }
    """
    if not gen_str:
        return {}

    # date, id, optional meal (1,2,3)
    pairs = re.findall(r'\[\s*(\d{4}-\d{2}-\d{2})\s*,\s*([0-9]+)\s*(?:,\s*([123])\s*)?\]', gen_str)
    out = {}
    for d, mid, meal in pairs:
        try:
            itm_id = int(mid)
            meal_i = int(meal) if meal else 3  # default to Dinner for legacy entries
            out.setdefault(d, []).append({'itm_id': itm_id, 'meal': meal_i})
        except ValueError:
            continue
    return out

def palette_for_item_ids(item_ids):
    """Deterministic pleasant color per item id"""
    import colorsys
    def hsl_to_hex(h, s, l):
        r, g, b = colorsys.hls_to_rgb(h/360.0, l/100.0, s/100.0)
        return '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
    palette = {}
    for iid in item_ids:
        seed = (iid * 9301 + 49297) % 233280
        hue = seed % 360
        palette[iid] = hsl_to_hex(hue, 65, 52)
    return palette

def fetch_menu_items_by_ids(ids):
    """Returns {itm_id: {..., 'restaurant_name': str}}"""
    if not ids:
        return {}
    conn = create_connection(db_file)
    try:
        qmarks = ",".join(["?"] * len(ids))
        sql = f"""
          SELECT m.itm_id, m.rtr_id, m.name, m.description, m.price, m.calories,
                 m.allergens, r.name AS restaurant_name
          FROM MenuItem m
          JOIN Restaurant r ON r.rtr_id = m.rtr_id
          WHERE m.itm_id IN ({qmarks})
        """
        rows = fetch_all(conn, sql, tuple(ids))
    finally:
        close_connection(conn)

    out = {}
    for r in rows:
        out[r[0]] = {
            "itm_id": r[0],
            "rtr_id": r[1],
            "name": r[2],
            "description": r[3],
            "price": r[4],
            "calories": r[5],
            "allergens": r[6],
            "restaurant_name": r[7],
        }
    return out


def build_calendar_cells(gen_map, year, month, items_by_id):
    """
    gen_map: {'YYYY-MM-DD': [ {'itm_id': int, 'meal': 1|2|3}, ... ]}
    Returns cells where each day has a 'meals' list (sorted Breakfast->Dinner).
    """
    def meal_sort_key(e):
        # Breakfast(1) first, then Lunch(2), then Dinner(3)
        return e.get('meal', 3)

    palette = palette_for_item_ids(items_by_id.keys())
    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    cells = []

    for week in cal.monthdayscalendar(year, month):
        for d in week:
            if d == 0:
                cells.append({"day": 0})
                continue

            iso = f"{year:04d}-{month:02d}-{d:02d}"
            entries = sorted(gen_map.get(iso, []), key=meal_sort_key)

            meals = []
            for e in entries:
                itm = items_by_id.get(e['itm_id'])
                if not itm:
                    continue
                meals.append({
                    "meal": e.get('meal', 3),
                    "item": itm,
                    "color": palette.get(itm['itm_id'], "#7aa2f7"),
                })

            cells.append({"day": d, "meals": meals})

    return cells


# ---------------------- Routes ----------------------

# Home route (supports /<year>/<month> for nav)
@app.route('/', defaults={'year': None, 'month': None})
@app.route('/<int:year>/<int:month>')
def index(year, month):
    if session.get("Username") is None:
        return redirect(url_for("login"))

    today = date.today()
    if not year or not month:
        year, month = today.year, today.month

    # Load current user's generated_menu
    conn = create_connection(db_file)
    try:
        user = fetch_one(conn, 'SELECT * FROM "User" WHERE email = ?', (session.get("Email"),))
    finally:
        close_connection(conn)

    if not user:
        return redirect(url_for("logout"))

    gen_str = user[9] if len(user) > 9 else ""
    gen_map = parse_generated_menu(gen_str)

    # All item ids referenced (for the whole plan)
    all_item_ids = sorted({e['itm_id'] for entries in gen_map.values() for e in entries})
    items_by_id = fetch_menu_items_by_ids(all_item_ids)

    # Build cells for the month
    cells = build_calendar_cells(gen_map, year, month, items_by_id)

    # Build "today_menu" (Breakfast, Lunch, Dinner if present)
    today_iso = f"{today.year:04d}-{today.month:02d}-{today.day:02d}"
    today_entries = sorted(gen_map.get(today_iso, []), key=lambda e: e.get('meal', 3))
    today_menu = []
    for e in today_entries:
        item = items_by_id.get(e['itm_id'])
        if item:
            # expose 'meal' and the full item dict to the template
            today_menu.append(type("TodayEntry", (), {"meal": e['meal'], "item": item}))

    # prev/next month nav (unchanged)
    cur = date(year, month, 15)
    prev_m = (cur.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_m = (cur.replace(day=28) + timedelta(days=10)).replace(day=1)

    return render_template(
        "index.html",
        username=session["Username"],
        month_name=calendar.month_name[month],
        month=month,
        year=year,
        prev_month=prev_m.month,
        prev_year=prev_m.year,
        next_month=next_m.month,
        next_year=next_m.year,
        calendar_cells=cells,
        today_year=today.year,
        today_month=today.month,
        today_day=today.day,
        today_menu=today_menu,
    )

# Login route
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        conn = create_connection(db_file)
        try:
            user = fetch_one(conn, 'SELECT * FROM "User" WHERE email = ?', (email,))
        finally:
            close_connection(conn)

        if user and check_password_hash(user[5], password):
            session["Fname"] = user[1]
            session["Lname"] = user[2]
            session["Username"] = user[1] + " " + user[2]
            session["Email"] = user[3]
            session["Phone"] = user[4]
            session["Wallet"] = user[6]
            session["Preferences"] = user[7] if len(user) > 7 else ""
            session["Allergies"] = user[8] if len(user) > 8 else ""
            session["GeneratedMenu"] = user[9] if len(user) > 9 else ""
            session.permanent = True
            app.permanent_session_lifetime = timedelta(minutes=30)
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

# Logout route (single, no duplicates)
@app.route('/logout')
def logout():
    for k in ["Username","Fname","Lname","Email","Phone","Wallet","Preferences","Allergies","GeneratedMenu"]:
        session.pop(k, None)
    return redirect(url_for("login"))

# Registration route (NO generated_menu creation here)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = (request.form.get('fname') or '').strip()
        lname = (request.form.get('lname') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        phone = (request.form.get('phone') or '').strip()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''
        allergies = (request.form.get('allergies') or '').strip()
        preferences = (request.form.get('preferences') or '').strip()

        # Basic validations
        if not fname or not lname:
            return render_template('register.html', error="First and last name are required")
        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return render_template('register.html', error="Please enter a valid email address")
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        if len(password) < 6:
            return render_template('register.html', error="Password must be at least 6 characters")

        digits_only = re.sub(r"\D+", "", phone)
        if len(digits_only) < 7:
            return render_template('register.html', error="Please enter a valid phone number")

        conn = create_connection(db_file)
        try:
            exists = fetch_one(conn, 'SELECT 1 FROM "User" WHERE email = ?', (email,))
            if exists:
                return render_template('register.html', error="Email already registered")

            password_hashed = generate_password_hash(password)

            # Insert WITHOUT generated_menu (your LLM will populate it later)
            execute_query(
                conn,
                """
                INSERT INTO "User"
                    (first_name, last_name, email, phone, password_HS, wallet, preferences, allergies)
                VALUES
                    (?,          ?,         ?,     ?,     ?,           ?,      ?,            ?)
                """,
                (fname, lname, email, digits_only, password_hashed, 0, preferences, allergies)
            )
        except IntegrityError:
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
    return render_template(
        'profile.html',
        username=session['Username'],
        email=session['Email'],
        phone=session['Phone'],
        wallet=session['Wallet'],
        preferences=session['Preferences']
    )

# Database viewer route (uses helpers only)
@app.route('/db')
def db_view():
    if session.get('Username') is None:
        return redirect(url_for('login'))

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
    try:
        total_row = fetch_one(conn, f'SELECT COUNT(*) FROM "{table}"')
        total = (total_row[0] if total_row else 0) or 0

        pages = max(math.ceil(total / per_page), 1)
        page = min(page, pages)
        offset = (page - 1) * per_page

        col_rows = fetch_all(conn, f'PRAGMA table_info("{table}")')
        columns = [r[1] for r in col_rows] if col_rows else []

        rows = fetch_all(conn, f'SELECT * FROM "{table}" LIMIT ? OFFSET ?', (per_page, offset))
    finally:
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

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flask App for Meal Planner")
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the Flask app on')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the Flask app on')
    return parser.parse_args()

if __name__ == '__main__':
    """
    DB column names:

    MenuItem: itm_id,rtr_id,name,description,price,calories,instock,restock,allergens
    Order: ord_id,rtr_id,usr_id,details,status
    Restaurant: rtr_id,name,description,phone,email,password_HS,address,city,state,zip,hours,status
    Review: rev_id,rtr_id,usr_id,title,rating,description
    User: usr_id,first_name,last_name,email,phone,password_HS,wallet,preferences,allergies,generated_menu
    """
    args = parse_args()
    app.run(host=args.host, port=args.port, debug=True)
