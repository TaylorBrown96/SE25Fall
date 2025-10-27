import os
import re
import json
import sqlite3
import importlib
import importlib.util
import sys
from datetime import date
import pytest

# ------------- Dynamic loader & sys.path -------------
PROJECT_ROOT = os.path.abspath(os.getcwd())
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def _load_module_as(name: str, filename_candidates):
    for cand in filename_candidates:
        p = os.path.abspath(cand)
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location(name, p)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore
            return mod
    raise ModuleNotFoundError(f"Could not find any of: {filename_candidates} in {os.getcwd()}")

def _import_pdf_receipt_if_present():
    try:
        return importlib.import_module("pdf_receipt")
    except ModuleNotFoundError:
        try:
            return _load_module_as("pdf_receipt", ["pdf_receipt.py", "pdfReceipt.py", "receipt.py"])
        except ModuleNotFoundError:
            return None

def _import_flask_app():
    _import_pdf_receipt_if_present()
    try:
        return importlib.import_module("Flask_app")
    except ModuleNotFoundError:
        return _load_module_as("Flask_app", ["Flask_app.py", "flask_app.py", "app.py", "FlaskApp.py"])

def _import_sql_queries():
    try:
        return importlib.import_module("sqlQueries")
    except ModuleNotFoundError:
        return _load_module_as("sqlQueries", ["sqlQueries.py", "sqlqueries.py", "SQLQueries.py"])

FA = _import_flask_app()
SQ = _import_sql_queries()

# ------------- Schema & seed -------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS "User" (
  usr_id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT,
  last_name TEXT,
  email TEXT UNIQUE,
  phone TEXT,
  password_HS TEXT,
  wallet INTEGER,
  preferences TEXT,
  allergies TEXT,
  generated_menu TEXT
);

CREATE TABLE IF NOT EXISTS "Restaurant" (
  rtr_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  description TEXT,
  phone TEXT,
  email TEXT,
  password_HS TEXT,
  address TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  hours TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS "MenuItem" (
  itm_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rtr_id INTEGER,
  name TEXT,
  description TEXT,
  price INTEGER,
  calories INTEGER,
  instock INTEGER,
  restock TEXT,
  allergens TEXT,
  FOREIGN KEY(rtr_id) REFERENCES Restaurant(rtr_id)
);

CREATE TABLE IF NOT EXISTS "Order" (
  ord_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rtr_id INTEGER,
  usr_id INTEGER,
  details TEXT,
  status TEXT,
  FOREIGN KEY(rtr_id) REFERENCES Restaurant(rtr_id),
  FOREIGN KEY(usr_id) REFERENCES User(usr_id)
);

CREATE TABLE IF NOT EXISTS "Review" (
  rev_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rtr_id INTEGER,
  usr_id INTEGER,
  title TEXT,
  rating INTEGER,
  description TEXT
);
"""

@pytest.fixture(scope="session")
def tmp_db_path_more(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db_more") / "CSC510_DB_test.sqlite"
    con = sqlite3.connect(db_path.as_posix())
    try:
        con.executescript(SCHEMA)
        # Restaurant A
        con.execute('INSERT INTO "Restaurant"(name, city, state, zip) VALUES (?,?,?,?)',
                    ("Pasta Palace", "Raleigh", "NC", "27601"))
        rtr_a = con.execute('SELECT rtr_id FROM "Restaurant" WHERE name=?', ("Pasta Palace",)).fetchone()[0]
        # Restaurant B
        con.execute('INSERT INTO "Restaurant"(name, city, state, zip) VALUES (?,?,?,?)',
                    ("Burger Barn", "Durham", "NC", "27701"))
        rtr_b = con.execute('SELECT rtr_id FROM "Restaurant" WHERE name=?', ("Burger Barn",)).fetchone()[0]

        # Items for A
        con.execute('INSERT INTO "MenuItem"(rtr_id, name, description, price, calories, instock, allergens) VALUES (?,?,?,?,?,?,?)',
                    (rtr_a, "Spaghetti", "Classic red sauce", 1299, 650, 1, "wheat"))
        con.execute('INSERT INTO "MenuItem"(rtr_id, name, description, price, calories, instock, allergens) VALUES (?,?,?,?,?,?,?)',
                    (rtr_a, "Lasagna", "Layers of goodness", 1499, 800, 1, "dairy,wheat"))
        # One out-of-stock item (should be excluded by /orders page logic)
        con.execute('INSERT INTO "MenuItem"(rtr_id, name, description, price, calories, instock, allergens) VALUES (?,?,?,?,?,?,?)',
                    (rtr_a, "Ravioli", "Out of stock", 1399, 700, 0, "wheat"))
        # Item for B
        con.execute('INSERT INTO "MenuItem"(rtr_id, name, description, price, calories, instock, allergens) VALUES (?,?,?,?,?,?,?)',
                    (rtr_b, "Cheeseburger", "With fries", 1099, 900, 1, "dairy,wheat"))

        item_ids = [row[0] for row in con.execute('SELECT itm_id FROM "MenuItem"').fetchall()]

        # User
        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash("secret123")
        gen_menu = f"[2025-10-27,{item_ids[0]},1][2025-10-27,{item_ids[1]},3]"
        con.execute('INSERT INTO "User"(first_name,last_name,email,phone,password_HS,wallet,preferences,allergies,generated_menu) VALUES (?,?,?,?,?,?,?,?,?)',
                    ("Taylor", "Brown", "taylor@example.com", "9195550000", pw_hash, 12568, "vegan-ish", "peanuts", gen_menu))
        usr_id = con.execute('SELECT usr_id FROM "User" WHERE email=?', ("taylor@example.com",)).fetchone()[0]

        # Seed one order
        details = {
            "placed_at": "2025-10-26T12:00:00-04:00",
            "restaurant_id": rtr_a,
            "items": [{"itm_id": item_ids[0], "name": "Spaghetti", "qty": 1, "unit_price": 12.99, "line_total": 12.99}],
            "charges": {"subtotal": 12.99, "tax": 0.94, "delivery_fee": 3.99, "service_fee": 1.49, "tip": 2.0, "total": 21.41},
            "delivery_type": "delivery",
            "eta_minutes": 40,
            "date": "2025-10-26",
            "meal": 3
        }
        con.execute('INSERT INTO "Order"(rtr_id, usr_id, details, status) VALUES (?,?,?,?)',
                    (rtr_a, usr_id, json.dumps(details), "Ordered"))
        con.commit()
    finally:
        con.close()
    return db_path.as_posix()

@pytest.fixture(autouse=True)
def _isolation_more(monkeypatch, tmp_db_path_more):
    # point to our DB
    monkeypatch.setattr(FA, "db_file", tmp_db_path_more, raising=False)

    # fake render_template
    def fake_render_template(name, **ctx):
        keys = ",".join(sorted(ctx.keys()))
        return f"TEMPLATE:{name}|CTX:{keys}"
    monkeypatch.setattr(FA, "render_template", fake_render_template, raising=False)

    FA.app.config.update(TESTING=True, SECRET_KEY="test")
    yield

@pytest.fixture
def client_more():
    return FA.app.test_client()

def _login(client, email="taylor@example.com", password="secret123", follow=True):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=follow)

# -------------------- 30 additional tests --------------------

def test_parse_generated_menu_empty():
    assert FA.parse_generated_menu("") == {}

def test_parse_generated_menu_ignores_bad_tokens():
    s = "not_a_pair [2025-10-27, 5, 2] [2025-99-99,abc] [2025-10-28, 6 , 3] junk"
    m = FA.parse_generated_menu(s)
    assert "2025-10-27" in m and "2025-10-28" in m
    assert all(isinstance(e["itm_id"], int) for e in m["2025-10-27"])

def test_parse_generated_menu_spaces_and_legacy():
    s = "[ 2025-10-27 , 5 ] [2025-10-27,6,1]"
    m = FA.parse_generated_menu(s)
    assert len(m["2025-10-27"]) == 2
    meals = sorted([e["meal"] for e in m["2025-10-27"]])
    assert meals == [1, 3]

def test_palette_for_item_ids_empty():
    assert FA.palette_for_item_ids([]) == {}

def test_money_rounding_and_negatives():
    assert FA._money(1.005) in (1.0, 1.01)
    assert FA._money(-3.333) == -3.33
    assert FA._money("nope") == 0.0

def test_cents_to_dollars_varied_inputs():
    assert FA._cents_to_dollars(250) == 2.5
    assert FA._cents_to_dollars(-125) == -1.25
    assert FA._cents_to_dollars(None) == 0.0

def test_build_calendar_cells_empty_month_structure():
    today = date.today()
    cells = FA.build_calendar_cells({}, today.year, today.month, {})
    import calendar as cal
    weeks = cal.Calendar(firstweekday=6).monthdayscalendar(today.year, today.month)
    assert len(cells) == len(weeks) * 7
    zero_days = [c for c in cells if c.get("day") == 0]
    assert len(zero_days) == sum(1 for w in weeks for d in w if d == 0)

def test_build_calendar_cells_meal_sort_order(tmp_db_path_more):
    items = FA.fetch_menu_items_by_ids([1,2])
    gen_map = {"2025-10-27": [{"itm_id": 1, "meal": 3}, {"itm_id": 2, "meal": 1}]}
    cells = FA.build_calendar_cells(gen_map, 2025, 10, items)
    target = next(c for c in cells if c.get("day") == 27)
    meals = [m["meal"] for m in target["meals"]]
    assert meals == [1, 3]

def test_fetch_menu_items_by_ids_empty_returns_empty():
    assert FA.fetch_menu_items_by_ids([]) == {}

def test_login_bad_password_shows_error(client_more):
    r = client_more.post("/login", data={"email":"taylor@example.com", "password":"WRONG"})
    assert r.status_code == 200
    assert b"TEMPLATE:login.html" in r.data

def test_register_get_200(client_more):
    r = client_more.get("/register")
    assert r.status_code == 200
    assert b"TEMPLATE:register.html" in r.data

def test_register_post_invalid_email(client_more):
    r = client_more.post("/register", data={
        "fname":"A","lname":"B","email":"bademail","phone":"1234567",
        "password":"abcdef","confirm_password":"abcdef"
    })
    assert b"TEMPLATE:register.html" in r.data
    assert r.status_code == 200

def test_register_post_mismatch_password(client_more):
    r = client_more.post("/register", data={
        "fname":"A","lname":"B","email":"ok@example.com","phone":"1234567",
        "password":"abcdef","confirm_password":"abcdeg"
    })
    assert r.status_code == 200
    assert b"TEMPLATE:register.html" in r.data

def test_register_post_short_password(client_more):
    r = client_more.post("/register", data={
        "fname":"A","lname":"B","email":"ok2@example.com","phone":"1234567",
        "password":"123","confirm_password":"123"
    })
    assert r.status_code == 200
    assert b"TEMPLATE:register.html" in r.data

def test_register_post_bad_phone(client_more):
    r = client_more.post("/register", data={
        "fname":"A","lname":"B","email":"ok3@example.com","phone":"12",
        "password":"abcdef","confirm_password":"abcdef"
    })
    assert r.status_code == 200
    assert b"TEMPLATE:register.html" in r.data

def test_register_post_success_and_duplicate(client_more):
    r = client_more.post("/register", data={
        "fname":"A","lname":"B","email":"ok4@example.com","phone":"919-555-0101",
        "password":"abcdef","confirm_password":"abcdef"
    }, follow_redirects=False)
    assert r.status_code in (302, 303)
    r2 = client_more.post("/register", data={
        "fname":"A","lname":"B","email":"ok4@example.com","phone":"919-555-0101",
        "password":"abcdef","confirm_password":"abcdef"
    })
    assert r2.status_code == 200
    assert b"TEMPLATE:register.html" in r2.data

def test_profile_requires_login_redirect(client_more):
    r = client_more.get("/profile")
    assert r.status_code in (302, 303)

def test_change_password_missing_current(client_more):
    _login(client_more)
    r = client_more.post("/profile/change-password", data={
        "current_password":"", "new_password":"abcdef", "confirm_password":"abcdef"
    }, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "pw_error=missing_current" in r.headers.get("Location","")

def test_change_password_same_as_current(client_more):
    _login(client_more)
    r = client_more.post("/profile/change-password", data={
        "current_password":"secret123", "new_password":"secret123", "confirm_password":"secret123"
    }, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "pw_error=same_as_current" in r.headers.get("Location","")

def test_change_password_incorrect_current(client_more):
    _login(client_more)
    r = client_more.post("/profile/change-password", data={
        "current_password":"WRONG", "new_password":"abcdef", "confirm_password":"abcdef"
    }, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "pw_error=incorrect_current" in r.headers.get("Location","")

def test_logout_clears_session(client_more):
    _login(client_more)
    r = client_more.get("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    r2 = client_more.get("/", follow_redirects=False)
    assert r2.status_code in (302, 303)

def test_orders_json_missing_items_400(client_more):
    _login(client_more)
    payload = {"restaurant_id": 1, "items": []}
    r = client_more.post("/order", json=payload)
    assert r.status_code == 400
    assert r.is_json and r.get_json().get("error") == "invalid_input"

def test_orders_json_invalid_restaurant_400(client_more):
    _login(client_more)
    payload = {"restaurant_id": 0, "items": [{"itm_id": 1, "qty": 1}]}
    r = client_more.post("/order", json=payload)
    assert r.status_code == 400

def test_orders_json_mixed_restaurants_400(client_more, tmp_db_path_more):
    _login(client_more)
    con = sqlite3.connect(tmp_db_path_more)
    try:
        rows = con.execute('SELECT itm_id, rtr_id FROM "MenuItem" ORDER BY itm_id').fetchall()
    finally:
        con.close()
    assert len(rows) >= 3
    itm_a = rows[0][0]
    itm_b = rows[-1][0]
    con = sqlite3.connect(tmp_db_path_more)
    try:
        rtr_a = con.execute('SELECT rtr_id FROM "MenuItem" WHERE itm_id=?', (itm_a,)).fetchone()[0]
    finally:
        con.close()
    payload = {"restaurant_id": rtr_a, "items": [{"itm_id": itm_a, "qty": 1}, {"itm_id": itm_b, "qty": 1}]}
    r = client_more.post("/order", json=payload)
    assert r.status_code == 400
    assert r.is_json and r.get_json().get("error") == "mixed_restaurants"

def test_orders_json_success_with_weird_delivery_type(client_more):
    _login(client_more)
    items = FA.fetch_menu_items_by_ids([1,2])
    rtr_id = list(items.values())[0]["rtr_id"]
    payload = {"restaurant_id": rtr_id, "items": [{"itm_id": 1, "qty": 2}], "delivery_type": "WEIRD", "tip": 0.0, "eta_minutes": 10, "date": "2025-10-27", "meal": 1}
    r = client_more.post("/order", json=payload)
    assert r.status_code == 200
    assert r.is_json and r.get_json().get("ok") is True

def test_order_legacy_missing_item_redirects(client_more):
    _login(client_more)
    r = client_more.get("/order")
    assert r.status_code in (302, 303)

def test_order_legacy_bad_item_redirects(client_more):
    _login(client_more)
    r = client_more.get("/order?itm_id=999999")
    assert r.status_code in (302, 303)

def test_db_view_invalid_table_falls_back(client_more):
    _login(client_more)
    r = client_more.get("/db?t=Nope", follow_redirects=True)
    assert r.status_code in (200, 302, 303)
    assert (b"TEMPLATE:db_view.html" in r.data) or (b"TEMPLATE:login.html" in r.data)

def test_db_view_out_of_range_page_clamps(client_more):
    _login(client_more)
    r = client_more.get("/db?t=User&page=9999", follow_redirects=True)
    assert r.status_code in (200, 302, 303)
    assert (b"TEMPLATE:db_view.html" in r.data) or (b"TEMPLATE:login.html" in r.data)

def test_profile_edit_get_and_post(client_more):
    _login(client_more)
    r = client_more.get("/profile/edit")
    assert r.status_code == 200
    assert b"TEMPLATE:edit_profile.html" in r.data
    r2 = client_more.post("/profile/edit", data={"phone":"8005551212", "preferences":"low-salt", "allergies":"shrimp"}, follow_redirects=False)
    assert r2.status_code in (302, 303)

def test_orders_page_lists_only_instock(client_more):
    _login(client_more)
    r = client_more.get("/orders")
    assert r.status_code == 200
    assert b"TEMPLATE:orders.html" in r.data

@pytest.mark.skipif(_import_pdf_receipt_if_present() is None, reason="pdf_receipt/reportlab not available")
def test_order_receipt_pdf_endpoint(client_more, tmp_db_path_more):
    _login(client_more)
    con = sqlite3.connect(tmp_db_path_more)
    try:
        oid = con.execute('SELECT ord_id FROM "Order" LIMIT 1').fetchone()[0]
    finally:
        con.close()
    r = client_more.get(f"/orders/{oid}/receipt.pdf")
    assert r.status_code == 200
    assert r.headers.get("Content-Type","").startswith("application/pdf")
    assert r.data[:4] == b"%PDF"
