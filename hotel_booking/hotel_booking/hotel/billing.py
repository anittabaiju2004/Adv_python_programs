"""Payment & Invoice module: nightly tariff pricing, GST, bills, payments and
refunds, invoice numbering and PDF tax invoices."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from .auth import log_activity
from .database import JSONDatabase
from .utils import (EXTRA_BED_RATE, HOTEL_ADDRESS, HOTEL_GSTIN, HOTEL_NAME, HOTEL_PHONE, MAX_DISCOUNT,
                    PAYMENT_MODES, SAC_ACCOMMODATION, SERVICE_TYPES, WEEKEND_NIGHTS,
                    WEEKEND_SURCHARGE, HotelError, NotFoundError, ValidationError, financial_year, gst,
                    nights_between, now_str, room_gst_rate, rupees_in_words, validate_amount,
                    validate_choice, validate_text)


# ================================================================== pricing
def price_nights(base_rate: float, check_in: date, check_out: date, extra_bed: bool = False,
                 discount_pct: float = 0.0) -> list[dict]:
    """Tariff for each night. Weekend nights carry a surcharge; an extra bed is
    added per night; the discount applies to the whole nightly tariff. GST is
    decided per night from the final tariff (<= 7,500 -> 5 %, above -> 18 %)."""
    if not 0 <= discount_pct <= MAX_DISCOUNT:
        raise ValidationError(f"Discount must be between 0 and {MAX_DISCOUNT:g} %.")
    nights = []
    for d in nights_between(check_in, check_out):
        weekend = d.weekday() in WEEKEND_NIGHTS
        rate = base_rate * (1 + WEEKEND_SURCHARGE / 100) if weekend else base_rate
        gross = rate + (EXTRA_BED_RATE if extra_bed else 0)
        tariff = round(gross * (1 - discount_pct / 100), 2)
        g_rate = room_gst_rate(tariff)
        nights.append({"date": d.isoformat(), "weekend": weekend, "base": round(rate, 2),
                       "extra_bed": EXTRA_BED_RATE if extra_bed else 0.0,
                       "discount": round(gross - tariff, 2), "tariff": tariff, "gst_rate": g_rate,
                       "gst": gst(tariff, g_rate)})
    return nights


def compute_bill(booking: dict, payments: list[dict]) -> dict:
    """Full bill for a booking: room nights + extra services, GST split into
    CGST/SGST, rounded total, payments and balance."""
    room_taxable = round(sum(n["tariff"] for n in booking["nights_detail"]), 2)
    room_gst = round(sum(n["gst"] for n in booking["nights_detail"]), 2)
    extras_taxable = round(sum(c["amount"] for c in booking["charges"]), 2)
    extras_gst = round(sum(c["gst"] for c in booking["charges"]), 2)
    by_rate = defaultdict(lambda: {"taxable": 0.0, "gst": 0.0})
    for item in booking["nights_detail"] + booking["charges"]:
        amt = item.get("tariff", item.get("amount"))
        by_rate[item["gst_rate"]]["taxable"] = round(by_rate[item["gst_rate"]]["taxable"] + amt, 2)
        by_rate[item["gst_rate"]]["gst"] = round(by_rate[item["gst_rate"]]["gst"] + item["gst"], 2)
    taxable = round(room_taxable + extras_taxable, 2)
    total_gst = round(room_gst + extras_gst, 2)
    exact = round(taxable + total_gst, 2)
    grand = float(round(exact))
    paid = round(sum(p["amount"] for p in payments), 2)
    return {"room_taxable": room_taxable, "room_gst": room_gst, "extras_taxable": extras_taxable,
            "extras_gst": extras_gst, "taxable": taxable, "gst": total_gst,
            "cgst": round(total_gst / 2, 2), "sgst": round(total_gst - round(total_gst / 2, 2), 2),
            "gst_by_rate": {f"{k:g}": v for k, v in sorted(by_rate.items())},
            "round_off": round(grand - exact, 2), "grand_total": grand, "paid": paid,
            "balance": round(grand - paid, 2)}


# ================================================================= payments
class BillingManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def _booking(self, booking_id: str) -> dict:
        b = self.db.find_one("bookings", booking_id=str(booking_id or "").strip().upper())
        if not b:
            raise NotFoundError(f"Booking '{booking_id}' not found.")
        return b

    def payments(self, booking_id: str) -> list[dict]:
        return sorted(self.db.find("payments", booking_id=booking_id.upper()), key=lambda p: p["at"])

    def paid(self, booking_id: str) -> float:
        return round(sum(p["amount"] for p in self.payments(booking_id)), 2)

    def record_payment(self, booking_id: str, amount, mode: str, reference: str = "",
                       kind: str = "PAYMENT") -> dict:
        b = self._booking(booking_id)
        if b["status"] in ("CANCELLED", "NO_SHOW", "CHECKED_OUT") and kind == "PAYMENT":
            raise HotelError(f"Booking is {b['status'].replace('_', ' ').lower()}; no further payments.")
        amount = validate_amount(amount)
        mode = validate_choice(mode, PAYMENT_MODES, "payment mode")
        reference = validate_text(reference, "Reference", 40)
        if mode in ("UPI", "Card", "Net Banking") and kind == "PAYMENT" and not reference:
            raise ValidationError(f"Enter the transaction reference for {mode} payments.")
        bill = self.bill(b["booking_id"])
        if kind == "PAYMENT" and amount > max(bill["balance"], 0) + 0.005:
            raise ValidationError(f"Payment exceeds the balance due ({bill['balance']:,.2f}).")
        p = {"payment_id": f"P{len(self.db.all('payments')) + 1:05d}", "booking_id": b["booking_id"],
             "amount": amount if kind == "PAYMENT" else -amount, "mode": mode, "reference": reference,
             "kind": kind, "at": now_str(), "by": self.actor}
        self.db.insert("payments", p)
        log_activity(self.db, self.actor, kind, f"{b['booking_id']} {amount:.2f} {mode}")
        return p

    def refund(self, booking_id: str, amount, mode: str, reason: str = "") -> dict:
        amount = validate_amount(amount)
        if amount > self.paid(booking_id) + 0.005:
            raise ValidationError("Refund exceeds the amount paid.")
        return self.record_payment(booking_id, amount, mode, reason or "Refund", kind="REFUND")

    def bill(self, booking_id: str) -> dict:
        b = self._booking(booking_id)
        return compute_bill(b, self.payments(b["booking_id"]))

    def next_invoice_no(self, on: date) -> str:
        fy = financial_year(on)
        prefix = f"INV/{fy}/"
        nums = [int(b["invoice_no"].split("/")[-1]) for b in self.db.all("bookings")
                if (b.get("invoice_no") or "").startswith(prefix)]
        return f"{prefix}{(max(nums) + 1) if nums else 1:04d}"

    # ------------------------------------------------------------- invoice PDF
    def invoice_pdf(self, booking_id: str, out_dir: Path | str, proforma: bool = False) -> Path:
        """Tax invoice (after check-out) or pro-forma bill (during the stay)."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        b = self._booking(booking_id)
        if not proforma and not b.get("invoice_no"):
            raise HotelError("Invoice is issued at check-out. Use the pro-forma bill during the stay.")
        bill = b["invoice"] if (b.get("invoice") and not proforma) else self.bill(b["booking_id"])
        cust = self.db.find_one("customers", customer_id=b["customer_id"]) or {}
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = (b["invoice_no"].replace("/", "-") if not proforma else f"PROFORMA-{b['booking_id']}")
        path = out_dir / f"{stem}.pdf"
        styles = getSampleStyleSheet()
        small = ParagraphStyle("s", parent=styles["Normal"], fontSize=8.5, leading=11)
        brand = colors.HexColor("#7a3e12")
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                topMargin=1.3 * cm, bottomMargin=1.3 * cm, title=stem)

        head = Table([[Paragraph(f"<font size=16 color='#7a3e12'><b>{escape(HOTEL_NAME)}</b></font><br/>"
                                 f"{escape(HOTEL_ADDRESS)}<br/>Phone {HOTEL_PHONE}<br/>GSTIN: {HOTEL_GSTIN}", small),
                       Paragraph(f"<font size=13><b>{'PRO-FORMA BILL' if proforma else 'TAX INVOICE'}</b></font><br/>"
                                 + (f"Invoice No: <b>{b['invoice_no']}</b><br/>Date: {b['invoice_date']}<br/>"
                                    if not proforma else f"Date: {date.today().isoformat()}<br/>")
                                 + f"Booking: {b['booking_id']}", small)]],
                     colWidths=[11 * cm, 6.8 * cm])
        head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, brand),
                                  ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]))
        guest = Table([[Paragraph(f"<b>Bill to</b><br/>{escape(cust.get('name', ''))} ({b['customer_id']})<br/>"
                                  f"{escape(cust.get('address', '') or '')}<br/>Phone {cust.get('phone', '')}"
                                  + (f"<br/>GSTIN: {cust['gstin']}" if cust.get("gstin") else ""), small),
                        Paragraph(f"<b>Stay</b><br/>Room {b['room_no']} ({b['category']})<br/>"
                                  f"Check-in: {b.get('actual_check_in', b['check_in'])[:16].replace('T', ' ')}<br/>"
                                  f"Check-out: {(b.get('actual_check_out') or b['check_out'])[:16].replace('T', ' ')}<br/>"
                                  f"Guests: {b['adults']} adult(s)" + (f", {b['children']} child(ren)" if b['children'] else ""),
                                  small)]], colWidths=[9 * cm, 8.8 * cm])
        guest.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8)]))

        rows = [["#", "Description", "SAC", "Taxable", "GST %", "GST", "Amount"]]
        for i, n in enumerate(b["nights_detail"], 1):
            desc = f"Room {b['room_no']} — night of {n['date']}" + (" (weekend)" if n["weekend"] else "") + \
                   (" + extra bed" if n["extra_bed"] else "") + (f" (disc. {n['discount']:,.2f})" if n["discount"] else "")
            rows.append([str(i), Paragraph(desc, small), SAC_ACCOMMODATION, f"{n['tariff']:,.2f}",
                         f"{n['gst_rate']:g}", f"{n['gst']:,.2f}", f"{n['tariff'] + n['gst']:,.2f}"])
        for j, c in enumerate(b["charges"], len(b["nights_detail"]) + 1):
            rows.append([str(j), Paragraph(f"{escape(c['service'])}: {escape(c['description'])} ({c['date']})", small),
                         SERVICE_TYPES[c["service"]]["sac"], f"{c['amount']:,.2f}", f"{c['gst_rate']:g}",
                         f"{c['gst']:,.2f}", f"{c['amount'] + c['gst']:,.2f}"])
        items = Table(rows, colWidths=[0.8 * cm, 7.4 * cm, 1.6 * cm, 2.2 * cm, 1.3 * cm, 1.9 * cm, 2.4 * cm],
                      repeatRows=1)
        items.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), brand), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                                   ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6c7b8")),
                                   ("ALIGN", (3, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        tot = [["Taxable value", f"{bill['taxable']:,.2f}"]]
        for rate, v in bill["gst_by_rate"].items():
            half = v["gst"] / 2
            tot += [[f"CGST @ {float(rate) / 2:g}% on {v['taxable']:,.2f}", f"{half:,.2f}"],
                    [f"SGST @ {float(rate) / 2:g}% on {v['taxable']:,.2f}", f"{v['gst'] - half:,.2f}"]]
        tot += [["Round off", f"{bill['round_off']:+,.2f}"], ["GRAND TOTAL", f"{bill['grand_total']:,.2f}"],
                ["Paid", f"{bill['paid']:,.2f}"], ["Balance", f"{bill['balance']:,.2f}"]]
        totals = Table(tot, colWidths=[6 * cm, 3 * cm], hAlign="RIGHT")
        gi = len(tot) - 3
        totals.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                    ("FONTNAME", (0, gi), (-1, gi), "Helvetica-Bold"),
                                    ("BACKGROUND", (0, gi), (-1, gi), colors.HexColor("#f3e9df")),
                                    ("LINEABOVE", (0, gi), (-1, gi), 0.8, brand)]))
        pay_rows = [[p["at"][:16].replace("T", " "), p["kind"].title(), p["mode"], p["reference"] or "-",
                     f"{p['amount']:,.2f}"] for p in self.payments(b["booking_id"])]
        story = [head, guest, Spacer(1, 6), items, Spacer(1, 8), totals, Spacer(1, 4),
                 Paragraph(f"<i>Amount in words: {rupees_in_words(bill['grand_total'])}</i>", small)]
        if pay_rows:
            pt = Table([["Date", "Type", "Mode", "Reference", "Amount"]] + pay_rows,
                       colWidths=[3.6 * cm, 2.6 * cm, 2.6 * cm, 5 * cm, 3 * cm], hAlign="LEFT")
            pt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey), ("ALIGN", (4, 0), (4, -1), "RIGHT")]))
            story += [Spacer(1, 12), Paragraph("<b>Payments</b>", small), pt]
        story += [Spacer(1, 18), Paragraph("Room tariff GST: 5% for tariff up to ₹7,500 per night, 18% above "
                                           "(notified rates from 22 Sep 2025). Thank you for staying with us!"
                                           .replace("₹", "Rs. "), small),
                  Paragraph("This is a computer-generated invoice.", small)]
        doc.build(story)
        return path
