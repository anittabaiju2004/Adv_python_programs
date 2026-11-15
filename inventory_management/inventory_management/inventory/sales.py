"""Sales & Billing: GST invoices with discounts, automatic stock deduction,
profit capture, payments / credit, cancellation and PDF tax invoices."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from .auth import log_activity
from .customers import CustomerManager
from .database import JSONDatabase
from .products import ProductManager
from .utils import (BUSINESS_ADDRESS, BUSINESS_GSTIN, BUSINESS_NAME, BUSINESS_PHONE, BUSINESS_STATE,
                    MAX_LINE_DISCOUNT, PAYMENT_MODES, WALK_IN_CUSTOMER, InventoryError, NotFoundError,
                    StockError, ValidationError, financial_year, gst_split, is_inter_state, now_str, parse_date,
                    rupees_in_words, validate_amount, validate_choice, validate_qty, validate_text)


# ====================================================================== maths
def compute_lines(lines: list[dict], inter_state: bool) -> dict:
    """Totals for an invoice / purchase. Each line needs qty, rate (excl. GST),
    discount_pct and gst_rate. Adds gross, discount, taxable, tax and total per
    line; returns document totals with a GST summary by rate and round-off."""
    out_lines, summary = [], defaultdict(lambda: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0})
    for ln in lines:
        gross = round(ln["qty"] * ln["rate"], 2)
        disc = round(gross * ln.get("discount_pct", 0) / 100, 2)
        taxable = round(gross - disc, 2)
        tax = gst_split(taxable, ln["gst_rate"], inter_state)
        out_lines.append({**ln, "gross": gross, "discount": disc, "taxable": taxable, **tax,
                          "total": round(taxable + tax["tax"], 2)})
        s = summary[ln["gst_rate"]]
        for k in ("cgst", "sgst", "igst"):
            s[k] = round(s[k] + tax[k], 2)
        s["taxable"] = round(s["taxable"] + taxable, 2)
    tot = {k: round(sum(l[k] for l in out_lines), 2) for k in ("gross", "discount", "taxable", "cgst", "sgst", "igst")}
    tot["tax"] = round(tot["cgst"] + tot["sgst"] + tot["igst"], 2)
    exact = round(tot["taxable"] + tot["tax"], 2)
    grand = float(round(exact))
    return {"lines": out_lines, **tot, "round_off": round(grand - exact, 2), "grand_total": grand,
            "inter_state": inter_state, "gst_summary": {f"{k:g}": v for k, v in sorted(summary.items())}}


def payment_status(total: float, paid: float) -> str:
    if paid <= 0.005:
        return "UNPAID"
    return "PAID" if paid >= total - 0.005 else "PARTIAL"


# ===================================================================== sales
class SalesManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.products = ProductManager(db, actor)
        self.customers = CustomerManager(db, actor)

    def _next_ids(self, on: date) -> tuple[str, str]:
        sales = self.db.all("sales")
        prefix = f"INV/{financial_year(on)}/"
        nums = [int(s["invoice_no"].split("/")[-1]) for s in sales if s["invoice_no"].startswith(prefix)]
        return f"S{len(sales) + 1:05d}", f"{prefix}{(max(nums) + 1) if nums else 1:04d}"

    def build_lines(self, items: list[dict], allow_discount: bool = True) -> list[dict]:
        """items: [{product_id, qty, price (optional), discount_pct (optional)}]"""
        if not items:
            raise ValidationError("Add at least one item.")
        lines, seen = [], set()
        for it in items:
            p = self.products.get(it["product_id"])
            if not p["active"]:
                raise InventoryError(f"{p['name']} is discontinued.")
            if p["product_id"] in seen:
                raise ValidationError(f"{p['name']} is listed twice; combine the quantities.")
            seen.add(p["product_id"])
            qty = validate_qty(it["qty"], p["unit"])
            if qty > p["stock"] + 0.0005:
                raise StockError(f"Only {p['stock']:g} {p['unit']} of {p['name']} in stock.")
            rate = validate_amount(it.get("price") or p["selling_price"], "Price")
            disc = float(it.get("discount_pct") or 0)
            if not 0 <= disc <= MAX_LINE_DISCOUNT:
                raise ValidationError(f"Discount must be between 0 and {MAX_LINE_DISCOUNT:g} %.")
            if disc and not allow_discount:
                raise ValidationError("You are not allowed to give discounts.")
            lines.append({"product_id": p["product_id"], "name": p["name"], "hsn": p["hsn"], "unit": p["unit"],
                          "qty": qty, "rate": rate, "discount_pct": disc, "gst_rate": p["gst_rate"],
                          "unit_cost": round(p["avg_cost"], 4)})
        return lines

    def quote(self, customer_id: str, items: list[dict]) -> dict:
        c = self.customers.get(customer_id)
        return compute_lines(self.build_lines(items), is_inter_state(c["state"]))

    def create(self, customer_id: str, items: list[dict], payment_mode: str = "Cash", amount_paid=None,
               reference: str = "", on=None, notes: str = "") -> dict:
        c = self.customers.get(customer_id)
        if not c["active"]:
            raise InventoryError(f"Customer {c['name']} is inactive.")
        on = parse_date(on or date.today())
        doc = compute_lines(self.build_lines(items), is_inter_state(c["state"]))
        mode = validate_choice(payment_mode, PAYMENT_MODES, "payment mode")
        paid = 0.0 if mode == "Credit" else (doc["grand_total"] if amount_paid in (None, "") else
                                            validate_amount(amount_paid, "Amount paid", 0, doc["grand_total"]))
        if paid < doc["grand_total"] - 0.005 and c["customer_id"] == WALK_IN_CUSTOMER:
            raise ValidationError("Credit / part payment is only allowed for registered customers.")
        if mode in ("UPI", "Card", "Bank Transfer") and paid and not str(reference or "").strip():
            raise ValidationError(f"Enter the transaction reference for {mode} payments.")
        cost = round(sum(l["qty"] * l["unit_cost"] for l in doc["lines"]), 2)
        sale_id, invoice_no = self._next_ids(on)
        payments = [{"at": now_str(), "amount": paid, "mode": mode, "reference": validate_text(reference, "Reference", 40)}] \
            if paid else []
        sale = {"sale_id": sale_id, "invoice_no": invoice_no, "date": on.isoformat(), "customer_id": c["customer_id"],
                "customer_name": c["name"], "customer_gstin": c["gstin"], "place_of_supply": c["state"],
                **doc, "cost": cost, "profit": round(doc["taxable"] - cost, 2), "payment_mode": mode,
                "amount_paid": paid, "payment_status": payment_status(doc["grand_total"], paid), "payments": payments,
                "status": "COMPLETED", "notes": validate_text(notes, "Notes", 120), "created_by": self.actor,
                "created_at": now_str(), "cancelled_at": None, "cancel_reason": None}
        for l in doc["lines"]:          # stock was checked in build_lines; move() re-checks atomically per item
            self.products.move(l["product_id"], -l["qty"], "SALE", invoice_no)
        self.db.insert("sales", sale)
        log_activity(self.db, self.actor, "SALE", f"{invoice_no} {c['name']} {doc['grand_total']:.2f}")
        return sale

    def get(self, ref: str) -> dict:
        key = str(ref or "").strip().upper()
        s = self.db.find_one("sales", sale_id=key) or self.db.find_one("sales", invoice_no=key)
        if not s:
            raise NotFoundError(f"Sale '{ref}' not found.")
        return s

    def receive_payment(self, ref: str, amount, mode: str, reference: str = "") -> dict:
        s = self.get(ref)
        if s["status"] != "COMPLETED":
            raise InventoryError("Invoice is cancelled.")
        due = round(s["grand_total"] - s["amount_paid"], 2)
        if due <= 0.005:
            raise InventoryError("This invoice is already fully paid.")
        amount = validate_amount(amount, "Amount", 0.01, due)
        mode = validate_choice(mode, [m for m in PAYMENT_MODES if m != "Credit"], "payment mode")
        if mode != "Cash" and not str(reference or "").strip():
            raise ValidationError(f"Enter the transaction reference for {mode} payments.")
        paid = round(s["amount_paid"] + amount, 2)
        pays = s["payments"] + [{"at": now_str(), "amount": amount, "mode": mode,
                                 "reference": validate_text(reference, "Reference", 40)}]
        log_activity(self.db, self.actor, "PAYMENT_RECEIVED", f"{s['invoice_no']} {amount:.2f}")
        return self.db.update("sales", "sale_id", s["sale_id"], {"amount_paid": paid, "payments": pays,
                                                                 "payment_status": payment_status(s["grand_total"], paid)})

    def cancel(self, ref: str, reason: str) -> dict:
        """Cancel an invoice: items go back into stock. Any amount paid is shown as refundable."""
        s = self.get(ref)
        if s["status"] == "CANCELLED":
            raise InventoryError("Invoice is already cancelled.")
        for l in s["lines"]:
            self.products.move(l["product_id"], l["qty"], "SALE_CANCEL", s["invoice_no"], unit_cost=l["unit_cost"])
        log_activity(self.db, self.actor, "SALE_CANCELLED", f"{s['invoice_no']} ({reason})")
        return self.db.update("sales", "sale_id", s["sale_id"],
                              {"status": "CANCELLED", "cancelled_at": now_str(),
                               "cancel_reason": validate_text(reason, "Reason", 120, required=True)})

    def list(self, start=None, end=None, customer_id: str | None = None, include_cancelled: bool = False) -> list[dict]:
        ss = self.db.all("sales")
        if not include_cancelled:
            ss = [s for s in ss if s["status"] == "COMPLETED"]
        if start:
            ss = [s for s in ss if s["date"] >= parse_date(start).isoformat()]
        if end:
            ss = [s for s in ss if s["date"] <= parse_date(end).isoformat()]
        if customer_id:
            ss = [s for s in ss if s["customer_id"] == customer_id.upper()]
        return sorted(ss, key=lambda s: (s["date"], s["sale_id"]), reverse=True)

    # ------------------------------------------------------------- PDF invoice
    def invoice_pdf(self, ref: str, out_dir: Path | str) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        s = self.get(ref)
        cust = self.customers.get(s["customer_id"])
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{s['invoice_no'].replace('/', '-')}.pdf"
        styles = getSampleStyleSheet()
        sm = ParagraphStyle("s", parent=styles["Normal"], fontSize=8.5, leading=11)
        brand = colors.HexColor("#1b5e4b")
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.4 * cm, rightMargin=1.4 * cm,
                                topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=s["invoice_no"])
        title = "TAX INVOICE" + ("  (CANCELLED)" if s["status"] == "CANCELLED" else "")
        head = Table([[Paragraph(f"<font size=15 color='#1b5e4b'><b>{escape(BUSINESS_NAME)}</b></font><br/>"
                                 f"{escape(BUSINESS_ADDRESS)}<br/>Phone {BUSINESS_PHONE}<br/>GSTIN: {BUSINESS_GSTIN}", sm),
                       Paragraph(f"<font size=13><b>{title}</b></font><br/>Invoice No: <b>{s['invoice_no']}</b><br/>"
                                 f"Date: {s['date']}<br/>Place of supply: {s['place_of_supply']}"
                                 + (" (inter-state)" if s["inter_state"] else ""), sm)]],
                     colWidths=[11 * cm, 7.2 * cm])
        head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, brand),
                                  ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]))
        bill_to = Paragraph(f"<b>Bill to:</b> {escape(cust['name'])} ({cust['customer_id']})"
                            + (f"<br/>{escape(cust['address'])}" if cust["address"] else "")
                            + (f"<br/>Phone {cust['phone']}" if cust["phone"] else "")
                            + (f"<br/>GSTIN: {cust['gstin']}" if cust["gstin"] else ""), sm)
        inter = s["inter_state"]
        hdr = ["#", "Item", "HSN", "Qty", "Rate", "Disc.", "Taxable", "GST %", "IGST" if inter else "Tax", "Total"]
        rows = [hdr]
        for i, l in enumerate(s["lines"], 1):
            rows.append([str(i), Paragraph(escape(l["name"]), sm), l["hsn"], f"{l['qty']:g} {l['unit']}",
                         f"{l['rate']:,.2f}", f"{l['discount']:,.2f}" if l["discount"] else "-", f"{l['taxable']:,.2f}",
                         f"{l['gst_rate']:g}", f"{l['tax']:,.2f}", f"{l['total']:,.2f}"])
        items = Table(rows, colWidths=[0.7 * cm, 5 * cm, 1.4 * cm, 1.8 * cm, 1.7 * cm, 1.4 * cm, 1.9 * cm,
                                       1.2 * cm, 1.8 * cm, 1.9 * cm], repeatRows=1)
        items.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), brand), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                                   ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bcd3cb")),
                                   ("ALIGN", (3, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        gst_rows = [["GST %", "Taxable", "IGST"] if inter else ["GST %", "Taxable", "CGST", "SGST"]]
        for rate, v in s["gst_summary"].items():
            gst_rows.append([rate, f"{v['taxable']:,.2f}"] + ([f"{v['igst']:,.2f}"] if inter else
                                                             [f"{v['cgst']:,.2f}", f"{v['sgst']:,.2f}"]))
        gst_tbl = Table(gst_rows, colWidths=[1.4 * cm, 2.4 * cm] + [2 * cm] * (1 if inter else 2), hAlign="LEFT")
        gst_tbl.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                     ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
        tot_rows = [["Gross amount", f"{s['gross']:,.2f}"]]
        if s["discount"]:
            tot_rows.append(["Less: discount", f"-{s['discount']:,.2f}"])
        tot_rows.append(["Taxable value", f"{s['taxable']:,.2f}"])
        tot_rows += [["IGST", f"{s['igst']:,.2f}"]] if inter else [["CGST", f"{s['cgst']:,.2f}"], ["SGST", f"{s['sgst']:,.2f}"]]
        tot_rows += [["Round off", f"{s['round_off']:+,.2f}"], ["GRAND TOTAL", f"{s['grand_total']:,.2f}"],
                     ["Paid", f"{s['amount_paid']:,.2f}"], ["Balance due", f"{s['grand_total'] - s['amount_paid']:,.2f}"]]
        tot = Table(tot_rows, colWidths=[4 * cm, 3 * cm])
        gi = len(tot_rows) - 3
        tot.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                 ("FONTNAME", (0, gi), (-1, gi), "Helvetica-Bold"),
                                 ("BACKGROUND", (0, gi), (-1, gi), colors.HexColor("#e3efea")),
                                 ("LINEABOVE", (0, gi), (-1, gi), 0.8, brand)]))
        bottom = Table([[gst_tbl, tot]], colWidths=[10.8 * cm, 7.4 * cm])
        bottom.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        pay = ", ".join(f"{p['mode']} {p['amount']:,.2f}" + (f" ({p['reference']})" if p["reference"] else "")
                        for p in s["payments"]) or "Credit (unpaid)"
        story = [head, Spacer(1, 6), bill_to, Spacer(1, 8), items, Spacer(1, 8), bottom, Spacer(1, 6),
                 Paragraph(f"<i>Amount in words: {rupees_in_words(s['grand_total'])}</i>", sm),
                 Paragraph(f"Payment: {escape(pay)} · Status: {s['payment_status']}", sm)]
        if s["status"] == "CANCELLED":
            story.append(Paragraph(f"<font color='red'><b>Cancelled on {s['cancelled_at'][:10]}: "
                                   f"{escape(s['cancel_reason'])}</b></font>", sm))
        story += [Spacer(1, 20), Paragraph("Goods once sold can be exchanged within 7 days with the bill. "
                                           "This is a computer-generated invoice.", sm)]
        doc.build(story)
        return path
