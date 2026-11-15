"""Reports: available / issued / overdue books, popular books, circulation
summary, member activity, fines; CSV exports and PDF reports."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .books import BookManager
from .circulation import CirculationManager
from .database import JSONDatabase
from .fines import FineManager
from .librarian import LibrarianDesk
from .members import MemberManager
from .utils import LIBRARY_NAME, LibraryError, ValidationError, parse_date, today


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
        self.books = BookManager(db)
        self.members = MemberManager(db)
        self.circ = CirculationManager(db)
        self.fines = FineManager(db)

    # ============================================================ data
    def available_books(self, category: str | None = None) -> list[dict]:
        out = []
        for b in self.books.list(category):
            a = self.books.availability(b["book_id"])
            if a["total"]:
                out.append({"book": b, **a})
        return out

    def issued_books(self) -> list[dict]:
        on = today()
        rows = []
        for l in sorted(self.circ.loans(status="ISSUED"), key=lambda l: l["due_on"]):
            days, fine = self.circ.overdue_fine(l, on)
            rows.append({**l, "days_overdue": days, "fine_so_far": fine})
        return rows

    def popular_books(self, start, end, top: int = 10) -> list[dict]:
        S, E = _period(start, end)
        counts = Counter(l["book_id"] for l in self.db.all("loans") if S <= l["issued_on"] <= E)
        out = []
        for book_id, n in counts.most_common(top):
            b = self.books.get(book_id)
            out.append({"book": b, "issues": n, "waiting": len([r for r in self.db.all("reservations")
                                                                if r["book_id"] == book_id and r["status"] == "WAITING"])})
        return out

    def circulation_summary(self, start, end) -> dict:
        S, E = _period(start, end)
        loans = self.db.all("loans")
        issued = [l for l in loans if S <= l["issued_on"] <= E]
        returned = [l for l in loans if l["returned_on"] and S <= l["returned_on"] <= E and l["status"] == "RETURNED"]
        late = [l for l in returned if l["returned_on"] > l["due_on"]]
        cats = {b["book_id"]: b["category"] for b in self.books.list()}
        mtypes = {m["member_id"]: m["type"] for m in self.db.all("members")}
        by_day = defaultdict(lambda: {"issued": 0, "returned": 0})
        for l in issued:
            by_day[l["issued_on"]]["issued"] += 1
        for l in returned:
            by_day[l["returned_on"]]["returned"] += 1
        return {"start": S, "end": E, "issued": len(issued), "returned": len(returned),
                "renewals": sum(l["renewals"] for l in issued), "returned_late": len(late),
                "on_time_rate": round((len(returned) - len(late)) / len(returned) * 100, 1) if returned else 100.0,
                "lost": sum(1 for l in loans if l["status"] == "LOST" and S <= (l["returned_on"] or "") <= E),
                "by_category": dict(Counter(cats.get(l["book_id"], "?") for l in issued).most_common()),
                "by_member_type": dict(Counter(mtypes.get(l["member_id"], "?") for l in issued).most_common()),
                "by_day": dict(sorted(by_day.items())),
                "fines": self.fines.collections(S, E)}

    def member_activity(self) -> list[dict]:
        loans = self.db.all("loans")
        out = []
        for m in self.members.list():
            mine = [l for l in loans if l["member_id"] == m["member_id"]]
            out.append({"member": m, "status": self.members.effective_status(m), "total_loans": len(mine),
                        "on_loan": sum(1 for l in mine if l["status"] == "ISSUED"),
                        "overdue": sum(1 for l in mine if l["status"] == "ISSUED" and l["due_on"] < today().isoformat()),
                        "fines_due": self.fines.outstanding(m["member_id"])})
        return out

    # ============================================================ CSV
    def _path(self, stem: str, ext: str) -> Path:
        return self.report_dir / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"

    @staticmethod
    def _csv(path: Path, header: list, rows: list) -> Path:
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return path

    def catalogue_csv(self) -> Path:
        return self._csv(self._path("catalogue", "csv"),
                         ["Book ID", "ISBN", "Title", "Authors", "Publisher", "Year", "Category", "Language", "Shelf",
                          "Price", "Copies", "Available", "Issued", "On Hold", "Damaged", "Lost", "Reference Only"],
                         [[x["book"]["book_id"], x["book"]["isbn"], x["book"]["title"], x["book"]["authors"],
                           x["book"]["publisher"], x["book"]["year"] or "", x["book"]["category"], x["book"]["language"],
                           x["book"]["shelf"], x["book"]["price"], x["total"], x["available"], x["issued"], x["on_hold"],
                           x["damaged"], x["lost"], "Yes" if x["book"]["reference_only"] else "No"]
                          for x in self.available_books()])

    def issued_csv(self) -> Path:
        return self._csv(self._path("issued_books", "csv"),
                         ["Loan", "Accession", "Title", "Member ID", "Member", "Issued On", "Due On", "Renewals",
                          "Days Overdue", "Fine So Far"],
                         [[l["loan_id"], l["accession"], l["title"], l["member_id"], l["member_name"], l["issued_on"],
                           l["due_on"], l["renewals"], l["days_overdue"], l["fine_so_far"]] for l in self.issued_books()])

    def overdue_csv(self) -> Path:
        mems = {m["member_id"]: m for m in self.db.all("members")}
        return self._csv(self._path("overdue", "csv"),
                         ["Loan", "Accession", "Title", "Member ID", "Member", "Phone", "Email", "Due On", "Days Overdue",
                          "Fine So Far"],
                         [[l["loan_id"], l["accession"], l["title"], l["member_id"], l["member_name"],
                           mems[l["member_id"]]["phone"], mems[l["member_id"]]["email"], l["due_on"], l["days_overdue"],
                           l["fine_so_far"]] for l in self.circ.overdue()])

    def members_csv(self) -> Path:
        return self._csv(self._path("members", "csv"),
                         ["Member ID", "Name", "Type", "ID Number", "Department", "Phone", "Email", "Joined", "Expires",
                          "Status", "Total Loans", "On Loan", "Overdue", "Fines Due"],
                         [[x["member"]["member_id"], x["member"]["name"], x["member"]["type"], x["member"]["id_number"],
                           x["member"]["department"], x["member"]["phone"], x["member"]["email"], x["member"]["joined_on"],
                           x["member"]["expires_on"], x["status"], x["total_loans"], x["on_loan"], x["overdue"],
                           x["fines_due"]] for x in self.member_activity()])

    def fines_csv(self) -> Path:
        return self._csv(self._path("fines", "csv"),
                         ["Fine ID", "Member ID", "Type", "Loan", "Accession", "Raised On", "Amount", "Paid", "Waived",
                          "Balance", "Status", "Note"],
                         [[f["fine_id"], f["member_id"], f["type"], f["loan_id"] or "", f["accession"] or "", f["created_on"],
                           f["amount"], f["paid"], f["waived"], FineManager.balance(f), f["status"], f["note"]]
                          for f in self.fines.list()])

    def circulation_csv(self, start, end) -> Path:
        s = self.circulation_summary(start, end)
        return self._csv(self._path(f"circulation_{s['start']}_{s['end']}", "csv"), ["Date", "Issued", "Returned"],
                         [[d, v["issued"], v["returned"]] for d, v in s["by_day"].items()] +
                         [["TOTAL", s["issued"], s["returned"]]])

    def reminders_csv(self) -> Path:
        return self._csv(self._path("reminders", "csv"), ["Type", "Member ID", "Name", "Phone", "Email", "Message"],
                         [[r["kind"], r["member"]["member_id"], r["member"]["name"], r["member"]["phone"],
                           r["member"]["email"], r["message"]] for r in LibrarianDesk(self.db).reminders()])

    # ============================================================ PDF
    def _pdf(self, title: str, subtitle: str, build) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        styles = getSampleStyleSheet()
        brand = colors.HexColor("#3b2f6b")
        cell = ParagraphStyle("c", parent=styles["Normal"], fontSize=8, leading=10)

        def table(rows, widths, right=(), highlight=None):
            t = Table(rows, colWidths=[w * cm for w in widths], repeatRows=1, hAlign="LEFT")
            st = [("BACKGROUND", (0, 0), (-1, 0), brand), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                  ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbc4e0")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f1fb")])]
            st += [("ALIGN", (c, 1), (c, -1), "RIGHT") for c in right]
            for r, col in (highlight or {}).items():
                st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor(col)))
            t.setStyle(TableStyle(st))
            return t
        k = {"table": table, "P": lambda t: Paragraph(escape(str(t)), cell), "S": Spacer,
             "H": lambda t: Paragraph(t, styles["Heading3"])}
        path = self._path(title.lower().replace(" ", "_").replace("&", "and"), "pdf")
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.4 * cm, rightMargin=1.4 * cm,
                                topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=title)
        story = [Paragraph(f"{LIBRARY_NAME} — {title}", styles["Title"]),
                 Paragraph(f"{subtitle} · generated {datetime.now():%d %b %Y %H:%M}", styles["Normal"]), Spacer(1, 10)]
        doc.build(story + build(k))
        return path

    def availability_pdf(self) -> Path:
        rows_data = self.available_books()
        if not rows_data:
            raise LibraryError("The catalogue is empty.")
        st = self.books.stats()

        def build(k):
            summary = [["Titles", "Copies", "Available", "Issued", "On hold", "Damaged", "Lost"],
                       [st["titles"], st["copies"], st["by_status"].get("AVAILABLE", 0), st["by_status"].get("ISSUED", 0),
                        st["by_status"].get("ON_HOLD", 0), st["by_status"].get("DAMAGED", 0), st["by_status"].get("LOST", 0)]]
            rows, hl = [["ID", "Title", "Author(s)", "Category", "Shelf", "Copies", "Avail.", "Issued"]], {}
            for i, x in enumerate(rows_data, 1):
                b = x["book"]
                rows.append([b["book_id"], k["P"](b["title"] + (" (ref.)" if b["reference_only"] else "")),
                             k["P"](b["authors"]), b["category"], b["shelf"], x["total"], x["available"], x["issued"]])
                if not x["available"]:
                    hl[i] = "#fde2e1"
            return [k["table"](summary, [2.5] * 7, right=tuple(range(7))), k["S"](1, 10),
                    k["H"]("Books and availability (red = no copy on the shelf)"),
                    k["table"](rows, [1.3, 5.4, 3.6, 2.6, 1.3, 1.3, 1.2, 1.3], right=(5, 6, 7), highlight=hl)]
        return self._pdf("Available & Issued Books", f"As of {today().isoformat()}", build)

    def overdue_pdf(self) -> Path:
        rows_data = self.circ.overdue()
        mems = {m["member_id"]: m for m in self.db.all("members")}

        def build(k):
            if not rows_data:
                return [k["P"]("No overdue books.")]
            rows = [["Loan", "Accession", "Title", "Member", "Phone", "Due on", "Days", "Fine"]]
            for l in rows_data:
                rows.append([l["loan_id"], l["accession"], k["P"](l["title"]), k["P"](f"{l['member_name']} ({l['member_id']})"),
                             mems[l["member_id"]]["phone"], l["due_on"], l["days_overdue"], f"{l['fine_so_far']:,.2f}"])
            total = sum(l["fine_so_far"] for l in rows_data)
            return [k["table"](rows, [1.4, 1.8, 4.6, 3.8, 2.1, 1.9, 1.0, 1.6], right=(6, 7)), k["S"](1, 8),
                    k["P"](f"{len(rows_data)} overdue loan(s); fines accrued so far: Rs. {total:,.2f}")]
        return self._pdf("Overdue Books", f"As of {today().isoformat()}", build)

    def circulation_pdf(self, start, end) -> Path:
        s = self.circulation_summary(start, end)
        pop = self.popular_books(start, end)

        def build(k):
            kpi = [["Issued", "Returned", "Renewals", "Returned late", "On-time %", "Fines collected"],
                   [s["issued"], s["returned"], s["renewals"], s["returned_late"], f"{s['on_time_rate']}%",
                    f"{s['fines']['collected']:,.2f}"]]
            cats = [["Category", "Issues"]] + [[c, n] for c, n in s["by_category"].items()]
            types = [["Member type", "Issues"]] + [[t, n] for t, n in s["by_member_type"].items()]
            popular = [["#", "Title", "Author(s)", "Issues", "Waiting"]] + \
                [[i, k["P"](p["book"]["title"]), k["P"](p["book"]["authors"]), p["issues"], p["waiting"]]
                 for i, p in enumerate(pop, 1)]
            fines = [["Fines", "Amount"], ["Raised", f"{s['fines']['raised']:,.2f}"],
                     ["Collected", f"{s['fines']['collected']:,.2f}"], ["Waived", f"{s['fines']['waived']:,.2f}"],
                     ["Outstanding (all time)", f"{s['fines']['outstanding_total']:,.2f}"]]
            from reportlab.platypus import Table
            side = Table([[k["table"](cats, [4.2, 1.6], right=(1,)), k["table"](types, [3, 1.6], right=(1,)),
                           k["table"](fines, [3.6, 2.2], right=(1,))]], hAlign="LEFT",
                         style=[("VALIGN", (0, 0), (-1, -1), "TOP")])
            return [k["table"](kpi, [2.6, 2.6, 2.6, 2.9, 2.6, 3.2], right=tuple(range(6))), k["S"](1, 10), side,
                    k["S"](1, 10), k["H"]("Most borrowed books"),
                    k["table"](popular, [0.8, 7.4, 5.2, 1.5, 1.6], right=(3, 4))]
        return self._pdf("Circulation Report", f"Period {s['start']} to {s['end']}", build)
