"""Reports: stock, low / out-of-stock, sales, profit, purchases, GST summary,
receivables / payables; CSV exports and PDF reports."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .customers import CustomerManager
from .database import JSONDatabase
from .products import ProductManager
from .purchases import PurchaseManager
from .sales import SalesManager
from .suppliers import SupplierManager
from .utils import BUSINESS_NAME, InventoryError, ValidationError, parse_date


def _period(start, end) -> tuple[str, str]:
    s, e = parse_date(start, "Start date"), parse_date(end, "End date")
    if e < s:
        raise ValidationError("End date is before start date.")
    return s.isoformat(), e.isoformat()


class ReportGenerator:
    def __init__(self, db: JSONDatabase, report_dir: Path | str):
        self.db = db
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.products = ProductManager(db)
        self.sales = SalesManager(db)
        self.purchases = PurchaseManager(db)
        self.customers = CustomerManager(db)
        self.suppliers = SupplierManager(db)

    # ============================================================== stock
    def stock_status(self, p: dict) -> str:
        if p["stock"] <= 0:
            return "OUT OF STOCK"
        return "LOW" if p["stock"] <= p["reorder_level"] else "OK"

    def stock_report(self, category: str | None = None) -> dict:
        rows = [{"product": p, "status": self.stock_status(p), "cost_value": round(p["stock"] * p["avg_cost"], 2),
                 "selling_value": round(p["stock"] * p["selling_price"], 2)}
                for p in self.products.list(category, sort_by="category")]
        by_cat = defaultdict(lambda: {"products": 0, "cost_value": 0.0, "selling_value": 0.0})
        for r in rows:
            c = by_cat[r["product"]["category"]]
            c["products"] += 1
            c["cost_value"] = round(c["cost_value"] + r["cost_value"], 2)
            c["selling_value"] = round(c["selling_value"] + r["selling_value"], 2)
        return {"rows": rows, "by_category": dict(sorted(by_cat.items())), **self.products.valuation()}

    # ============================================================== sales
    def sales_report(self, start, end) -> dict:
        S, E = _period(start, end)
        sales = self.sales.list(S, E)
        cancelled = [s for s in self.sales.list(S, E, include_cancelled=True) if s["status"] == "CANCELLED"]
        keys = ("gross", "discount", "taxable", "cgst", "sgst", "igst", "tax", "grand_total", "amount_paid")
        tot = {k: round(sum(s[k] for s in sales), 2) for k in keys}
        by_mode, by_day = defaultdict(float), defaultdict(lambda: {"invoices": 0, "total": 0.0})
        for s in sales:
            for p in s["payments"]:
                by_mode[p["mode"]] += p["amount"]
            by_day[s["date"]]["invoices"] += 1
            by_day[s["date"]]["total"] = round(by_day[s["date"]]["total"] + s["grand_total"], 2)
        credit = round(tot["grand_total"] - tot["amount_paid"], 2)
        if credit > 0.005:
            by_mode["Credit (outstanding)"] = credit
        return {"start": S, "end": E, "invoices": len(sales), "cancelled": len(cancelled), **tot,
                "outstanding": credit, "avg_bill": round(tot["grand_total"] / len(sales), 2) if sales else 0.0,
                "by_mode": {k: round(v, 2) for k, v in sorted(by_mode.items())}, "by_day": dict(sorted(by_day.items())),
                "sales": sales}

    def profit_report(self, start, end) -> dict:
        """Gross profit = taxable sales value - cost of goods sold (weighted-average cost at time of sale)."""
        S, E = _period(start, end)
        by_prod = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0, "cost": 0.0})
        by_cat = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0})
        cats = {p["product_id"]: p["category"] for p in self.products.list(include_inactive=True)}
        for s in self.sales.list(S, E):
            for l in s["lines"]:
                cost = round(l["qty"] * l["unit_cost"], 2)
                bp = by_prod[(l["product_id"], l["name"], l["unit"])]
                bp["qty"] = round(bp["qty"] + l["qty"], 3)
                bp["revenue"] = round(bp["revenue"] + l["taxable"], 2)
                bp["cost"] = round(bp["cost"] + cost, 2)
                bc = by_cat[cats.get(l["product_id"], "Unknown")]
                bc["revenue"] = round(bc["revenue"] + l["taxable"], 2)
                bc["cost"] = round(bc["cost"] + cost, 2)

        def finish(d):
            d["profit"] = round(d["revenue"] - d["cost"], 2)
            d["margin"] = round(d["profit"] / d["revenue"] * 100, 1) if d["revenue"] else 0.0
            return d
        products = [{"product_id": k[0], "name": k[1], "unit": k[2], **finish(v)} for k, v in by_prod.items()]
        revenue = round(sum(p["revenue"] for p in products), 2)
        cost = round(sum(p["cost"] for p in products), 2)
        return {"start": S, "end": E, "revenue": revenue, "cogs": cost, "gross_profit": round(revenue - cost, 2),
                "margin": round((revenue - cost) / revenue * 100, 1) if revenue else 0.0,
                "by_category": {k: finish(v) for k, v in sorted(by_cat.items())},
                "products": sorted(products, key=lambda p: -p["revenue"]),
                "top_by_qty": sorted(products, key=lambda p: -p["qty"])[:10],
                "top_by_profit": sorted(products, key=lambda p: -p["profit"])[:10]}

    # ========================================================== purchases
    def purchase_report(self, start, end) -> dict:
        S, E = _period(start, end)
        pos = [p for p in self.purchases.list("RECEIVED") if S <= p["received_on"] <= E]
        by_sup = defaultdict(lambda: {"bills": 0, "total": 0.0, "paid": 0.0})
        for p in pos:
            b = by_sup[p["supplier_name"]]
            b["bills"] += 1
            b["total"] = round(b["total"] + p["grand_total"], 2)
            b["paid"] = round(b["paid"] + p["amount_paid"], 2)
        return {"start": S, "end": E, "bills": len(pos),
                "taxable": round(sum(p["taxable"] for p in pos), 2), "tax": round(sum(p["tax"] for p in pos), 2),
                "total": round(sum(p["grand_total"] for p in pos), 2),
                "paid": round(sum(p["amount_paid"] for p in pos), 2),
                "by_supplier": dict(sorted(by_sup.items(), key=lambda kv: -kv[1]["total"])),
                "open_orders": self.purchases.list("ORDERED"), "purchases": pos}

    # ================================================================ GST
    def gst_report(self, start, end) -> dict:
        """Output GST on sales vs input GST on purchases received, by rate."""
        S, E = _period(start, end)

        def collect(docs):
            by_rate = defaultdict(lambda: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0})
            for d in docs:
                for rate, v in d["gst_summary"].items():
                    for k in ("taxable", "cgst", "sgst", "igst"):
                        by_rate[rate][k] = round(by_rate[rate][k] + v[k], 2)
            totals = {k: round(sum(v[k] for v in by_rate.values()), 2) for k in ("taxable", "cgst", "sgst", "igst")}
            totals["tax"] = round(totals["cgst"] + totals["sgst"] + totals["igst"], 2)
            return dict(sorted(by_rate.items(), key=lambda kv: float(kv[0]))), totals
        out_rates, out_tot = collect(self.sales.list(S, E))
        in_rates, in_tot = collect([p for p in self.purchases.list("RECEIVED") if S <= p["received_on"] <= E])
        return {"start": S, "end": E, "output": out_rates, "output_total": out_tot, "input": in_rates,
                "input_total": in_tot, "net_payable": round(out_tot["tax"] - in_tot["tax"], 2)}

    # ================================================================ CSV
    def _path(self, stem: str, ext: str) -> Path:
        return self.report_dir / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"

    @staticmethod
    def _csv(path: Path, header: list, rows: list) -> Path:
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return path

    def stock_csv(self) -> Path:
        r = self.stock_report()
        return self._csv(self._path("stock", "csv"),
                         ["Product ID", "Name", "Brand", "Category", "Unit", "Stock", "Reorder Level", "Status",
                          "Avg Cost", "Selling Price", "GST %", "Cost Value", "Selling Value", "Location"],
                         [[x["product"]["product_id"], x["product"]["name"], x["product"]["brand"],
                           x["product"]["category"], x["product"]["unit"], x["product"]["stock"],
                           x["product"]["reorder_level"], x["status"], f"{x['product']['avg_cost']:.2f}",
                           f"{x['product']['selling_price']:.2f}", x["product"]["gst_rate"], f"{x['cost_value']:.2f}",
                           f"{x['selling_value']:.2f}", x["product"]["location"]] for x in r["rows"]])

    def reorder_csv(self) -> Path:
        sup = {s["supplier_id"]: s["name"] for s in self.suppliers.list(include_inactive=True)}
        return self._csv(self._path("reorder_list", "csv"),
                         ["Product ID", "Name", "Unit", "Stock", "Reorder Level", "Suggested Qty", "Estimated Cost",
                          "Last Supplier"],
                         [[r["product"]["product_id"], r["product"]["name"], r["product"]["unit"], r["product"]["stock"],
                           r["product"]["reorder_level"], r["suggested_qty"], f"{r['estimated_cost']:.2f}",
                           sup.get(r["last_supplier"], "")] for r in self.products.reorder_suggestions()])

    def sales_csv(self, start, end) -> Path:
        r = self.sales_report(start, end)
        return self._csv(self._path(f"sales_{r['start']}_{r['end']}", "csv"),
                         ["Invoice", "Date", "Customer", "GSTIN", "Place of Supply", "Taxable", "CGST", "SGST", "IGST",
                          "Discount", "Grand Total", "Paid", "Balance", "Payment Status", "Profit"],
                         [[s["invoice_no"], s["date"], s["customer_name"], s["customer_gstin"], s["place_of_supply"],
                           s["taxable"], s["cgst"], s["sgst"], s["igst"], s["discount"], s["grand_total"],
                           s["amount_paid"], round(s["grand_total"] - s["amount_paid"], 2), s["payment_status"],
                           s["profit"]] for s in sorted(r["sales"], key=lambda s: s["invoice_no"])])

    def purchases_csv(self, start, end) -> Path:
        r = self.purchase_report(start, end)
        return self._csv(self._path(f"purchases_{r['start']}_{r['end']}", "csv"),
                         ["Purchase", "Date", "Received", "Supplier", "Supplier Invoice", "Taxable", "GST", "Total",
                          "Paid", "Payment Status"],
                         [[p["purchase_id"], p["date"], p["received_on"], p["supplier_name"], p["supplier_invoice"],
                           p["taxable"], p["tax"], p["grand_total"], p["amount_paid"], p["payment_status"]]
                          for p in sorted(r["purchases"], key=lambda p: p["purchase_id"])])

    def profit_csv(self, start, end) -> Path:
        r = self.profit_report(start, end)
        return self._csv(self._path(f"profit_{r['start']}_{r['end']}", "csv"),
                         ["Product ID", "Name", "Qty Sold", "Unit", "Revenue (taxable)", "Cost", "Profit", "Margin %"],
                         [[p["product_id"], p["name"], p["qty"], p["unit"], p["revenue"], p["cost"], p["profit"],
                           p["margin"]] for p in r["products"]] +
                         [["", "TOTAL", "", "", r["revenue"], r["cogs"], r["gross_profit"], r["margin"]]])

    def gst_csv(self, start, end) -> Path:
        r = self.gst_report(start, end)
        rows = [["Output (sales)", rate, v["taxable"], v["cgst"], v["sgst"], v["igst"]] for rate, v in r["output"].items()]
        rows += [["Input (purchases)", rate, v["taxable"], v["cgst"], v["sgst"], v["igst"]] for rate, v in r["input"].items()]
        rows += [["Net GST payable", "", "", "", "", r["net_payable"]]]
        return self._csv(self._path(f"gst_{r['start']}_{r['end']}", "csv"),
                         ["Type", "GST %", "Taxable", "CGST", "SGST", "IGST"], rows)

    def parties_csv(self, kind: str) -> Path:
        mgr = self.customers if kind == "customers" else self.suppliers
        idf = mgr.id_field
        bal = {x["customer"]["customer_id"]: x["receivable"] for x in self.customers.receivables()} if kind == "customers" \
            else {x["supplier"]["supplier_id"]: x["payable"] for x in self.suppliers.payables()}
        return self._csv(self._path(kind, "csv"),
                         ["ID", "Name", "Contact", "Phone", "Email", "GSTIN", "State", "Address", "Active",
                          "Receivable" if kind == "customers" else "Payable"],
                         [[r[idf], r["name"], r.get("contact_person", ""), r["phone"], r["email"], r["gstin"], r["state"],
                           r["address"], "Yes" if r["active"] else "No", f"{bal.get(r[idf], 0):.2f}"]
                          for r in mgr.list(include_inactive=True)])

    def ledger_csv(self, product_id: str) -> Path:
        p = self.products.get(product_id)
        return self._csv(self._path(f"ledger_{p['product_id']}", "csv"),
                         ["Date/Time", "Type", "Qty", "Balance", "Reference", "Unit Cost", "Note", "By"],
                         [[m["at"].replace("T", " "), m["type"], m["qty"], m["balance"], m["ref"], m["unit_cost"],
                           m["note"], m["by"]] for m in self.products.ledger(p["product_id"])])

    # ================================================================ PDF
    def _pdf(self, title: str, subtitle: str, story_fn, landscape_mode: bool = False) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        styles = getSampleStyleSheet()
        brand = colors.HexColor("#1b5e4b")
        cell = ParagraphStyle("c", parent=styles["Normal"], fontSize=8, leading=10)

        def table(rows, widths, right=(), highlight=None):
            t = Table(rows, colWidths=[w * cm for w in widths], repeatRows=1, hAlign="LEFT")
            st = [("BACKGROUND", (0, 0), (-1, 0), brand), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                  ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bcd3cb")),
                  ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f7f4")])]
            st += [("ALIGN", (c, 1), (c, -1), "RIGHT") for c in right]
            for row, color in (highlight or {}).items():
                st.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor(color)))
            t.setStyle(TableStyle(st))
            return t
        kit = {"table": table, "P": lambda t: Paragraph(escape(str(t)), cell), "H": lambda t: Paragraph(t, styles["Heading3"]),
               "S": Spacer, "cm": cm}
        stem = title.lower().replace(" ", "_").replace("&", "and")
        path = self._path(stem, "pdf")
        size = landscape(A4) if landscape_mode else A4
        doc = SimpleDocTemplate(str(path), pagesize=size, leftMargin=1.3 * cm, rightMargin=1.3 * cm,
                                topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=title)
        story = [Paragraph(f"{BUSINESS_NAME} — {title}", styles["Title"]),
                 Paragraph(f"{subtitle} · generated {datetime.now():%d %b %Y %H:%M}", styles["Normal"]), Spacer(1, 10)]
        story += story_fn(kit)
        doc.build(story)
        return path

    def stock_pdf(self) -> Path:
        r = self.stock_report()
        if not r["rows"]:
            raise InventoryError("No products to report.")

        def story(k):
            summary = [["Products", "Units", "Stock value (cost)", "Stock value (selling)", "Low stock", "Out of stock"],
                       [r["products"], f"{r['units']:g}", f"{r['cost_value']:,.2f}", f"{r['selling_value']:,.2f}",
                        r["low_stock"], r["out_of_stock"]]]
            rows = [["ID", "Product", "Category", "Stock", "Reorder", "Status", "Avg cost", "Value (cost)"]]
            hl = {}
            for i, x in enumerate(r["rows"], 1):
                p = x["product"]
                rows.append([p["product_id"], k["P"](f"{p['name']} {p['brand']}".strip()), p["category"],
                             f"{p['stock']:g} {p['unit']}", f"{p['reorder_level']:g}", x["status"],
                             f"{p['avg_cost']:,.2f}", f"{x['cost_value']:,.2f}"])
                if x["status"] != "OK":
                    hl[i] = "#fde2e1" if x["status"] == "OUT OF STOCK" else "#fff3cd"
            cats = [["Category", "Products", "Value (cost)", "Value (selling)"]] + \
                [[c, v["products"], f"{v['cost_value']:,.2f}", f"{v['selling_value']:,.2f}"] for c, v in r["by_category"].items()]
            return [k["table"](summary, [2.6, 2.4, 3.3, 3.4, 2.4, 2.6], right=(0, 1, 2, 3, 4, 5)), k["S"](1, 10),
                    k["H"]("Stock by category"), k["table"](cats, [5, 2.4, 3.6, 3.6], right=(1, 2, 3)), k["S"](1, 10),
                    k["H"]("Product stock (yellow = low, red = out of stock)"),
                    k["table"](rows, [1.4, 5.6, 2.6, 2.1, 1.5, 2.3, 1.8, 2.2], right=(3, 4, 6, 7), highlight=hl)]
        return self._pdf("Stock Report", f"As of {date.today().isoformat()}", story)

    def sales_profit_pdf(self, start, end) -> Path:
        s, pr, g = self.sales_report(start, end), self.profit_report(start, end), self.gst_report(start, end)

        def story(k):
            kpi = [["Invoices", "Sales (incl. GST)", "Taxable sales", "Gross profit", "Margin", "Net GST payable"],
                   [s["invoices"], f"{s['grand_total']:,.2f}", f"{s['taxable']:,.2f}", f"{pr['gross_profit']:,.2f}",
                    f"{pr['margin']}%", f"{g['net_payable']:,.2f}"]]
            cat = [["Category", "Revenue", "Cost", "Profit", "Margin %"]] + \
                [[c, f"{v['revenue']:,.2f}", f"{v['cost']:,.2f}", f"{v['profit']:,.2f}", v["margin"]]
                 for c, v in pr["by_category"].items()]
            top = [["Product", "Qty", "Revenue", "Profit", "Margin %"]] + \
                [[k["P"](p["name"]), f"{p['qty']:g} {p['unit']}", f"{p['revenue']:,.2f}", f"{p['profit']:,.2f}", p["margin"]]
                 for p in pr["products"][:15]]
            modes = [["Payment mode", "Amount"]] + [[m, f"{v:,.2f}"] for m, v in s["by_mode"].items()]
            gst = [["", "Taxable", "CGST", "SGST", "IGST", "Total GST"],
                   ["Output (sales)", f"{g['output_total']['taxable']:,.2f}", f"{g['output_total']['cgst']:,.2f}",
                    f"{g['output_total']['sgst']:,.2f}", f"{g['output_total']['igst']:,.2f}", f"{g['output_total']['tax']:,.2f}"],
                   ["Input (purchases)", f"{g['input_total']['taxable']:,.2f}", f"{g['input_total']['cgst']:,.2f}",
                    f"{g['input_total']['sgst']:,.2f}", f"{g['input_total']['igst']:,.2f}", f"{g['input_total']['tax']:,.2f}"],
                   ["Net payable", "", "", "", "", f"{g['net_payable']:,.2f}"]]
            return [k["table"](kpi, [2.2, 3.2, 3, 2.9, 2.2, 3.1], right=(0, 1, 2, 3, 4, 5)), k["S"](1, 10),
                    k["H"]("Profit by category"), k["table"](cat, [5, 3, 3, 3, 2], right=(1, 2, 3, 4)), k["S"](1, 8),
                    k["H"]("Top products by revenue"), k["table"](top, [6.6, 2.4, 3, 3, 2], right=(1, 2, 3, 4)),
                    k["S"](1, 8), k["H"]("Collections"), k["table"](modes, [5, 3], right=(1,)), k["S"](1, 8),
                    k["H"]("GST summary"), k["table"](gst, [3.4, 3, 2.6, 2.6, 2.6, 2.8], right=(1, 2, 3, 4, 5))]
        return self._pdf("Sales & Profit Report", f"Period {s['start']} to {s['end']}", story)
