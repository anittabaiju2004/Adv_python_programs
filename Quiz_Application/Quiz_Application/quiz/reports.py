"""Reports: PDF result / scorecard, PDF certificate, PDF performance report
with charts, PDF quiz report, and CSV exports."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .analysis import PerformanceAnalyzer
from .database import JSONDatabase
from .leaderboard import Leaderboard
from .questions import QuestionManager
from .results import ResultManager
from .utils import APP_NAME, ORGANISATION, QuizError, fmt_duration

BRAND = "#2a6f97"


class ReportGenerator:
    def __init__(self, db: JSONDatabase, report_dir: Path | str):
        self.db = db
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.results = ResultManager(db)
        self.analyzer = PerformanceAnalyzer(db)

    def _name(self, username: str) -> str:
        u = self.db.find_one("users", username=username) or {}
        return u.get("name", username)

    def _stamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ============================================================ result PDF
    def result_pdf(self, result_id: str) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        r = self.results.get(result_id)
        path = self.report_dir / "results" / f"result_{r['result_id']}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        st = getSampleStyleSheet()
        small = ParagraphStyle("s", parent=st["Normal"], fontSize=8.5, leading=11)
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                topMargin=1.4 * cm, bottomMargin=1.4 * cm, title=f"Result {r['result_id']}")
        verdict = "PASSED" if r["passed"] else "NOT PASSED"
        color = "#2e9d5b" if r["passed"] else "#d1495b"
        summary = Table([["Student", f"{self._name(r['username'])} ({r['username']})", "Result ID", r["result_id"]],
                         ["Quiz", r["quiz_title"], "Mode", r["mode"]],
                         ["Submitted", r["submitted_at"].replace("T", " "), "Time taken",
                          fmt_duration(r["duration_sec"]) + (" (time up)" if r["time_up"] else "")]],
                        colWidths=[2.6 * cm, 6.4 * cm, 2.6 * cm, 6.2 * cm])
        summary.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                                     ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold")]))
        score = Table([["Score", "Percentage", "Grade", "Correct", "Wrong", "Skipped", "Result"],
                       [f"{r['score']:g} / {r['max_score']}", f"{r['percent']:.1f}%", r["grade"], r["correct"], r["wrong"],
                        r["skipped"], verdict]], colWidths=[2.8 * cm, 2.6 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 4.4 * cm])
        score.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
                                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 9),
                                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                   ("FONTSIZE", (0, 1), (-1, 1), 12), ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                                   ("TEXTCOLOR", (6, 1), (6, 1), colors.HexColor(color)),
                                   ("BOX", (0, 0), (-1, -1), 0.5, colors.grey), ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.grey)]))
        rows = [["#", "Question", "Your answer", "Correct answer", "Marks"]]
        hl = []
        for i, a in enumerate(r["answers"], 1):
            yours = a["options"][a["chosen"]] if a["chosen"] is not None else "— skipped —"
            q = escape(a["text"]) + (f"<br/><font color='#666'><i>{escape(a['explanation'])}</i></font>" if a["explanation"] else "")
            rows.append([str(i), Paragraph(q, small), Paragraph(escape(yours), small),
                         Paragraph(escape(a["options"][a["answer"]]), small), f"{a['marks']:+g}"])
            hl.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(
                {"CORRECT": "#e6f4ea", "WRONG": "#fdecea", "SKIPPED": "#f5f5f5"}[a["status"]])))
        review = Table(rows, colWidths=[0.8 * cm, 8.6 * cm, 3.4 * cm, 3.4 * cm, 1.6 * cm], repeatRows=1)
        review.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c9d6df")),
                                    ("ALIGN", (4, 1), (4, -1), "RIGHT")] + hl))
        story = [Paragraph(APP_NAME, st["Title"]), Paragraph("Quiz Result", st["Heading2"]), summary, Spacer(1, 8), score]
        if r["negative_marks"]:
            story.append(Paragraph(f"Negative marking deducted {r['negative_marks']:g} mark(s).", small))
        story += [Spacer(1, 10), Paragraph("Answer review (green = correct, red = wrong, grey = skipped)", st["Heading3"]),
                  review]
        if r["certificate_code"]:
            story += [Spacer(1, 8), Paragraph(f"Certificate issued — ID {r['result_id']}, verification code "
                                              f"<b>{r['certificate_code']}</b>.", small)]
        doc.build(story)
        return path

    # =========================================================== certificate
    def certificate_pdf(self, result_id: str) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas

        r = self.results.get(result_id)
        if not r["certificate_code"]:
            raise QuizError("Certificates are issued only for passed exam attempts.")
        path = self.report_dir / "certificates" / f"certificate_{r['result_id']}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        w, h = landscape(A4)
        c = canvas.Canvas(str(path), pagesize=(w, h))
        gold, navy = colors.HexColor("#b8860b"), colors.HexColor("#1f3a5f")
        c.setStrokeColor(navy)
        c.setLineWidth(6)
        c.rect(22, 22, w - 44, h - 44)
        c.setStrokeColor(gold)
        c.setLineWidth(1.5)
        c.rect(34, 34, w - 68, h - 68)
        for x, y in ((34, 34), (w - 34, 34), (34, h - 34), (w - 34, h - 34)):
            c.setFillColor(gold)
            c.circle(x, y, 6, fill=1, stroke=0)
        c.setFillColor(navy)
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(w / 2, h - 80, ORGANISATION.upper())
        c.setFont("Times-Bold", 40)
        c.drawCentredString(w / 2, h - 140, "Certificate of Achievement")
        c.setFillColor(colors.black)
        c.setFont("Times-Italic", 16)
        c.drawCentredString(w / 2, h - 185, "This is to certify that")
        c.setFillColor(navy)
        c.setFont("Times-Bold", 32)
        name = self._name(r["username"])
        c.drawCentredString(w / 2, h - 230, name)
        c.setStrokeColor(gold)
        c.setLineWidth(1)
        c.line(w / 2 - 180, h - 240, w / 2 + 180, h - 240)
        c.setFillColor(colors.black)
        c.setFont("Times-Roman", 16)
        c.drawCentredString(w / 2, h - 275, "has successfully completed the online examination")
        c.setFont("Times-Bold", 20)
        c.drawCentredString(w / 2, h - 305, r["quiz_title"])
        c.setFont("Times-Roman", 16)
        c.drawCentredString(w / 2, h - 340, f"scoring {r['percent']:.1f}%  ·  Grade {r['grade']} ({r['remark']})")
        c.setFont("Helvetica", 10)
        c.drawString(70, 95, f"Date: {r['submitted_at'][:10]}")
        c.drawString(70, 80, f"Certificate ID: {r['result_id']}")
        c.drawString(70, 65, f"Verification code: {r['certificate_code']}")
        c.line(w - 270, 100, w - 80, 100)
        c.drawCentredString(w - 175, 85, "Examination Controller")
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(w / 2, 48, f"Verify this certificate in {APP_NAME} → 'Verify a certificate' using the ID and code.")
        c.showPage()
        c.save()
        return path

    # ===================================================== performance PDF
    def performance_pdf(self, username: str) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        s = self.analyzer.student(username)
        if not s["attempts"]:
            raise QuizError("No quiz attempts yet.")
        charts = self.analyzer.student_charts(username, self.report_dir / "charts")
        path = self.report_dir / f"performance_{username}_{self._stamp()}.pdf"
        st = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                topMargin=1.3 * cm, bottomMargin=1.3 * cm, title=f"Performance {username}")
        kpi = Table([["Attempts", "Average", "Best", "Accuracy", "Exam pass rate", "Certificates"],
                     [s["attempts"], f"{s['average']}%", f"{s['best']:.1f}%", f"{s['accuracy']}%",
                      f"{s['pass_rate']}%" if s["pass_rate"] is not None else "-", s["certificates"]]],
                    colWidths=[2.95 * cm] * 6)
        kpi.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, 0), 8), ("TEXTCOLOR", (0, 0), (-1, 0), colors.grey),
                                 ("FONTSIZE", (0, 1), (-1, 1), 14), ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                                 ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor(BRAND)), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                 ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d6df"))]))
        diff = [["Difficulty", "Questions", "Correct", "Accuracy"]] + \
            [[d, v["total"], v["correct"], f"{v['accuracy']}%"] for d, v in s["by_difficulty"].items()]
        dt = Table(diff, colWidths=[3.5 * cm, 3 * cm, 3 * cm, 3 * cm], hAlign="LEFT")
        dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 9),
                                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c9d6df"))]))
        notes = []
        if s["weak_areas"]:
            notes.append(f"<b>Focus on:</b> {', '.join(s['weak_areas'])} (accuracy below 60%).")
        if s["strengths"]:
            notes.append(f"<b>Strengths:</b> {', '.join(s['strengths'])}.")
        if s["improvement"] is not None:
            notes.append(f"<b>Trend:</b> last 3 attempts average {s['improvement']:+.1f} points compared with the first 3.")
        notes.append(f"Average time per question: {s['avg_sec_per_question']} s.")
        story = [Paragraph(f"{APP_NAME} — Performance Report", st["Title"]),
                 Paragraph(f"{self._name(username)} ({username}) · generated {datetime.now():%d %b %Y %H:%M}", st["Normal"]),
                 Spacer(1, 10), kpi, Spacer(1, 10), Image(str(charts[0]), width=17 * cm, height=7.6 * cm),
                 Image(str(charts[1]), width=17 * cm, height=min(9, 0.9 * len(s["by_category"]) + 2.5) * cm),
                 Spacer(1, 6), dt, Spacer(1, 8)] + [Paragraph(n, st["Normal"]) for n in notes]
        doc.build(story)
        return path

    # ============================================================ quiz PDF
    def quiz_pdf(self, quiz_id: str) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        q = self.analyzer.quiz(quiz_id)
        if not q["attempts"]:
            raise QuizError("No exam attempts for this quiz yet.")
        chart = self.analyzer.quiz_chart(quiz_id, self.report_dir / "charts")
        board = Leaderboard(self.db).for_quiz(quiz_id, top=10)
        path = self.report_dir / f"quiz_report_{quiz_id}_{self._stamp()}.pdf"
        st = getSampleStyleSheet()
        small = ParagraphStyle("s", parent=st["Normal"], fontSize=8.5, leading=11)
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                topMargin=1.3 * cm, bottomMargin=1.3 * cm, title=f"Quiz report {quiz_id}")

        def tbl(rows, widths):
            t = Table(rows, colWidths=[x * cm for x in widths], hAlign="LEFT", repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
                                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                   ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c9d6df"))]))
            return t
        stats = [["Attempts", "Students", "Average", "Highest", "Lowest", "Pass rate", "Avg time"],
                 [q["attempts"], q["students"], f"{q['average']}%", f"{q['highest']:.1f}%", f"{q['lowest']:.1f}%",
                  f"{q['pass_rate']}%", fmt_duration(q["avg_duration"])]]
        top = [["Rank", "Student", "Score", "Grade", "Time", "Date"]] + \
            [[b["rank"], b["name"], f"{b['percent']:.1f}%", b["grade"], fmt_duration(b["duration_sec"]), b["date"]] for b in board]
        hard = [["Question", "Attempts", "Correct %"]] + \
            [[Paragraph(escape(h["text"]), small), h["attempts"], f"{h['correct_pct']}%"] for h in q["hardest"]]
        doc.build([Paragraph(f"Quiz Report — {q['title']}", st["Title"]),
                   Paragraph(f"{quiz_id} · exam attempts only · generated {datetime.now():%d %b %Y %H:%M}", st["Normal"]),
                   Spacer(1, 8), tbl(stats, [2.4] * 7), Spacer(1, 8), Image(str(chart), width=15 * cm, height=7.3 * cm),
                   Paragraph("Top 10", st["Heading3"]), tbl(top, [1.3, 5.5, 2.2, 1.6, 2.4, 2.6]),
                   Paragraph("Hardest questions (lowest % correct)", st["Heading3"]), tbl(hard, [12.5, 2, 2.2])])
        return path

    # ================================================================ CSV
    def _csv(self, stem: str, header: list, rows: list) -> Path:
        path = self.report_dir / f"{stem}_{self._stamp()}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return path

    def results_csv(self, quiz_id: str | None = None, start=None, end=None) -> Path:
        rs = self.results.list(quiz_id=quiz_id, start=start, end=end)
        return self._csv("results", ["Result ID", "Username", "Name", "Quiz", "Mode", "Submitted", "Duration (s)",
                                     "Time Up", "Correct", "Wrong", "Skipped", "Score", "Max", "Percent", "Grade", "Passed"],
                         [[r["result_id"], r["username"], self._name(r["username"]), r["quiz_title"], r["mode"],
                           r["submitted_at"], r["duration_sec"], r["time_up"], r["correct"], r["wrong"], r["skipped"],
                           r["score"], r["max_score"], r["percent"], r["grade"], "Yes" if r["passed"] else "No"] for r in rs])

    def leaderboard_csv(self, quiz_id: str | None = None, period: str = "all") -> Path:
        lb = Leaderboard(self.db)
        if quiz_id:
            rows = lb.for_quiz(quiz_id, period, top=None)
            return self._csv(f"leaderboard_{quiz_id}", ["Rank", "Username", "Name", "Percent", "Grade", "Time (s)", "Date"],
                             [[r["rank"], r["username"], r["name"], r["percent"], r["grade"], r["duration_sec"], r["date"]]
                              for r in rows])
        rows = lb.overall(period, top=None)
        return self._csv("leaderboard_overall", ["Rank", "Username", "Name", "Quizzes", "Average best %", "Points"],
                         [[r["rank"], r["username"], r["name"], r["quizzes"], r["average"], r["points"]] for r in rows])

    def item_analysis_csv(self) -> Path:
        return self._csv("question_analysis", ["Question ID", "Category", "Difficulty", "Question", "Attempts",
                                               "Correct %", "Skipped %"],
                         [[s["question"]["question_id"], s["question"]["category"], s["question"]["difficulty"],
                           s["question"]["text"], s["attempts"], s["correct_pct"], s["skipped_pct"]]
                          for s in QuestionManager(self.db).item_analysis()])

    def users_csv(self) -> Path:
        an = self.analyzer
        rows = []
        for u in sorted(self.db.all("users"), key=lambda u: u["username"]):
            s = an.student(u["username"]) if u["role"] == "student" else {"attempts": 0}
            rows.append([u["username"], u["name"], u["role"], u.get("email", ""), u.get("institution", ""),
                         "Yes" if u["active"] else "No", s["attempts"], s.get("average", ""), s.get("certificates", ""),
                         u["created_at"][:10], (u["last_login"] or "")[:16]])
        return self._csv("users", ["Username", "Name", "Role", "Email", "Institution", "Active", "Attempts", "Average %",
                                   "Certificates", "Registered", "Last Login"], rows)
