"""
Flask_app.py — Minimal Flask application for CSC510 Project 2.

Features:
- Session-based login/logout and profile display
- Local Swagger UI (/apidocs) & tiny API blueprint (/api)
- Admin-gated DB table viewer (whitelisted tables)
- SQLite helpers via sqlQueries.py
"""

import os
import math
from datetime import timedelta
from functools import wraps
from typing import Optional, Iterable
from pathlib import Path
from flask import (
    Flask,
    render_template,
    url_for,
    redirect,
    request,
    session,
    jsonify,
    Blueprint,
    flash,
)
from werkzeug.security import check_password_hash
from flasgger import Swagger, swag_from
from dotenv import load_dotenv

from sqlQueries import create_connection, close_connection, fetch_one

# -------------------------
# Configuration & Bootstrap
# -------------------------

ENV_PATH = Path(__file__).with_name(".env")  # <repo>/proj2/.env
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = Flask(__name__)

# Secret + session settings (env-driven; local-safe defaults)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-insecure")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# If you run behind HTTPS locally, you may also set:
# app.config["SESSION_COOKIE_SECURE"] = True

# Path to local SQLite DB file
db_file = os.path.join(os.path.dirname(__file__), "CSC510_DB.db")

# Optional: admin allowlist (comma-separated emails in .env)
ADMIN_EMAILS: set[str] = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "").split(",")
    if e.strip()
}
print(f"[BOOT] CWD={os.getcwd()}  ENV_PATH={ENV_PATH}  ADMIN_EMAILS={ADMIN_EMAILS}")

# Local Swagger UI and OpenAPI JSON at /apidocs and /apispec_1.json
Swagger(app)


# -------------------------
# Helpers & Decorators
# -------------------------

def login_required(view_func):
    """Decorator that redirects to /login if no active session user."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("Username"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator restricting access to admin users only.

    Admin is determined by:
    1) Session flag `is_admin=True` (set at login if email is in ADMIN_EMAILS), OR
    2) You may extend this with a DB role column later.
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("Username"):
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            flash("Admin access required.", "warning")
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)
    return wrapper


def is_admin_email(email: Optional[str]) -> bool:
    """Check if an email matches the configured admin allowlist."""
    return bool(email and email.lower() in ADMIN_EMAILS)


# -------------------------
# Minimal API (for docs & FE)
# -------------------------

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
@swag_from(
    {
        "tags": ["meta"],
        "summary": "Health check",
        "responses": {200: {"description": "OK"}},
    }
)
def health():
    """Health probe endpoint."""
    return jsonify(status="ok")


@api_bp.get("/me")
@swag_from(
    {
        "tags": ["user"],
        "summary": "Current user from session",
        "responses": {
            200: {"description": "User info"},
            401: {"description": "Not logged in"},
        },
    }
)
def me():
    """Return a minimal view of the current user from the session.

    NOTE: In your current app, you store the display name under 'Username'
    and individual fields like 'Fname', 'Lname', 'Email', etc.
    """
    # BUGFIX: your old code checked 'username' (lowercase) which was never set.
    if not session.get("Username"):
        return jsonify(error="unauthorized"), 401

    return jsonify(
        {
            "Username": session.get("Username"),
            "Fname": session.get("Fname"),
            "Lname": session.get("Lname"),
            "Email": session.get("Email"),
            "Wallet": session.get("Wallet"),
        }
    )


app.register_blueprint(api_bp)


# -------------------------
# Web Views (Jinja)
# -------------------------

@app.route("/")
@login_required
def index():
    """Home page.

    Redirects to /login if no active session, else renders index.html.
    """
    return render_template("index.html", username=session["Username"])


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login (email + password).

    GET: Render login form.
    POST: Verify credentials against DB and start a session.

    Session fields set on success:
    - Fname, Lname, Username (Fname + Lname), Email, Phone, Wallet, Preferences
    - is_admin (derived from ADMIN_EMAILS)
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = create_connection(db_file)
        user = fetch_one(conn, "SELECT * FROM User WHERE email = ?", (email,))
        close_connection(conn)

        # Expected User schema:
        # usr_id, first_name, last_name, email, phone, password_HS, wallet, preferences
        if user and check_password_hash(user[5], password):
            session["Fname"] = user[1]
            session["Lname"] = user[2]
            session["Username"] = f"{user[1]} {user[2]}"
            session["Email"] = user[3]
            session["Phone"] = user[4]
            session["Wallet"] = user[6]
            session["Preferences"] = user[7]

            # Simple admin allowlist (optional)
            session["is_admin"] = is_admin_email(user[3])
            # email_value = (user[3] or "").strip().lower()  # normalize
            # session["is_admin"] = email_value in ADMIN_EMAILS

            # 30-minute rolling session
            session.permanent = True
            app.permanent_session_lifetime = timedelta(minutes=30)

            return redirect(url_for("index"))

        # Invalid
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear the session and return to /login."""
    keys: Iterable[str] = (
        "Username",
        "Fname",
        "Lname",
        "Email",
        "Phone",
        "Wallet",
        "Preferences",
        "is_admin",
    )
    for k in keys:
        session.pop(k, None)
    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():
    """User profile page (reads values from the session)."""
    return render_template(
        "profile.html",
        username=session["Username"],
        email=session.get("Email"),
        phone=session.get("Phone"),
        wallet=session.get("Wallet"),
        preferences=session.get("Preferences"),
    )


@app.route("/db")
@admin_required
def db_view():
    """Admin-only DB table viewer (read-only, whitelisted).

    Query Params:
        t: Table name (one of allowed_tables)
        page: 1-based page index (default 1)

    Renders:
        db_view.html with columns, rows, pagination metadata.
    """
    # Whitelist of tables the viewer can access
    allowed_tables = {"User", "Restaurant", "MenuItem", "Order", "Review"}

    table = request.args.get("t", "User")
    if table not in allowed_tables:
        table = "User"

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page = max(page, 1)
    per_page = 10

    conn = create_connection(db_file)
    cur = conn.cursor()

    # Total count (table name safely whitelisted above)
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0] or 0

    # Pagination math
    pages = max(math.ceil(total / per_page), 1)
    page = min(page, pages)
    offset = (page - 1) * per_page

    # Columns via PRAGMA
    cur.execute(f"PRAGMA table_info({table})")
    columns = [r[1] for r in cur.fetchall()]

    # Fetch the rows
    cur.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (per_page, offset))
    rows = cur.fetchall()

    close_connection(conn)

    start = 0 if total == 0 else offset + 1
    end = min(offset + per_page, total)

    return render_template(
        "db_view.html",
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


# -------------------------
# Run (local)
# -------------------------

if __name__ == "__main__":
    """
    DB column names:

    MenuItem: itm_id,rtr_id,name,description,price,calories,instock,restock,allergens
    Order:    ord_id,rtr_id,usr_id,details,status
    Restaurant: rtr_id,name,description,phone,email,password_HS,address,city,state,zip,hours,status
    Review:   rev_id,rtr_id,usr_id,title,rating,description
    User:     usr_id,first_name,last_name,email,phone,password_HS,wallet,preferences
    """
    # Debug server for local development only
    app.run(debug=True)
