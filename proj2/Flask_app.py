import os
import re
import math
import json
import calendar
from io import BytesIO
from flask import jsonify
from sqlite3 import IntegrityError
from datetime import timedelta, date, datetime
from pdf_receipt import generate_order_receipt_pdf
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template, url_for, redirect, request, session, send_file, abort

# Use ONLY these helpers for DB access
from sqlQueries import create_connection, close_connection, fetch_one, fetch_all, execute_query

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')

# ---------------------- Helpers ----------------------

def _money(x: float) -> float:
    try:
        return round(float(x) + 1e-9, 2)
    except Exception:
        return 0.0

def _cents_to_dollars(cents) -> float:
    try:
        return _money((cents or 0) / 100.0)
    except Exception:
        return 0.0

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
            session["usr_id"] = user[0] 
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

# Registration route
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
    # Must be logged in
    if session.get('Username') is None:
        return redirect(url_for('login'))

    # Load the full user row by session email
    email = session.get('Email')
    if not email:
        return redirect(url_for('logout'))

    import json
    from datetime import datetime

    def _fmt_date(iso_str: str) -> str:
        if not iso_str:
            return ""
        try:
            # Handles "2025-10-18T18:22:00-04:00" style strings
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return iso_str  # if it’s not ISO, show raw

    def _fmt_total(val) -> str:
        try:
            return f"${float(val):.2f}"
        except Exception:
            return ""

    conn = create_connection(db_file)
    try:
        row = fetch_one(conn, 'SELECT usr_id,first_name,last_name,email,phone,password_HS,wallet,preferences,allergies FROM "User" WHERE email = ?', (email,))
        if not row:
            return redirect(url_for('logout'))

        user = {
            "usr_id":        row[0],
            "first_name":    row[1],
            "last_name":     row[2],
            "email":         row[3],
            "phone":         row[4],
            "password_HS":   row[5],
            "wallet":        (row[6] or 0) / 100.0,
            "preferences":   row[7] or "",
            "allergies":     row[8] or "",
        }

        session['usr_id'] = user["usr_id"]

        # Pull orders for this user; details is JSON we will parse
        order_rows = fetch_all(
            conn,
            '''
            SELECT o.ord_id, o.details, o.status, r.name
            FROM "Order" o
            JOIN "Restaurant" r ON o.rtr_id = r.rtr_id
            WHERE o.usr_id = ?
            ORDER BY o.ord_id DESC
            ''',
            (user["usr_id"],)
        )

        orders = []
        for ord_id, details, status, r_name in order_rows:
            placed = ""
            total = ""
            if details:
                try:
                    j = json.loads(details)
                    placed = _fmt_date(j.get("placed_at") or j.get("time"))
                    charges = j.get("charges") or {}
                    total_val = charges.get("total") or charges.get("grand_total") or charges.get("amount")
                    total = _fmt_total(total_val) if total_val is not None else ""
                except Exception:
                    pass

            orders.append({
                "id": ord_id,
                "date": placed,
                "status": status or "",
                "restaurant": r_name,
                "total": total
            })
    finally:
        close_connection(conn)

    pw_updated = request.args.get('pw_updated')
    pw_error   = request.args.get('pw_error')

    return render_template(
        "profile.html",
        user=user,
        orders=orders,
        pw_updated=pw_updated,
        pw_error=pw_error
    )

# Edit Profile route
@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if session.get('Username') is None:
        return redirect(url_for('login'))

    usr_id = session.get('usr_id')
    if not usr_id:
        return redirect(url_for('logout'))

    conn = create_connection(db_file)
    try:
        row = fetch_one(conn, '''
            SELECT usr_id, first_name, last_name, email, phone, wallet, preferences, allergies
            FROM "User" WHERE usr_id = ?
        ''', (usr_id,))
    finally:
        close_connection(conn)

    if not row:
        return redirect(url_for('logout'))

    user = {
        "usr_id": row[0],
        "first_name": row[1],
        "last_name": row[2],
        "email": row[3],
        "phone": row[4],
        "wallet": (row[5] or 0) / 100.0,
        "preferences": row[6] or "",
        "allergies": row[7] or "",
    }

    # For now just render an edit form (you can build edit_profile.html)
    if request.method == 'POST':
        # You’ll expand this with update logic later
        # Example: update phone, preferences, allergies
        new_phone = request.form.get('phone') or user['phone']
        new_prefs = request.form.get('preferences') or user['preferences']
        new_allergies = request.form.get('allergies') or user['allergies']

        conn = create_connection(db_file)
        try:
            execute_query(conn, '''
                UPDATE "User"
                SET phone = ?, preferences = ?, allergies = ?
                WHERE usr_id = ?
            ''', (new_phone, new_prefs, new_allergies, usr_id))
        finally:
            close_connection(conn)

        # Refresh session values
        session['Phone'] = new_phone
        session['Preferences'] = new_prefs
        session['Allergies'] = new_allergies

        return redirect(url_for('profile'))

    return render_template("edit_profile.html", user=user)

@app.route('/profile/change-password', methods=['POST'])
def change_password():
    # Must be logged in
    if session.get('Username') is None:
        return redirect(url_for('login'))

    usr_id = session.get('usr_id')
    if not usr_id:
        # Fallback: resolve via email
        email = session.get('Email')
        if not email:
            return redirect(url_for('logout'))
        conn = create_connection(db_file)
        try:
            row = fetch_one(conn, 'SELECT usr_id FROM "User" WHERE email = ?', (email,))
            if not row:
                return redirect(url_for('logout'))
            usr_id = row[0]
            session['usr_id'] = usr_id
        finally:
            close_connection(conn)

    # Read form fields
    current_password = (request.form.get('current_password') or '').strip()
    new_password     = (request.form.get('new_password') or '').strip()
    confirm_password = (request.form.get('confirm_password') or '').strip()

    # Basic validations (mirror your frontend behavior)
    if not current_password:
        return redirect(url_for('profile', pw_error='missing_current'))
    if len(new_password) < 6:
        return redirect(url_for('profile', pw_error='too_short'))
    if new_password != confirm_password:
        return redirect(url_for('profile', pw_error='mismatch'))
    if new_password == current_password:
        return redirect(url_for('profile', pw_error='same_as_current'))

    # Verify current hash & update to new hash
    conn = create_connection(db_file)
    try:
        row = fetch_one(conn, 'SELECT password_HS FROM "User" WHERE usr_id = ?', (usr_id,))
        if not row:
            return redirect(url_for('logout'))

        stored_hash = row[0]
        if not check_password_hash(stored_hash, current_password):
            # wrong current password
            return redirect(url_for('profile', pw_error='incorrect_current'))

        # All good → update
        new_hash = generate_password_hash(new_password)
        execute_query(conn, 'UPDATE "User" SET password_HS = ? WHERE usr_id = ?', (new_hash, usr_id))

    finally:
        close_connection(conn)

    # Success
    return redirect(url_for('profile', pw_updated=1))

# Order route (Calendar "Order" button target)
@app.route('/order', methods=['GET', 'POST'])
def order():
    # Must be logged in
    if session.get("Username") is None:
        return redirect(url_for("login"))

    # Resolve usr_id strictly
    usr_id = session.get("usr_id")
    if not usr_id:
        conn = create_connection(db_file)
        try:
            row = fetch_one(conn, 'SELECT usr_id FROM "User" WHERE email = ?', (session.get('Email'),))
            if not row:
                return redirect(url_for("logout"))
            usr_id = row[0]
            session["usr_id"] = usr_id
        finally:
            close_connection(conn)

    # ---- POST JSON: place a single order containing ALL items in the restaurant group ----
    if request.method == 'POST' and request.is_json:
        payload = request.get_json(silent=True) or {}
        rtr_id = int(payload.get("restaurant_id") or 0)
        items_in = payload.get("items") or []     # [{itm_id, qty, notes}]
        delivery_type = (payload.get("delivery_type") or "delivery").lower()
        if delivery_type not in ("delivery", "pickup"):
            delivery_type = "delivery"
        tip_dollars = _money(payload.get("tip") or 0)
        eta_minutes = int(payload.get("eta_minutes") or 40)
        iso_date = (payload.get("date") or datetime.now().date().isoformat())
        try:
            meal = int(payload.get("meal") or 3)
        except Exception:
            meal = 3

        if rtr_id <= 0 or not items_in:
            return jsonify({"ok": False, "error": "invalid_input"}), 400

        # Look up all items strictly from DB to get authoritative prices/names
        itm_ids = [int(it.get("itm_id") or 0) for it in items_in if int(it.get("itm_id") or 0) > 0]
        if not itm_ids:
            return jsonify({"ok": False, "error": "no_items"}), 400

        conn = create_connection(db_file)
        try:
            qmarks = ",".join(["?"] * len(itm_ids))
            rows = fetch_all(conn, f'''
                SELECT m.itm_id, m.rtr_id, m.name, m.price, r.name
                FROM "MenuItem" m
                JOIN "Restaurant" r ON r.rtr_id = m.rtr_id
                WHERE m.itm_id IN ({qmarks})
            ''', tuple(itm_ids))
        finally:
            close_connection(conn)

        # Validate that all items belong to the same restaurant
        if not rows:
            return jsonify({"ok": False, "error": "items_not_found"}), 404

        # Map itm_id -> {price, name, rtr_id, rtr_name}
        dbmap = {row[0]: {"rtr_id": row[1], "name": row[2], "price_cents": row[3] or 0, "restaurant_name": row[4]} for row in rows}
        for it in itm_ids:
            if it not in dbmap:
                return jsonify({"ok": False, "error": f"item_{it}_not_found"}), 404
            if int(dbmap[it]["rtr_id"]) != rtr_id:
                return jsonify({"ok": False, "error": "mixed_restaurants"}), 400

        # Build items array for details; compute charges
        detail_items = []
        subtotal = 0.0
        for it in items_in:
            iid = int(it.get("itm_id"))
            qty = int(it.get("qty") or 1)
            if qty <= 0: qty = 1
            meta = dbmap[iid]
            unit_price = _cents_to_dollars(meta["price_cents"])
            line_total = _money(unit_price * qty)
            subtotal = _money(subtotal + line_total)
            detail_items.append({
                "itm_id": iid,
                "name": meta["name"],
                "qty": qty,
                "unit_price": unit_price,
                "line_total": line_total,
                **({"notes": (it.get("notes") or "")} if it.get("notes") else {})
            })

        tax = _money(subtotal * 0.0725)
        delivery_fee = 3.99 if delivery_type == "delivery" else 0.00
        service_fee = 1.49
        total = _money(subtotal + tax + delivery_fee + service_fee + tip_dollars)

        placed_iso = datetime.now().astimezone().isoformat()

        details = {
            "placed_at": placed_iso,
            "restaurant_id": int(rtr_id),
            "items": detail_items,
            "charges": {
                "subtotal": subtotal,
                "tax": tax,
                "delivery_fee": delivery_fee,
                "service_fee": service_fee,
                "tip": tip_dollars,
                "total": total
            },
            "delivery_type": delivery_type,
            "eta_minutes": int(eta_minutes),
            "date": iso_date,
            "meal": meal
        }

        # Insert the single order row with status "Ordered"
        conn = create_connection(db_file)
        try:
            execute_query(conn, '''
                INSERT INTO "Order" (rtr_id, usr_id, details, status)
                VALUES (?, ?, ?, ?)
            ''', (rtr_id, usr_id, json.dumps(details), "Ordered"))
            row = fetch_one(conn, 'SELECT last_insert_rowid()')
            new_ord_id = row[0] if row else None
        finally:
            close_connection(conn)

        return jsonify({"ok": True, "ord_id": new_ord_id})

    # ---- (optional) legacy GET single-item path, kept for compatibility ----
    # If you don't need this anymore, you can remove the whole GET section.
    # Expect query: itm_id, qty, notes, delivery, tip, eta, date, meal
    itm_id = int(request.args.get("itm_id") or 0)
    if itm_id <= 0:
        return redirect(url_for("orders"))

    try:
        qty = max(1, int(request.args.get("qty", "1")))
    except ValueError:
        qty = 1
    delivery_type = (request.args.get("delivery") or "delivery").lower()
    if delivery_type not in ("delivery", "pickup"):
        delivery_type = "delivery"
    try:
        tip_dollars = _money(float(request.args.get("tip", "0")))
    except Exception:
        tip_dollars = 0.0
    try:
        eta_minutes = int(request.args.get("eta", "40"))
    except Exception:
        eta_minutes = 40
    iso_date = (request.args.get("date") or datetime.now().date().isoformat())
    try:
        meal = int(request.args.get("meal", "3"))
    except Exception:
        meal = 3
    notes = (request.args.get("notes") or "").strip()

    # Look up item & restaurant strictly
    conn = create_connection(db_file)
    try:
        mi = fetch_one(conn, '''
            SELECT m.itm_id, m.rtr_id, m.name, m.price, r.name
            FROM "MenuItem" m
            JOIN "Restaurant" r ON r.rtr_id = m.rtr_id
            WHERE m.itm_id = ?
        ''', (itm_id,))
    finally:
        close_connection(conn)
    if not mi:
        return redirect(url_for("orders"))

    item_id, rtr_id, item_name, price_cents, restaurant_name = mi
    unit_price = _cents_to_dollars(price_cents)
    line_total = _money(unit_price * qty)

    tax = _money(line_total * 0.0725)
    delivery_fee = 3.99 if delivery_type == "delivery" else 0.00
    service_fee = 1.49
    total = _money(line_total + tax + delivery_fee + service_fee + tip_dollars)

    details = {
        "placed_at": datetime.now().astimezone().isoformat(),
        "restaurant_id": int(rtr_id),
        "items": [{
            "itm_id": int(item_id),
            "name": item_name,
            "qty": int(qty),
            "unit_price": unit_price,
            "line_total": line_total,
            **({"notes": notes} if notes else {})
        }],
        "charges": {
            "subtotal": line_total,
            "tax": tax,
            "delivery_fee": delivery_fee,
            "service_fee": service_fee,
            "tip": tip_dollars,
            "total": total
        },
        "delivery_type": delivery_type,
        "eta_minutes": int(eta_minutes),
        "date": iso_date,
        "meal": meal
    }

    conn = create_connection(db_file)
    try:
        execute_query(conn, '''
            INSERT INTO "Order" (rtr_id, usr_id, details, status)
            VALUES (?, ?, ?, ?)
        ''', (rtr_id, usr_id, json.dumps(details), "Ordered"))
        row = fetch_one(conn, 'SELECT last_insert_rowid()')
        new_ord_id = row[0] if row else None
    finally:
        close_connection(conn)

    return redirect(url_for("profile") + (f"?ordered={new_ord_id}" if new_ord_id else ""))

# Orders route
@app.route('/orders')
def orders():
    if session.get('Username') is None:
        return redirect(url_for('login'))

    conn = create_connection(db_file)
    try:
        # Pull address fields too
        restaurants = fetch_all(conn, 'SELECT rtr_id, name, address, city, state, zip FROM "Restaurant"')
        menu_items = fetch_all(conn, '''
            SELECT itm_id, rtr_id, name, price, calories, allergens, description
            FROM "MenuItem"
            WHERE instock IS NULL OR instock = 1
        ''')
    finally:
        close_connection(conn)

    def _addr(a, c, s, z) -> str:
        """
        Safely join address parts that might be None/ints.
        """
        parts_raw = [a, c, s, z]
        parts = []
        for p in parts_raw:
            if p is None:
                continue
            # Coerce to string and strip
            sp = str(p).strip()
            if sp:
                parts.append(sp)
        return ", ".join(parts)

    rest_list = [{
        "rtr_id": r[0],
        "name": r[1],
        "address": r[2] or "",
        "city": r[3] or "",
        "state": r[4] or "",
        "zip": r[5] if r[5] is not None else "",
        "address_full": _addr(r[2], r[3], r[4], r[5]),
    } for r in restaurants]

    item_list = [{
        "itm_id":      m[0],
        "rtr_id":      m[1],
        "name":        m[2],
        "price_cents": m[3] or 0,
        "calories":    m[4] or 0,
        "allergens":   m[5] or "",
        "description": m[6] or "",
    } for m in menu_items]

    return render_template("orders.html", restaurants=rest_list, items=item_list)

# Order receipt PDF route
@app.route('/orders/<int:ord_id>/receipt.pdf')
def order_receipt(ord_id: int):
    # Must be logged in
    if session.get('Username') is None:
        return redirect(url_for('login'))

    # Ensure the order belongs to the logged-in user
    conn = create_connection(db_file)
    try:
        row = fetch_one(conn, 'SELECT usr_id FROM "Order" WHERE ord_id = ?', (ord_id,))
        if not row:
            abort(404)
        if session.get('usr_id') and row[0] != session['usr_id']:
            abort(403)
        # If usr_id not in session (older sessions), compare via email
        if not session.get('usr_id'):
            # Resolve current user's usr_id by email
            urow = fetch_one(conn, 'SELECT usr_id FROM "User" WHERE email = ?', (session.get('Email'),))
            if not urow or urow[0] != row[0]:
                abort(403)

        pdf_bytes = generate_order_receipt_pdf(db_file, ord_id)  # returns bytes
    finally:
        close_connection(conn)

    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'order_{ord_id}_receipt.pdf'
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

if __name__ == '__main__':
    """
    DB column names:

    MenuItem: itm_id,rtr_id,name,description,price,calories,instock,restock,allergens
    Order: ord_id,rtr_id,usr_id,details,status
    Restaurant: rtr_id,name,description,phone,email,password_HS,address,city,state,zip,hours,status
    Review: rev_id,rtr_id,usr_id,title,rating,description
    User: usr_id,first_name,last_name,email,phone,password_HS,wallet,preferences,allergies,generated_menu
    """
    app.run(debug=True)
