"""report.py — PDF account statement (ReportLab), customer & transaction CSV
exports and a system summary."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from database import JSONDatabase
from transaction import CREDIT_TYPES
from utils import BANK_NAME, AccountNotFoundError, mask_account


class ReportGenerator:
    def __init__(self, db: JSONDatabase, report_dir: Path | str):
        self.db = db
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _stamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------------ csv
    def export_customers_csv(self) -> Path:
        path = self.report_dir / f"customers_{self._stamp()}.csv"
        loans = self.db.all("loans")
        fds = self.db.all("fixed_deposits")
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Account No", "Name", "Phone", "Email", "Type", "Balance", "Status",
                        "Active FDs", "Active Loans", "Loan Outstanding", "Created At", "Last Login"])
            for c in sorted(self.db.all("customers"), key=lambda c: c["created_at"]):
                my_loans = [l for l in loans if l["account_no"] == c["account_no"] and l["status"] == "ACTIVE"]
                w.writerow([c["account_no"], c["name"], c["phone"], c["email"], c["account_type"],
                            f"{c['balance']:.2f}", c["status"],
                            sum(1 for f in fds if f["account_no"] == c["account_no"] and f["status"] == "ACTIVE"),
                            len(my_loans), f"{sum(l['outstanding'] for l in my_loans):.2f}",
                            c["created_at"], c.get("last_login") or ""])
        return path

    def export_transactions_csv(self, account_no: str | None = None,
                                start: str | None = None, end: str | None = None) -> Path:
        txns = self.db.find("transactions", **({"account_no": account_no} if account_no else {}))
        if start:
            txns = [t for t in txns if t["timestamp"][:10] >= start]
        if end:
            txns = [t for t in txns if t["timestamp"][:10] <= end]
        txns.sort(key=lambda t: t["timestamp"])  # stable: keeps file order
        suffix = f"_{account_no}" if account_no else "_all"
        path = self.report_dir / f"transactions{suffix}_{self._stamp()}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Txn ID", "Timestamp", "Account No", "Type", "Credit", "Debit",
                        "Balance After", "Counterparty", "Description"])
            for t in txns:
                credit = t["type"] in CREDIT_TYPES
                w.writerow([t["txn_id"], t["timestamp"], t["account_no"], t["type"],
                            f"{t['amount']:.2f}" if credit else "", "" if credit else f"{t['amount']:.2f}",
                            f"{t['balance_after']:.2f}", t.get("counterparty") or "", t["description"]])
        return path

    # ------------------------------------------------------------------ pdf
    def account_statement_pdf(self, account_no: str, start: str | None = None,
                              end: str | None = None) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        cust = self.db.find_one("customers", account_no=account_no)
        if not cust:
            raise AccountNotFoundError(f"Account {account_no} not found.")
        txns = self.db.find("transactions", account_no=account_no)
        if start:
            txns = [t for t in txns if t["timestamp"][:10] >= start]
        if end:
            txns = [t for t in txns if t["timestamp"][:10] <= end]
        txns.sort(key=lambda t: t["timestamp"])  # stable: keeps file order

        path = self.report_dir / f"statement_{account_no}_{self._stamp()}.pdf"
        styles = getSampleStyleSheet()
        from reportlab.lib.styles import ParagraphStyle
        cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=10)
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                                title=f"Account Statement {mask_account(account_no)}")

        def styled(data, widths, right_cols=()):
            t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b57")),
                     ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                     ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                     ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                     ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b0b7bf")),
                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
                     ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
            style += [("ALIGN", (c, 1), (c, -1), "RIGHT") for c in right_cols]
            t.setStyle(TableStyle(style))
            return t

        period_start = start or (txns[0]["timestamp"][:10] if txns else cust["created_at"][:10])
        period_end = end or datetime.now().strftime("%Y-%m-%d")
        credits = sum(t["amount"] for t in txns if t["type"] in CREDIT_TYPES)
        debits = sum(t["amount"] for t in txns if t["type"] not in CREDIT_TYPES)
        info = [["Account Holder", cust["name"], "Account No", cust["account_no"]],
                ["Account Type", cust["account_type"], "Status", cust["status"]],
                ["Phone", cust["phone"], "Email", cust["email"]],
                ["Period", f"{period_start} to {period_end}",
                 "Generated", f"{datetime.now():%Y-%m-%d %H:%M}"]]
        info_tbl = Table(info, colWidths=[3.2 * cm, 5.6 * cm, 2.8 * cm, 6.2 * cm], hAlign="LEFT")
        info_tbl.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9),
                                      ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                                      ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story = [Paragraph(BANK_NAME, styles["Title"]),
                 Paragraph("Account Statement", styles["Heading2"]), info_tbl, Spacer(1, 10),
                 styled([["Total Credits", "Total Debits", "Transactions", "Closing Balance"],
                         [f"{credits:,.2f}", f"{debits:,.2f}", str(len(txns)), f"{cust['balance']:,.2f}"]],
                        [4.4 * cm] * 4, right_cols=(0, 1, 3)),
                 Spacer(1, 12), Paragraph("Transactions", styles["Heading3"])]
        rows = [["Date / Time", "Txn ID", "Description", "Debit", "Credit", "Balance"]]
        for t in txns:
            cr = t["type"] in CREDIT_TYPES
            rows.append([t["timestamp"][:16], t["txn_id"][-8:], Paragraph(t["description"], cell),
                         "" if cr else f"{t['amount']:,.2f}", f"{t['amount']:,.2f}" if cr else "",
                         f"{t['balance_after']:,.2f}"])
        if len(rows) == 1:
            rows.append(["-", "-", "No transactions in this period", "", "", ""])
        story.append(styled(rows, [3 * cm, 2 * cm, 6 * cm, 2.2 * cm, 2.2 * cm, 2.4 * cm], right_cols=(3, 4, 5)))

        fds = [f for f in self.db.find("fixed_deposits", account_no=account_no) if f["status"] == "ACTIVE"]
        if fds:
            story += [Spacer(1, 12), Paragraph("Active Fixed Deposits", styles["Heading3"]),
                      styled([["FD ID", "Principal", "Rate", "Maturity Date", "Maturity Amount"]] +
                             [[f["fd_id"], f"{f['principal']:,.2f}", f"{f['rate']}%", f["maturity_date"],
                               f"{f['maturity_amount']:,.2f}"] for f in fds],
                             [4.6 * cm, 3 * cm, 2 * cm, 3.2 * cm, 3.5 * cm], right_cols=(1, 4))]
        loans = [l for l in self.db.find("loans", account_no=account_no) if l["status"] == "ACTIVE"]
        if loans:
            story += [Spacer(1, 12), Paragraph("Active Loans", styles["Heading3"]),
                      styled([["Loan ID", "Type", "Principal", "EMI", "Outstanding"]] +
                             [[l["loan_id"], l["loan_type"], f"{l['principal']:,.2f}", f"{l['emi']:,.2f}",
                               f"{l['outstanding']:,.2f}"] for l in loans],
                             [4.6 * cm, 2.6 * cm, 3 * cm, 3 * cm, 3.1 * cm], right_cols=(2, 3, 4))]
        story += [Spacer(1, 16), Paragraph("This is a computer-generated statement and does not require a "
                                           "signature.", styles["Italic"])]
        doc.build(story)
        return path

    # -------------------------------------------------------------- summary
    def system_summary(self) -> dict:
        customers = self.db.all("customers")
        txns = self.db.all("transactions")
        loans = self.db.all("loans")
        fds = self.db.all("fixed_deposits")
        by_type: dict[str, dict] = {}
        for t in txns:
            d = by_type.setdefault(t["type"], {"count": 0, "amount": 0.0})
            d["count"] += 1
            d["amount"] = round(d["amount"] + t["amount"], 2)
        active_loans = [l for l in loans if l["status"] == "ACTIVE"]
        active_fds = [f for f in fds if f["status"] == "ACTIVE"]
        return {
            "total_customers": len(customers),
            "active_accounts": sum(1 for c in customers if c["status"] == "ACTIVE"),
            "frozen_accounts": sum(1 for c in customers if c["status"] == "FROZEN"),
            "total_deposits_held": round(sum(c["balance"] for c in customers), 2),
            "total_transactions": len(txns),
            "active_fds": len(active_fds),
            "fd_principal": round(sum(f["principal"] for f in active_fds), 2),
            "active_loans": len(active_loans),
            "loan_outstanding": round(sum(l["outstanding"] for l in active_loans), 2),
            "by_type": dict(sorted(by_type.items())),
        }
