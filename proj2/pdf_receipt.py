# pdf_receipt.py
import json
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from sqlQueries import create_connection, close_connection, fetch_one, fetch_all

def _safe_str(x):
    return "" if x is None else str(x)

def _money(x):
    try:
        return f"${float(x):.2f}"
    except Exception:
        return ""

def _dt_display(iso_str):
    if not iso_str:
        return ""
    try:
        return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str

def generate_order_receipt_pdf(db_file: str, ord_id: int) -> bytes:
    """
    Build a PDF receipt for an order.
    Uses only sqlQueries helpers to pull data.
    Returns: bytes of the PDF.
    """
    conn = create_connection(db_file)
    try:
        # Order: ord_id,rtr_id,usr_id,details,status
        orow = fetch_one(conn, 'SELECT ord_id, rtr_id, usr_id, details, status FROM "Order" WHERE ord_id = ?', (ord_id,))
        if not orow:
            raise ValueError("Order not found")

        ord_id, rtr_id, usr_id, details, status = orow

        # User
        urow = fetch_one(conn,
                         'SELECT first_name, last_name, email, phone FROM "User" WHERE usr_id = ?',
                         (usr_id,))
        first_name, last_name, email, phone = (urow or ("", "", "", ""))

        # Restaurant
        rrow = fetch_one(conn,
                         'SELECT name, address, city, state, zip, phone FROM "Restaurant" WHERE rtr_id = ?',
                         (rtr_id,))
        r_name, r_addr, r_city, r_state, r_zip, r_phone = (rrow or ("", "", "", "", "", ""))

        # Parse details JSON (new format)
        j = {}
        try:
            j = json.loads(details or "{}")
        except Exception:
            j = {}

        placed_at = _dt_display(j.get("placed_at") or j.get("time"))
        delivery_type = _safe_str(j.get("delivery_type"))
        notes = _safe_str(j.get("notes"))

        items = j.get("items") or []
        charges = j.get("charges") or {}
        subtotal = charges.get("subtotal")
        tax = charges.get("tax")
        delivery_fee = charges.get("delivery_fee")
        service_fee = charges.get("service_fee")
        tip = charges.get("tip")
        total = charges.get("total") or charges.get("grand_total") or charges.get("amount")

        # --------- Build PDF ----------
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        margin = 0.75 * inch
        y = height - margin

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, f"Receipt · Order #{ord_id}")
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.grey)
        c.drawString(margin, y - 14, f"Status: {_safe_str(status)}")
        c.drawRightString(width - margin, y - 14, f"Placed: {placed_at}")
        c.setFillColor(colors.black)
        y -= 30

        # Parties
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Billed To")
        c.setFont("Helvetica", 10)
        c.drawString(margin, y - 14, f"{_safe_str(first_name)} {_safe_str(last_name)}")
        c.drawString(margin, y - 28, f"Email: {_safe_str(email)}")
        c.drawString(margin, y - 42, f"Phone: {_safe_str(phone)}")

        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - margin, y, "Restaurant")
        c.setFont("Helvetica", 10)
        c.drawRightString(width - margin, y - 14, _safe_str(r_name))
        c.drawRightString(width - margin, y - 28, f"{_safe_str(r_addr)}")
        c.drawRightString(width - margin, y - 42, f"{_safe_str(r_city)}, {_safe_str(r_state)} {_safe_str(r_zip)}")
        c.drawRightString(width - margin, y - 56, f"Phone: {_safe_str(r_phone)}")

        y -= 78

        # Divider
        c.setStrokeColor(colors.lightgrey)
        c.line(margin, y, width - margin, y)
        y -= 16

        # Items table header
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, "Qty")
        c.drawString(margin + 40, y, "Item")
        c.drawRightString(width - margin - 140, y, "Unit")
        c.drawRightString(width - margin, y, "Line")
        y -= 12
        c.setStrokeColor(colors.lightgrey)
        c.line(margin, y, width - margin, y)
        y -= 10
        c.setFont("Helvetica", 10)

        # Items rows
        for it in items:
            qty = _safe_str(it.get("qty"))
            name = _safe_str(it.get("name"))
            unit = _money(it.get("unit_price"))
            line = _money(it.get("line_total"))

            c.drawString(margin, y, qty)
            c.drawString(margin + 40, y, name[:60])
            c.drawRightString(width - margin - 140, y, unit)
            c.drawRightString(width - margin, y, line)
            y -= 14
            if y < 1.25 * inch:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 10)

        # Divider
        y -= 6
        c.setStrokeColor(colors.lightgrey)
        c.line(margin, y, width - margin, y)
        y -= 12

        # Charges
        c.setFont("Helvetica", 10)
        def row(label, value):
            nonlocal y
            if value is None or value == "":
                return
            c.drawRightString(width - margin - 140, y, label)
            c.drawRightString(width - margin, y, _money(value))
            y -= 14

        row("Subtotal", subtotal)
        row("Tax", tax)
        row("Delivery fee", delivery_fee)
        row("Service fee", service_fee)
        row("Tip", tip)

        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - margin - 140, y, "Total")
        c.drawRightString(width - margin, y, _money(total))
        y -= 18

        # Footer notes
        c.setFont("Helvetica", 9)
        if delivery_type:
            c.drawString(margin, y, f"Delivery type: {delivery_type}")
            y -= 12
        if notes:
            c.drawString(margin, y, f"Notes: {notes[:120]}")
            y -= 12

        c.setFillColor(colors.grey)
        c.drawString(margin, 0.6 * inch, "Thank you for your order!")
        c.setFillColor(colors.black)

        c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()
        buf.close()
        return pdf_bytes

    finally:
        close_connection(conn)
