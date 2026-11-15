"""Reports module: CSV export, PDF contact directory, vCard export and a
users report for the admin."""
from __future__ import annotations

import csv
from datetime import datetime
from xml.sax.saxutils import escape
from pathlib import Path

from .contacts import ContactManager
from .database import JSONDatabase
from .models import Contact
from .utils import APP_NAME, ContactBookError

CSV_HEADERS = ["First Name", "Last Name", "Phone", "Alternate Phone", "Email", "Company", "Job Title",
               "Address", "Birthday", "Category", "Favorite", "Notes"]


class ReportGenerator:
    def __init__(self, db: JSONDatabase, username: str, report_dir: Path | str):
        self.db = db
        self.username = username
        self.contacts = ContactManager(db, username)
        self.report_dir = Path(report_dir) / username
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, stem: str, ext: str) -> Path:
        return self.report_dir / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"

    def _select(self, category: str | None, favorites_only: bool) -> list[Contact]:
        contacts = self.contacts.list(category, favorites_only)
        if not contacts:
            raise ContactBookError("No contacts to export for that selection.")
        return contacts

    # ------------------------------------------------------------------ csv
    def export_csv(self, category: str | None = None, favorites_only: bool = False) -> Path:
        """CSV export. The same file format can be imported back."""
        contacts = self._select(category, favorites_only)
        path = self._path("contacts", "csv")
        with path.open("w", newline="", encoding="utf-8-sig") as fh:   # BOM so Excel shows ₹/Unicode
            w = csv.writer(fh)
            w.writerow(CSV_HEADERS)
            for c in contacts:
                w.writerow([c.first_name, c.last_name, c.phone, c.alt_phone, c.email, c.company, c.job_title,
                            c.address, c.birthday, c.category, "Yes" if c.favorite else "No", c.notes])
        return path

    # ---------------------------------------------------------------- vcard
    @staticmethod
    def _vescape(text: str) -> str:
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    def export_vcard(self, category: str | None = None, favorites_only: bool = False) -> Path:
        """vCard 3.0 file that phones and email apps (Google, Outlook, iPhone) can import."""
        contacts = self._select(category, favorites_only)
        path = self._path("contacts", "vcf")
        e = self._vescape
        lines = []
        for c in contacts:
            lines += ["BEGIN:VCARD", "VERSION:3.0",
                      f"N:{e(c.last_name)};{e(c.first_name)};;;", f"FN:{e(c.full_name)}",
                      f"TEL;TYPE=CELL:{c.phone}"]
            if c.alt_phone:
                lines.append(f"TEL;TYPE=HOME:{c.alt_phone}")
            if c.email:
                lines.append(f"EMAIL;TYPE=INTERNET:{c.email}")
            if c.company:
                lines.append(f"ORG:{e(c.company)}")
            if c.job_title:
                lines.append(f"TITLE:{e(c.job_title)}")
            if c.address:
                lines.append(f"ADR;TYPE=HOME:;;{e(c.address)};;;;")
            if c.birthday:
                lines.append(f"BDAY:{c.birthday}")
            if c.notes:
                lines.append(f"NOTE:{e(c.notes)}")
            lines += [f"CATEGORIES:{e(c.category)}" + (",Favorites" if c.favorite else ""), "END:VCARD"]
        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        return path

    # ------------------------------------------------------------------ pdf
    def export_pdf(self, category: str | None = None, favorites_only: bool = False,
                   group_by: str = "letter") -> Path:
        """PDF contact directory grouped by first letter or by category."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        contacts = self._select(category, favorites_only)
        path = self._path("contact_directory", "pdf")
        styles = getSampleStyleSheet()
        cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=10.5)
        group_style = ParagraphStyle("grp", parent=styles["Heading3"], textColor=colors.HexColor("#1d4e89"),
                                     spaceBefore=8, spaceAfter=4)
        doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=1.4 * cm, rightMargin=1.4 * cm,
                                topMargin=1.3 * cm, bottomMargin=1.3 * cm, title="Contact Directory")

        def footer(canvas, d):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawString(1.4 * cm, 0.8 * cm, f"{APP_NAME} — {self.username}")
            canvas.drawRightString(landscape(A4)[0] - 1.4 * cm, 0.8 * cm, f"Page {d.page}")
            canvas.restoreState()

        groups: dict[str, list[Contact]] = {}
        for c in contacts:
            key = c.category if group_by == "category" else (c.first_name[0].upper() if c.first_name[0].isalpha() else "#")
            groups.setdefault(key, []).append(c)

        subtitle = " · ".join(filter(None, [f"Category: {category}" if category else "",
                                            "Favourites only" if favorites_only else "",
                                            f"{len(contacts)} contacts", "* = favourite",
                                            f"Generated {datetime.now():%d %b %Y %H:%M}"]))
        story = [Paragraph("Contact Directory", styles["Title"]),
                 Paragraph(subtitle, ParagraphStyle("sub", parent=styles["Normal"], alignment=1,
                                                    textColor=colors.grey)),
                 Spacer(1, 10)]
        widths = [5.2 * cm, 3.9 * cm, 3.9 * cm, 5.6 * cm, 5 * cm, 3.2 * cm]
        for key in sorted(groups):
            rows = [["Name", "Phone", "Alt. Phone", "Email", "Company / Title", "Category"]]
            for c in groups[key]:
                name = f"<b>{escape(c.full_name)} *</b>" if c.favorite else escape(c.full_name)
                org = escape(" — ".join(filter(None, [c.company, c.job_title])))
                rows.append([Paragraph(name, cell), c.display_phone, c.alt_phone or "",
                             Paragraph(escape(c.email), cell), Paragraph(org, cell), c.category])
            t = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4e89")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f9")]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#c5d3e3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story += [Paragraph(escape(key), group_style), t]
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        return path


def export_users_report(db: JSONDatabase, report_dir: Path | str) -> Path:
    """Admin report: one row per user with contact counts (no private contact data)."""
    path = Path(report_dir) / f"users_report_{datetime.now():%Y%m%d_%H%M%S}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    contacts = db.all("contacts")
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Username", "Full Name", "Role", "Active", "Contacts", "Favourites", "In Recycle Bin",
                    "Categories", "Created At", "Last Login"])
        for u in sorted(db.all("users"), key=lambda u: u["username"]):
            mine = [c for c in contacts if c["owner"] == u["username"]]
            active = [c for c in mine if not c.get("deleted")]
            w.writerow([u["username"], u.get("full_name", ""), u["role"], "Yes" if u.get("active", True) else "No",
                        len(active), sum(1 for c in active if c.get("favorite")), len(mine) - len(active),
                        len(u.get("categories") or []), u.get("created_at", ""), u.get("last_login") or ""])
    return path
