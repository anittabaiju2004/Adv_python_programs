"""Reports: revenue, occupancy (with ADR / RevPAR), booking and customer
exports, and a PDF performance report."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .database import JSONDatabase
from .utils import (HOTEL_NAME, ROOM_CATEGORIES, SERVICE_TYPES, HotelError, ValidationError, parse_date)

STAYED = ("CHECKED_IN", "CHECKED_OUT")
ON_BOOKS = ("CONFIRMED", "CHECKED_IN", "CHECKED_OUT")


def _range(start, end) -> tuple[date, date]:
    s, e = parse_date(start, "Start date"), parse_date(end, "End date")
    if e < s:
        raise ValidationError("End date is before start date.")
    if (e - s).days > 366:
        raise ValidationError("Report period can be at most one year.")
    return s, e


class ReportGenerator:
    def __init__(self, db: JSONDatabase, report_dir: Path | str):
        self.db = db
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, stem: str, ext: str) -> Path:
        return self.report_dir / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"

    # ============================================================== revenue
    def revenue(self, start, end) -> dict:
        """Revenue from invoices issued in the period (check-outs), plus
        cancellation / no-show fees retained, and cash flow by payment mode."""
        s, e = _range(start, end)
        S, E = s.isoformat(), e.isoformat()
        invoiced = [b for b in self.db.all("bookings") if b.get("invoice_date") and S <= b["invoice_date"] <= E]
        cancelled = [b for b in self.db.all("bookings") if b["status"] in ("CANCELLED", "NO_SHOW")
                     and b.get("cancelled_at") and S <= b["cancelled_at"][:10] <= E]
        extras = defaultdict(float)
        for b in invoiced:
            for c in b["charges"]:
                extras[c["service"]] += c["amount"]
        by_cat = defaultdict(lambda: {"nights": 0, "revenue": 0.0})
        for b in invoiced:
            by_cat[b["category"]]["nights"] += b["nights"]
            by_cat[b["category"]]["revenue"] = round(by_cat[b["category"]]["revenue"] + b["invoice"]["room_taxable"], 2)
        payments = [p for p in self.db.all("payments") if S <= p["at"][:10] <= E]
        by_mode = defaultdict(float)
        for p in payments:
            by_mode[p["mode"]] += p["amount"]
        daily = defaultdict(float)
        for b in invoiced:
            daily[b["invoice_date"]] += b["invoice"]["taxable"]
        room = round(sum(b["invoice"]["room_taxable"] for b in invoiced), 2)
        nights = sum(b["nights"] for b in invoiced)
        fees = round(sum(b["cancellation_fee"] for b in cancelled), 2)
        return {
            "start": S, "end": E, "invoices": len(invoiced), "room_nights": nights,
            "room_revenue": room, "extras": {k: round(v, 2) for k, v in sorted(extras.items())},
            "extras_revenue": round(sum(extras.values()), 2), "cancellation_fees": fees,
            "net_revenue": round(room + sum(extras.values()) + fees, 2),
            "gst_collected": round(sum(b["invoice"]["gst"] for b in invoiced), 2),
            "billed_total": round(sum(b["invoice"]["grand_total"] for b in invoiced), 2),
            "adr": round(room / nights, 2) if nights else 0.0,
            "by_category": dict(sorted(by_cat.items())),
            "payments_by_mode": {k: round(v, 2) for k, v in sorted(by_mode.items())},
            "cash_in": round(sum(p["amount"] for p in payments if p["amount"] > 0), 2),
            "refunds": round(-sum(p["amount"] for p in payments if p["amount"] < 0), 2),
            "daily": dict(sorted((k, round(v, 2)) for k, v in daily.items())),
        }

    # ============================================================ occupancy
    def occupancy(self, start, end) -> dict:
        """Nightly occupancy. 'Occupied' counts rooms sold for the night (stays and
        confirmed bookings). ADR and RevPAR use nights actually stayed."""
        s, e = _range(start, end)
        rooms = self.db.all("rooms")
        if not rooms:
            raise HotelError("No rooms configured.")
        per_cat = Counter(r["category"] for r in rooms)
        bookings = [b for b in self.db.all("bookings") if b["status"] in ON_BOOKS]
        days, d = [], s
        stayed_revenue, stayed_nights = 0.0, 0
        cat_sold = Counter()
        while d <= e:
            ds = d.isoformat()
            sold = [b for b in bookings if b["check_in"] <= ds < b["check_out"]]
            for b in sold:
                cat_sold[b["category"]] += 1
                if b["status"] in STAYED:
                    n = next((n for n in b["nights_detail"] if n["date"] == ds), None)
                    if n:
                        stayed_revenue += n["tariff"]
                        stayed_nights += 1
            days.append({"date": ds, "sold": len(sold), "available": len(rooms),
                         "occupancy": round(len(sold) / len(rooms) * 100, 1)})
            d += timedelta(days=1)
        room_nights = len(rooms) * len(days)
        sold_total = sum(x["sold"] for x in days)
        return {
            "start": s.isoformat(), "end": e.isoformat(), "rooms": len(rooms), "days": days,
            "average_occupancy": round(sold_total / room_nights * 100, 1),
            "room_nights_sold": sold_total, "room_nights_available": room_nights,
            "peak": max(days, key=lambda x: x["sold"]),
            "by_category": {c: {"rooms": per_cat[c], "sold": cat_sold[c],
                                "occupancy": round(cat_sold[c] / (per_cat[c] * len(days)) * 100, 1)}
                            for c in ROOM_CATEGORIES if per_cat[c]},
            "adr": round(stayed_revenue / stayed_nights, 2) if stayed_nights else 0.0,
            "revpar": round(stayed_revenue / room_nights, 2),
        }

    # ================================================================== CSV
    @staticmethod
    def _csv(path: Path, header: list, rows: list) -> Path:
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return path

    def bookings_csv(self, start=None, end=None) -> Path:
        bs = self.db.all("bookings")
        if start:
            bs = [b for b in bs if b["check_out"] > parse_date(start).isoformat()]
        if end:
            bs = [b for b in bs if b["check_in"] <= parse_date(end).isoformat()]
        paid = defaultdict(float)
        for p in self.db.all("payments"):
            paid[p["booking_id"]] += p["amount"]
        return self._csv(self._path("bookings", "csv"),
                         ["Booking", "Guest", "Customer ID", "Room", "Category", "Check-in", "Check-out", "Nights",
                          "Adults", "Children", "Source", "Status", "Invoice", "Bill Total", "Paid (net)",
                          "Cancellation Fee", "Created By"],
                         [[b["booking_id"], b["guest_name"], b["customer_id"], b["room_no"], b["category"],
                           b["check_in"], b["check_out"], b["nights"], b["adults"], b["children"], b["source"],
                           b["status"], b.get("invoice_no") or "",
                           f"{(b.get('invoice') or {}).get('grand_total', 0):.2f}", f"{paid[b['booking_id']]:.2f}",
                           f"{b['cancellation_fee']:.2f}", b["created_by"]]
                          for b in sorted(bs, key=lambda b: b["check_in"])])

    def customers_csv(self) -> Path:
        bookings = self.db.all("bookings")
        rows = []
        for c in sorted(self.db.all("customers"), key=lambda c: c["customer_id"]):
            mine = [b for b in bookings if b["customer_id"] == c["customer_id"]]
            stays = [b for b in mine if b["status"] == "CHECKED_OUT"]
            masked = (c["id_number"][:2] + "*" * (len(c["id_number"]) - 6) + c["id_number"][-4:]) if c["id_number"] else ""
            rows.append([c["customer_id"], c["name"], c["phone"], c["email"], c["nationality"], c["id_type"], masked,
                         len(mine), len(stays), sum(b["nights"] for b in stays),
                         f"{sum(b['invoice']['grand_total'] for b in stays):.2f}", c["created_at"][:10]])
        return self._csv(self._path("customers", "csv"),
                         ["Customer ID", "Name", "Phone", "Email", "Nationality", "ID Type", "ID Number (masked)",
                          "Bookings", "Stays", "Nights", "Total Spent", "Registered"], rows)

    def revenue_csv(self, start, end) -> Path:
        r = self.revenue(start, end)
        return self._csv(self._path(f"revenue_{r['start']}_{r['end']}", "csv"), ["Date", "Taxable Revenue"],
                         [[d, f"{v:.2f}"] for d, v in r["daily"].items()] + [["TOTAL", f"{r['net_revenue'] - r['cancellation_fees']:.2f}"]])

    def occupancy_csv(self, start, end) -> Path:
        o = self.occupancy(start, end)
        return self._csv(self._path(f"occupancy_{o['start']}_{o['end']}", "csv"),
                         ["Date", "Rooms Sold", "Rooms Available", "Occupancy %"],
                         [[d["date"], d["sold"], d["available"], d["occupancy"]] for d in o["days"]])

    # ================================================================== PDF
    def performance_pdf(self, start, end) -> Path:
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.shapes import Drawing, String
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        rev, occ = self.revenue(start, end), self.occupancy(start, end)
        path = self._path(f"performance_{rev['start']}_{rev['end']}", "pdf")
        styles = getSampleStyleSheet()
        brand = colors.HexColor("#7a3e12")
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                topMargin=1.4 * cm, bottomMargin=1.4 * cm, title="Hotel Performance Report")

        def tbl(rows, widths, right=()):
            t = Table(rows, colWidths=widths, hAlign="LEFT")
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), brand), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                                   ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6c7b8")),
                                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf4ee")])]
                                  + [("ALIGN", (c, 1), (c, -1), "RIGHT") for c in right]))
            return t

        kpi = Table([["Average occupancy", "ADR", "RevPAR", "Net revenue"],
                     [f"{occ['average_occupancy']}%", f"{occ['adr']:,.2f}", f"{occ['revpar']:,.2f}",
                      f"{rev['net_revenue']:,.2f}"]], colWidths=[4.45 * cm] * 4)
        kpi.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, 0), 8), ("TEXTCOLOR", (0, 0), (-1, 0), colors.grey),
                                 ("FONTSIZE", (0, 1), (-1, 1), 15), ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                                 ("TEXTCOLOR", (0, 1), (-1, 1), brand), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                 ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6c7b8")),
                                 ("TOPPADDING", (0, 1), (-1, 1), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 8)]))
        rev_rows = [["Revenue", "Amount"], ["Room revenue", f"{rev['room_revenue']:,.2f}"]] + \
            [[f"  {k}", f"{v:,.2f}"] for k, v in rev["extras"].items()] + \
            [["Cancellation / no-show fees", f"{rev['cancellation_fees']:,.2f}"],
             ["Net revenue (excl. GST)", f"{rev['net_revenue']:,.2f}"], ["GST collected", f"{rev['gst_collected']:,.2f}"],
             ["Refunds paid", f"{rev['refunds']:,.2f}"]]
        cat_rows = [["Category", "Rooms", "Nights sold", "Occupancy"]] + \
            [[c, v["rooms"], v["sold"], f"{v['occupancy']}%"] for c, v in occ["by_category"].items()]
        mode_rows = [["Payment mode", "Net received"]] + [[m, f"{v:,.2f}"] for m, v in rev["payments_by_mode"].items()]

        # daily occupancy bar chart
        days = occ["days"][-31:]
        dr = Drawing(17.5 * cm, 6 * cm)
        ch = VerticalBarChart()
        ch.x, ch.y, ch.width, ch.height = 30, 25, 17.5 * cm - 45, 6 * cm - 45
        ch.data = [[x["occupancy"] for x in days]]
        ch.valueAxis.valueMin, ch.valueAxis.valueMax, ch.valueAxis.valueStep = 0, 100, 25
        ch.categoryAxis.categoryNames = [x["date"][8:] for x in days]
        ch.categoryAxis.labels.fontSize = 6
        ch.valueAxis.labels.fontSize = 7
        ch.bars[0].fillColor = colors.HexColor("#c8803e")
        ch.bars[0].strokeColor = None
        dr.add(ch)
        dr.add(String(30, 6 * cm - 12, "Daily occupancy % (day of month)", fontSize=8, fillColor=colors.grey))

        story = [Paragraph(f"{HOTEL_NAME} — Performance Report", styles["Title"]),
                 Paragraph(f"Period {rev['start']} to {rev['end']} · {occ['rooms']} rooms · generated "
                           f"{datetime.now():%d %b %Y %H:%M}", styles["Normal"]), Spacer(1, 10), kpi, Spacer(1, 12),
                 dr, Spacer(1, 10),
                 Table([[tbl(rev_rows, [5.6 * cm, 3 * cm], (1,)), tbl(cat_rows, [3 * cm, 1.5 * cm, 2.1 * cm, 2 * cm], (1, 2, 3))]],
                       colWidths=[8.9 * cm, 8.9 * cm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]),
                 Spacer(1, 10), tbl(mode_rows, [5.6 * cm, 3 * cm], (1,)), Spacer(1, 10),
                 Paragraph(f"Invoices issued: {rev['invoices']} · Room nights billed: {rev['room_nights']} · "
                           f"Peak night: {occ['peak']['date']} ({occ['peak']['occupancy']}%). ADR = room revenue ÷ "
                           "room nights stayed; RevPAR = room revenue ÷ room nights available.", styles["Normal"])]
        doc.build(story)
        return path
