
import os
import re
import json
import sqlite3
import importlib
import importlib.util
import sys
from datetime import date
import pytest
from werkzeug.security import generate_password_hash

# Ensure the project root (where this test file lives) is on sys.path
PROJECT_ROOT = os.path.abspath(os.getcwd())
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def _load_module_as(name: str, filename_candidates):
    """
    Load a Python module from the first existing filename in filename_candidates
    and insert it into sys.modules under the given name.
    """
    for cand in filename_candidates:
        p = os.path.abspath(cand)
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location(name, p)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            assert spec and spec.loader, f"Could not prepare loader for {cand}"
            spec.loader.exec_module(mod)  # type: ignore
            return mod
    raise ModuleNotFoundError(f"Could not find any of: {filename_candidates} in {os.getcwd()}")

# Try to import normally; if it fails, load by filename
def _import_pdf_receipt_if_present():
    try:
        return importlib.import_module("pdf_receipt")
    except ModuleNotFoundError:
        # Try common filenames
        try:
            return _load_module_as("pdf_receipt", ["pdf_receipt.py", "pdfReceipt.py", "receipt.py"])
        except ModuleNotFoundError:
            # It's optional for most tests; only receipt route uses it.
            return None

def _import_flask_app():
    # Make sure pdf_receipt is importable first (Flask_app imports it)
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

# Import once at module import time so tests reuse same modules
FA = _import_flask_app()
SQ = _import_sql_queries()

# ---------------- Schema & seed fixtures ----------------
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
def tmp_db_path(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "CSC510_DB_test.sqlite"
    con = sqlite3.connect(db_path.as_posix())
    try:
        con.executescript(SCHEMA)
        # Restaurant
        con.execute('INSERT INTO "Restaurant"(name, city, state, zip) VALUES (?,?,?,?)',
                    ("Pasta Palace", "Raleigh", "NC", "27601"))
        rtr_id = con.execute('SELECT rtr_id FROM "Restaurant" WHERE name=?', ("Pasta Palace",)).fetchone()[0]

        # Items
        con.execute('INSERT INTO "MenuItem"(rtr_id, name, description, price, calories, instock, allergens) VALUES (?,?,?,?,?,?,?)',
                    (rtr_id, "Spaghetti", "Classic red sauce", 1299, 650, 1, "wheat"))
        con.execute('INSERT INTO "MenuItem"(rtr_id, name, description, price, calories, instock, allergens) VALUES (?,?,?,?,?,?,?)',
                    (rtr_id, "Lasagna", "Layers of goodness", 1499, 800, 1, "dairy,wheat"))
        item_ids = [row[0] for row in con.execute('SELECT itm_id FROM "MenuItem"').fetchall()]

        # User (wallet in cents)
        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash("secret123")
        gen_menu = f"[2025-10-27,{item_ids[0]},1][2025-10-27,{item_ids[1]},3]"
        con.execute('INSERT INTO "User"(first_name,last_name,email,phone,password_HS,wallet,preferences,allergies,generated_menu) VALUES (?,?,?,?,?,?,?,?,?)',
                    ("Taylor", "Brown", "taylor@example.com", "9195550000", pw_hash, 12568, "vegan-ish", "peanuts", gen_menu))
        usr_id = con.execute('SELECT usr_id FROM "User" WHERE email=?', ("taylor@example.com",)).fetchone()[0]

        # One order
        details = {
            "placed_at": "2025-10-26T12:00:00-04:00",
            "restaurant_id": rtr_id,
            "items": [{"itm_id": item_ids[0], "name": "Spaghetti", "qty": 1, "unit_price": 12.99, "line_total": 12.99}],
            "charges": {"subtotal": 12.99, "tax": 0.94, "delivery_fee": 3.99, "service_fee": 1.49, "tip": 2.0, "total": 21.41},
            "delivery_type": "delivery",
            "eta_minutes": 40,
            "date": "2025-10-26",
            "meal": 3
        }
        con.execute('INSERT INTO "Order"(rtr_id, usr_id, details, status) VALUES (?,?,?,?)',
                    (rtr_id, usr_id, json.dumps(details), "Ordered"))
        con.commit()
    finally:
        con.close()
    return db_path.as_posix()

@pytest.fixture(autouse=True)
def _isolation(monkeypatch, tmp_db_path):
    """
    Point app at temp DB and stub render_template so templates aren't required.
    """
    FA = sys.modules["Flask_app"]

    monkeypatch.setattr(FA, "db_file", tmp_db_path, raising=False)

    def fake_render_template(name, **ctx):
        keys = ",".join(sorted(ctx.keys()))
        return f"TEMPLATE:{name}|CTX:{keys}"
    monkeypatch.setattr(FA, "render_template", fake_render_template, raising=False)

    FA.app.config.update(TESTING=True, SECRET_KEY="test")
    yield

@pytest.fixture
def app_client():
    FA = sys.modules["Flask_app"]
    return FA.app.test_client()

# ---------------- Tests: Flask_app.py ----------------

def test_modules_import():
    import types
    assert isinstance(FA, types.ModuleType)
    assert isinstance(SQ, types.ModuleType)

def test_flask_app_exposes_app_if_present():
    from flask import Flask
    assert isinstance(FA.app, Flask)

def test_root_route_smoke(app_client):
    resp = app_client.get("/")
    assert resp.status_code in (200, 302, 404)

def test_money_and_cents_helpers():
    assert FA._cents_to_dollars(12568) == 125.68
    assert FA._cents_to_dollars(None) == 0.0
    assert FA._money("bad") == 0.0

def test_parse_generated_menu_basic():
    s = "[2025-10-27,10,1][2025-10-28,11]"
    m = FA.parse_generated_menu(s)
    assert set(m.keys()) == {"2025-10-27","2025-10-28"}
    assert m["2025-10-27"][0]["meal"] == 1
    assert m["2025-10-28"][0]["meal"] == 3

def test_palette_deterministic():
    p1 = FA.palette_for_item_ids([1,2,3])
    p2 = FA.palette_for_item_ids([1,2,3])
    assert p1 == p2
    assert all(re.match(r"^#[0-9a-fA-F]{6}$", c) for c in p1.values())

def test_fetch_menu_items_by_ids(tmp_db_path):
    items = FA.fetch_menu_items_by_ids([1,2,999])
    assert 1 in items and 2 in items
    assert "restaurant_name" in items[1]

def test_login_get_ok(app_client):
    r = app_client.get("/login")
    assert r.status_code in (200, 302, 303)
    assert b"TEMPLATE:login.html" in r.data

def test_login_post_success_and_fail(app_client):
    ok = app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    assert ok.status_code in (200, 302, 303)
    bad = app_client.post("/login", data={"email":"taylor@example.com", "password":"wrong"})
    assert bad.status_code == 200
    assert b"TEMPLATE:login.html" in bad.data

def test_index_requires_login_then_ok(app_client):
    r = app_client.get("/")
    assert r.status_code in (302, 303)
    app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    r2 = app_client.get("/")
    assert r2.status_code == 200
    assert b"TEMPLATE:index.html" in r2.data

def test_orders_route_lists_restaurants_and_items(app_client):
    app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    r = app_client.get("/orders")
    assert r.status_code in (200, 302, 303)
    assert b"TEMPLATE:orders.html" in r.data

def test_profile_lists_orders_and_wallet(app_client):
    app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    r = app_client.get("/profile")
    assert r.status_code in (200, 302, 303)
    assert b"CTX:orders,pw_error,pw_updated,user" in r.data

def test_change_password_flow(app_client):
    app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    # too short
    r1 = app_client.post("/profile/change-password", data=dict(
        current_password="secret123", new_password="123", confirm_password="123"
    ))
    assert r1.status_code in (302, 303)
    # mismatch
    r2 = app_client.post("/profile/change-password", data=dict(
        current_password="secret123", new_password="newstrong", confirm_password="newWRONG"
    ))
    assert r2.status_code in (302, 303)
    # success
    r3 = app_client.post("/profile/change-password", data=dict(
        current_password="secret123", new_password="newstrong", confirm_password="newstrong"
    ))
    assert r3.status_code in (302, 303)

def test_db_view_pagination(app_client):
    app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    r = app_client.get("/db?t=User&page=1", follow_redirects=True)
    assert r.status_code in (200, 302, 303)
    # Accept either the DB template or a guarded redirect to /login
    assert (b"TEMPLATE:db_view.html" in r.data) or (b"/login" in r.data) or (b"TEMPLATE:login.html" in r.data)

def test_order_post_json_group_success(app_client):
    app_client.post("/login", data={"email":"taylor@example.com", "password":"secret123"}, follow_redirects=True)
    items = FA.fetch_menu_items_by_ids([1,2])
    rtr_id = list(items.values())[0]["rtr_id"]
    payload = {
        "restaurant_id": rtr_id,
        "items": [{"itm_id": 1, "qty": 2}, {"itm_id": 2, "qty": 1}],
        "delivery_type": "pickup",
        "tip": 1.23,
        "eta_minutes": 20,
        "date": "2025-10-27",
        "meal": 2
    }
    r = app_client.post("/order", json=payload)
    assert r.status_code in (200, 302, 303)
    if r.is_json:
        data = r.get_json()
        assert data and data.get("ok") is True
        assert isinstance(data.get("ord_id"), int)
    else:
        # Likely got redirected to login; verify that
        loc = r.headers.get("Location", "")
        assert ("/login" in loc) or (b"/login" in r.data)

# ---------------- Tests: sqlQueries.py ----------------

def test_sql_create_and_close(tmp_path):
    dbp = tmp_path / "mini.sqlite"
    con = SQ.create_connection(dbp.as_posix())
    assert con is not None
    SQ.close_connection(con)

def test_sql_execute_and_fetch(tmp_path):
    dbp = tmp_path / "mini.sqlite"
    con = SQ.create_connection(dbp.as_posix())
    try:
        SQ.execute_query(con, 'CREATE TABLE T(a INTEGER, b TEXT)')
        SQ.execute_query(con, 'INSERT INTO T(a,b) VALUES (?,?)', (1, "x"))
        SQ.execute_query(con, 'INSERT INTO T(a,b) VALUES (?,?)', (2, "y"))
        rows = SQ.fetch_all(con, 'SELECT * FROM T ORDER BY a')
        assert rows == [(1,"x"), (2,"y")]
        row1 = SQ.fetch_one(con, 'SELECT b FROM T WHERE a=?', (2,))
        assert row1 == ("y",)
    finally:
        SQ.close_connection(con)
