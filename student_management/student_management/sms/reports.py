"""Reports: PDF report card, mark list, rank list and attendance report;
CSV exports of students, mark lists, rank lists and attendance."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .attendance import AttendanceManager
from .database import JSONDatabase
from .results import ResultProcessor
from .students import ClassManager, StudentManager
from .utils import INSTITUTION, INSTITUTION_ADDRESS, MIN_ATTENDANCE, PASS_MARK, SUBJECTS, SMSError

BRAND = "#264653"


class ReportGenerator:
    def __init__(self, db: JSONDatabase, report_dir: Path | str):
        self.db = db
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.results = ResultProcessor(db)
        self.students = StudentManager(db)
        self.classes = ClassManager(db)
        self.attendance = AttendanceManager(db)

    def _stamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------ pdf kit
    def _kit(self):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        st = getSampleStyleSheet()
        k = type("Kit", (), {})()
        k.colors, k.A4, k.landscape, k.cm, k.P, k.Doc, k.Spacer, k.Table, k.TS = \
            colors, A4, landscape, cm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        k.st = st
        k.small = ParagraphStyle("s", parent=st["Normal"], fontSize=8.5, leading=11)

        def table(rows, widths, right=(), center=(), highlight=None):
            t = Table(rows, colWidths=[w * cm for w in widths], repeatRows=1, hAlign="LEFT")
            sty = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                   ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b7c4c9")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f6")])]
            sty += [("ALIGN", (c, 1), (c, -1), "RIGHT") for c in right]
            sty += [("ALIGN", (c, 0), (c, -1), "CENTER") for c in center]
            for row, col in (highlight or {}).items():
                sty.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor(col)))
            t.setStyle(TableStyle(sty))
            return t
        k.table = table

        def head(title: str, subtitle: str):
            return [Paragraph(INSTITUTION, st["Title"]),
                    Paragraph(INSTITUTION_ADDRESS, ParagraphStyle("a", parent=st["Normal"], alignment=1, textColor=colors.grey)),
                    Spacer(1, 6), Paragraph(title, st["Heading2"]), Paragraph(subtitle, st["Normal"]), Spacer(1, 8)]
        k.head = head
        return k

    # ========================================================== report card
    def report_card_pdf(self, roll_no: str, exam: str) -> Path:
        k = self._kit()
        r = self.results.student_result(roll_no, exam)
        s = self.students.get(roll_no)
        cls = self.classes.get(s["class_code"])
        rank = self.results.rank_of(roll_no, r["exam"])
        out = self.report_dir / "report_cards"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"report_card_{s['roll_no']}_{r['exam'].replace(' ', '_')}.pdf"
        doc = k.Doc(str(path), pagesize=k.A4, leftMargin=1.8 * k.cm, rightMargin=1.8 * k.cm, topMargin=1.4 * k.cm,
                    bottomMargin=1.4 * k.cm, title=f"Report card {s['roll_no']}")
        info = k.Table([["Name", s["name"], "Roll No", s["roll_no"]],
                        ["Class", f"{cls['name']} ({cls['code']})", "Semester", str(cls["semester"])],
                        ["Course", cls["course"], "Academic year", cls["academic_year"]],
                        ["Guardian", s.get("guardian_name") or "-", "Exam", r["exam"]]],
                       colWidths=[2.8 * k.cm, 6.4 * k.cm, 3 * k.cm, 5.2 * k.cm])
        info.setStyle(k.TS([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                            ("BOX", (0, 0), (-1, -1), 0.5, k.colors.grey),
                            ("INNERGRID", (0, 0), (-1, -1), 0.25, k.colors.HexColor("#d5dde0"))]))
        rows = [["Subject", "Max", "Pass", "Marks", "Grade", "Result"]]
        hl = {}
        for i, x in enumerate(r["subjects"], 1):
            rows.append([x["subject"], x["max"], PASS_MARK, x["marks"], x["grade"], x["result"]])
            if x["result"] != "PASS":
                hl[i] = "#fde2e1"
        rows.append(["TOTAL", r["max_total"], "", f"{r['total']:g}", r["grade"], r["result"]])
        marks = k.table(rows, [5.4, 2.2, 2.2, 2.6, 2.4, 2.6], center=(1, 2, 3, 4, 5), highlight=hl)
        marks.setStyle(k.TS([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                             ("BACKGROUND", (0, -1), (-1, -1), k.colors.HexColor("#dfe9ec"))]))
        summary = k.table([["Percentage", "Average", "GPA (10)", "Rank", "Division", "Attendance"],
                           [f"{r['percent']:.2f}%", f"{r['average']:g}", f"{r['gpa']:.2f}", rank or "-", r["division"],
                            f"{r['attendance']:.1f}%"]], [2.6, 2.2, 2.2, 1.8, 5.4, 3.2], center=tuple(range(6)))
        notes = []
        if r["failed_subjects"]:
            notes.append(f"Failed / absent in: {', '.join(r['failed_subjects'])}. Supplementary examination required.")
        if r["attendance_shortage"]:
            notes.append(f"Attendance is below the required {MIN_ATTENDANCE:g}%."
                         + ("" if r["eligible"] else " Not eligible for the semester examination results until condoned."))
        if rank == 1:
            notes.append("Congratulations — class topper!")
        story = k.head("Student Report Card", f"{r['exam']} · issued {datetime.now():%d %b %Y}") + \
            [info, k.Spacer(1, 12), marks, k.Spacer(1, 10), summary, k.Spacer(1, 10)] + \
            [k.P(n, k.small) for n in notes] + [k.Spacer(1, 40)]
        sig = k.Table([["Class Teacher", "Head of Department", "Principal"]], colWidths=[5.8 * k.cm] * 3)
        sig.setStyle(k.TS([("LINEABOVE", (0, 0), (-1, 0), 0.6, k.colors.black), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("FONTSIZE", (0, 0), (-1, -1), 9)]))
        doc.build(story + [sig, k.Spacer(1, 10),
                           k.P(f"Grading: O ≥90 · A+ ≥80 · A ≥70 · B+ ≥60 · B ≥50 · C ≥40 · F <40. Pass mark {PASS_MARK} "
                               "in every subject.".replace("≥", ">="), k.small)])
        return path

    # ============================================================ mark list
    def mark_list_pdf(self, class_code: str, exam: str) -> Path:
        k = self._kit()
        res = self.results.class_result(class_code, exam)
        if not res["rows"]:
            raise SMSError("No marks entered for this class and exam.")
        cls = self.classes.get(class_code)
        path = self.report_dir / f"mark_list_{cls['code']}_{res['exam'].replace(' ', '_')}_{self._stamp()}.pdf"
        doc = k.Doc(str(path), pagesize=k.landscape(k.A4), leftMargin=1.2 * k.cm, rightMargin=1.2 * k.cm,
                    topMargin=1.2 * k.cm, bottomMargin=1.2 * k.cm, title="Mark list")
        hdr = ["Roll No", "Name"] + SUBJECTS + ["Total", "%", "Grade", "Result", "Rank", "Attendance"]
        rows, hl = [hdr], {}
        for i, r in enumerate(sorted(res["rows"], key=lambda x: x["roll_no"]), 1):
            rows.append([r["roll_no"], k.P(escape(r["name"]), k.small)] +
                        [next(x["marks"] for x in r["subjects"] if x["subject"] == s) for s in SUBJECTS] +
                        [f"{r['total']:g}", f"{r['percent']:.1f}", r["grade"], r["result"], r["rank"] or "-",
                         f"{r['attendance']:.0f}%"])
            if not r["passed"]:
                hl[i] = "#fde2e1"
            elif r["rank"] == 1:
                hl[i] = "#fff3c4"
        n = len(SUBJECTS)
        table = k.table(rows, [2.4, 5.2] + [1.9] * n + [1.8, 1.6, 1.6, 1.8, 1.4, 2.2],
                        center=tuple(range(2, len(hdr))), highlight=hl)
        stats = [["Subject", "Appeared", "Absent", "Passed", "Pass %", "Average", "Highest", "Lowest", "Topper(s)"]] + \
            [[s, v["appeared"], v["absent"], v["passed"], f"{v['pass_percent']}%", v["average"], v["highest"], v["lowest"],
              k.P(escape(", ".join(v["toppers"])), k.small)] for s, v in res["subject_stats"].items()]
        tops = ", ".join(f"{t['name']} ({t['roll_no']}, {t['percent']:.1f}%)" for t in res["toppers"]) or "-"
        summary = (f"Appeared {res['appeared']} · passed {res['passed']} · failed {res['failed']} · pass percentage "
                   f"{res['pass_percent']}% · class average {res['class_average']}% · distinctions {res['distinctions']} · "
                   f"<b>Class topper: {escape(tops)}</b>")
        doc.build(k.head(f"Mark List — {cls['name']} ({cls['code']})",
                         f"{res['exam']} · {'published' if res['published'] else 'PROVISIONAL (not yet published)'} · "
                         f"generated {datetime.now():%d %b %Y}") +
                  [table, k.Spacer(1, 8), k.P(summary, k.st["Normal"]), k.Spacer(1, 10),
                   k.P("Subject analysis", k.st["Heading3"]),
                   k.table(stats, [3, 2, 1.8, 1.8, 1.8, 2, 2, 2, 8.2], center=(1, 2, 3, 4, 5, 6, 7))])
        return path

    # ============================================================ rank list
    def rank_list_pdf(self, class_code: str, exam: str) -> Path:
        k = self._kit()
        res = self.results.class_result(class_code, exam)
        ranked = [r for r in res["rows"] if r["rank"]]
        if not ranked:
            raise SMSError("No passed students to rank yet.")
        cls = self.classes.get(class_code)
        path = self.report_dir / f"rank_list_{cls['code']}_{res['exam'].replace(' ', '_')}_{self._stamp()}.pdf"
        doc = k.Doc(str(path), pagesize=k.A4, leftMargin=1.8 * k.cm, rightMargin=1.8 * k.cm, topMargin=1.4 * k.cm,
                    bottomMargin=1.4 * k.cm, title="Rank list")
        rows = [["Rank", "Roll No", "Name", "Total", "%", "Grade", "Division"]]
        hl = {}
        for i, r in enumerate(ranked, 1):
            rows.append([r["rank"], r["roll_no"], k.P(escape(r["name"]), k.small), f"{r['total']:g}",
                         f"{r['percent']:.2f}", r["grade"], k.P(r["division"], k.small)])
            if r["rank"] <= 3:
                hl[i] = {1: "#fff3c4", 2: "#eef1f3", 3: "#f6e7da"}[r["rank"]]
        failed = [r for r in res["rows"] if not r["rank"]]
        story = k.head(f"Rank List — {cls['name']} ({cls['code']})",
                       f"{res['exam']} · {len(ranked)} passed of {res['appeared']} · ties share a rank") + \
            [k.table(rows, [1.4, 2.4, 5.4, 1.8, 1.8, 1.6, 3.4], center=(0, 3, 4, 5), highlight=hl)]
        if failed:
            story += [k.Spacer(1, 8), k.P(f"Not ranked (failed / absent in a subject): "
                                          f"{', '.join(r['roll_no'] for r in failed)}", k.small)]
        doc.build(story)
        return path

    # =========================================================== attendance
    def attendance_pdf(self, class_code: str, start=None, end=None) -> Path:
        k = self._kit()
        cs = self.attendance.class_summary(class_code, start, end)
        cls = self.classes.get(class_code)
        path = self.report_dir / f"attendance_{cls['code']}_{self._stamp()}.pdf"
        doc = k.Doc(str(path), pagesize=k.A4, leftMargin=1.8 * k.cm, rightMargin=1.8 * k.cm, topMargin=1.4 * k.cm,
                    bottomMargin=1.4 * k.cm, title="Attendance report")
        rows, hl = [["Roll No", "Name", "Days", "Present", "Absent", "Leave", "%", "Status"]], {}
        for i, r in enumerate(cs["students"], 1):
            rows.append([r["roll_no"], k.P(escape(r["name"]), k.small), r["days"], r["present"], r["absent"], r["leave"],
                         f"{r['percent']:.1f}", "SHORTAGE" if r["shortage"] else "OK"])
            if r["shortage"]:
                hl[i] = "#fde2e1"
        period = f"{start or 'start'} to {end or 'today'}"
        doc.build(k.head(f"Attendance Report — {cls['name']} ({cls['code']})",
                         f"Period {period} · {cs['days_marked']} working day(s) marked · class average {cs['average']}% · "
                         f"minimum required {MIN_ATTENDANCE:g}%") +
                  [k.table(rows, [2.4, 5.6, 1.4, 1.8, 1.8, 1.6, 1.6, 2.2], center=(2, 3, 4, 5, 6, 7), highlight=hl),
                   k.Spacer(1, 8), k.P(f"{len(cs['shortage'])} student(s) below {MIN_ATTENDANCE:g}% attendance.", k.small)])
        return path

    # ================================================================== CSV
    def _csv(self, stem: str, header: list, rows: list) -> Path:
        path = self.report_dir / f"{stem}_{self._stamp()}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return path

    def students_csv(self, class_code: str | None = None) -> Path:
        return self._csv("students", ["Roll No", "Name", "Gender", "DOB", "Phone", "Email", "Guardian", "Guardian Phone",
                                      "Class", "Admission Date", "Status", "Address"],
                         [[s["roll_no"], s["name"], s["gender"], s["dob"], s["phone"], s["email"], s["guardian_name"],
                           s["guardian_phone"], s["class_code"], s["admission_date"], s["status"], s["address"]]
                          for s in self.students.list(class_code, status=None)])

    def mark_list_csv(self, class_code: str, exam: str) -> Path:
        res = self.results.class_result(class_code, exam)
        return self._csv(f"mark_list_{class_code.upper()}_{res['exam'].replace(' ', '_')}",
                         ["Roll No", "Name"] + SUBJECTS + ["Total", "Average", "Percent", "Grade", "GPA", "Result",
                                                           "Division", "Rank", "Attendance %"],
                         [[r["roll_no"], r["name"]] + [next(x["marks"] for x in r["subjects"] if x["subject"] == s)
                                                       for s in SUBJECTS] +
                          [r["total"], r["average"], r["percent"], r["grade"], r["gpa"], r["result"], r["division"],
                           r["rank"] or "", r["attendance"]] for r in sorted(res["rows"], key=lambda x: x["roll_no"])])

    def rank_list_csv(self, class_code: str, exam: str) -> Path:
        res = self.results.class_result(class_code, exam)
        return self._csv(f"rank_list_{class_code.upper()}_{res['exam'].replace(' ', '_')}",
                         ["Rank", "Roll No", "Name", "Total", "Percent", "Grade", "Division"],
                         [[r["rank"], r["roll_no"], r["name"], r["total"], r["percent"], r["grade"], r["division"]]
                          for r in res["rows"] if r["rank"]])

    def attendance_csv(self, class_code: str, month: str) -> Path:
        reg = self.attendance.monthly_register(class_code, month)
        return self._csv(f"attendance_{class_code.upper()}_{month}",
                         ["Roll No", "Name"] + [d[8:] for d in reg["dates"]] + ["Present", "Days", "%"],
                         [[r["roll_no"], r["name"]] + r["marks"] + [r["present"], r["taken"], r["percent"] if r["percent"] is not None else ""]
                          for r in reg["rows"]])
