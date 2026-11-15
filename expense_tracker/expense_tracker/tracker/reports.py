"""Reports: summaries, monthly/yearly analytics, CSV & PDF export, Matplotlib charts."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .budget import BudgetManager
from .database import JSONDatabase
from .exceptions import TrackerError
from .savings import SavingsManager
from .transactions import ExpenseManager, IncomeManager


class ReportGenerator:
    def __init__(self, db: JSONDatabase, username: str, report_dir: Path | str):
        self.db = db
        self.username = username
        self.report_dir = Path(report_dir) / username
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.expenses = ExpenseManager(db, username)
        self.incomes = IncomeManager(db, username)
        self.budgets = BudgetManager(db, username)
        self.savings = SavingsManager(db, username)

    def _stamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------ analytics
    def monthly_summary(self, month: str) -> dict:
        exp = self.expenses.total(month=month)
        inc = self.incomes.total(month=month)
        items = self.expenses.for_month(month)
        days = {t.date for t in items}
        return {
            "period": month,
            "income": inc,
            "expense": exp,
            "net": round(inc - exp, 2),
            "savings_rate": round((inc - exp) / inc * 100, 1) if inc else 0.0,
            "transactions": len(items),
            "avg_per_active_day": round(exp / len(days), 2) if days else 0.0,
            "largest": max(items, key=lambda t: t.amount) if items else None,
            "by_category": self.expenses.by_category(month=month),
        }

    def yearly_summary(self, year: str) -> dict:
        year = str(year)
        exp_m = self.expenses.by_month(year)
        inc_m = self.incomes.by_month(year)
        exp, inc = sum(exp_m.values()), sum(inc_m.values())
        active = [m for m, v in exp_m.items() if v > 0]
        top_month = max(exp_m, key=exp_m.get) if active else None
        return {
            "period": year,
            "income": round(inc, 2),
            "expense": round(exp, 2),
            "net": round(inc - exp, 2),
            "savings_rate": round((inc - exp) / inc * 100, 1) if inc else 0.0,
            "avg_monthly_expense": round(exp / len(active), 2) if active else 0.0,
            "highest_spending_month": top_month,
            "monthly_expense": exp_m,
            "monthly_income": inc_m,
            "by_category": self.expenses.by_category(year=year),
        }

    # ------------------------------------------------------------------ csv
    def export_csv(self, start: str | None = None, end: str | None = None) -> Path:
        path = self.report_dir / f"transactions_{self._stamp()}.csv"
        rows = [("Expense", e) for e in self.expenses.list(start, end)]
        rows += [("Income", i) for i in self.incomes.list(start, end)]
        rows.sort(key=lambda r: r[1].date)
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["ID", "Type", "Date", "Category/Source", "Amount", "Payment Mode", "Description"])
            for kind, t in rows:
                w.writerow([t.id, kind, t.date, t.category, f"{t.amount:.2f}",
                            getattr(t, "payment_mode", ""), t.description])
        return path

    # --------------------------------------------------------------- charts
    def _plt(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt

    def chart_category_pie(self, month: str | None = None, year: str | None = None) -> Path:
        data = self.expenses.by_category(month=month, year=year)
        if not data:
            raise TrackerError("No expense data for that period.")
        plt = self._plt()
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.pie(data.values(), labels=data.keys(), autopct="%1.1f%%", startangle=90,
               wedgeprops={"edgecolor": "white"})
        ax.set_title(f"Expenses by Category — {month or year or 'All time'}")
        ax.axis("equal")
        path = self.report_dir / f"category_pie_{self._stamp()}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    def chart_monthly_trend(self, year: str) -> Path:
        year = str(year)
        exp = self.expenses.by_month(year)
        inc = self.incomes.by_month(year)
        labels = [datetime.strptime(m, "%Y-%m").strftime("%b") for m in exp]
        plt = self._plt()
        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(labels))
        ax.bar([i - 0.2 for i in x], list(inc.values()), width=0.4, label="Income", color="#2e9d5b")
        ax.bar([i + 0.2 for i in x], list(exp.values()), width=0.4, label="Expense", color="#d1495b")
        ax.set_xticks(list(x), labels)
        ax.set_title(f"Monthly Income vs Expense — {year}")
        ax.set_ylabel("Amount")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        path = self.report_dir / f"monthly_trend_{year}_{self._stamp()}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    def chart_budget(self, month: str) -> Path:
        statuses = self.budgets.status(month)
        if not statuses:
            raise TrackerError(f"No budgets set for {month}.")
        plt = self._plt()
        fig, ax = plt.subplots(figsize=(9, 0.6 * len(statuses) + 1.5))
        names = [s.budget.category for s in statuses]
        colors = {"OK": "#2e9d5b", "WARNING": "#f0a202", "EXCEEDED": "#d1495b"}
        ax.barh(names, [s.budget.limit for s in statuses], color="#e0e0e0", label="Limit")
        ax.barh(names, [s.spent for s in statuses], color=[colors[s.level] for s in statuses],
                height=0.5, label="Spent")
        ax.invert_yaxis()
        ax.set_title(f"Budget Utilisation — {month}")
        ax.legend()
        path = self.report_dir / f"budget_{month}_{self._stamp()}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    # ------------------------------------------------------------------ pdf
    def export_pdf(self, month: str | None = None, year: str | None = None) -> Path:
        """PDF report for a month (YYYY-MM) or a year (YYYY)."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,
                                        TableStyle)

        if not (month or year):
            raise TrackerError("Specify a month or a year for the PDF report.")
        summary = self.monthly_summary(month) if month else self.yearly_summary(year)
        period = summary["period"]
        path = self.report_dir / f"report_{period}_{self._stamp()}.pdf"
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                                topMargin=1.8 * cm, bottomMargin=1.8 * cm)

        def table(data, widths, header_color="#34495e"):
            t = Table(data, colWidths=widths, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            return t

        story = [
            Paragraph("Personal Expense Report", styles["Title"]),
            Paragraph(f"User: <b>{self.username}</b> &nbsp;&nbsp; Period: <b>{period}</b> &nbsp;&nbsp; "
                      f"Generated: {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("Summary", styles["Heading2"]),
            table([["Metric", "Value"],
                   ["Total Income", f"{summary['income']:,.2f}"],
                   ["Total Expense", f"{summary['expense']:,.2f}"],
                   ["Net Savings", f"{summary['net']:,.2f}"],
                   ["Savings Rate", f"{summary['savings_rate']}%"]], [8 * cm, 5 * cm]),
            Spacer(1, 12),
        ]

        cats = summary["by_category"]
        if cats:
            total = sum(cats.values())
            story += [Paragraph("Expenses by Category", styles["Heading2"]),
                      table([["Category", "Share", "Amount"]] +
                            [[c, f"{v / total * 100:.1f}%", f"{v:,.2f}"] for c, v in cats.items()],
                            [6 * cm, 3 * cm, 4 * cm]),
                      Spacer(1, 12)]
            try:
                pie = self.chart_category_pie(month=month, year=year)
                story += [Image(str(pie), width=11 * cm, height=9.4 * cm), Spacer(1, 12)]
            except Exception:
                pass

        if month:
            statuses = self.budgets.status(month)
            if statuses:
                story += [Paragraph("Budget Status", styles["Heading2"]),
                          table([["Category", "Limit", "Spent", "Status"]] +
                                [[s.budget.category, f"{s.budget.limit:,.2f}", f"{s.spent:,.2f}", s.level]
                                 for s in statuses], [5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm]),
                          Spacer(1, 12)]
            items = self.expenses.for_month(month)
            if items:
                story += [Paragraph("Expense Transactions", styles["Heading2"]),
                          table([["Date", "Category", "Description", "Amount"]] +
                                [[t.date, t.category, (t.description or "-")[:40], f"{t.amount:,.2f}"]
                                 for t in sorted(items, key=lambda t: t.date)],
                                [2.6 * cm, 3 * cm, 7.4 * cm, 3 * cm])]
        else:
            story += [Paragraph("Monthly Breakdown", styles["Heading2"]),
                      table([["Month", "Income", "Expense", "Net"]] +
                            [[m, f"{summary['monthly_income'][m]:,.2f}", f"{e:,.2f}",
                              f"{summary['monthly_income'][m] - e:,.2f}"]
                             for m, e in summary["monthly_expense"].items()],
                            [3.5 * cm, 4 * cm, 4 * cm, 4 * cm]),
                      Spacer(1, 12)]
            try:
                trend = self.chart_monthly_trend(year)
                story.append(Image(str(trend), width=16 * cm, height=8 * cm))
            except Exception:
                pass

        goals = self.savings.list_goals()
        if goals:
            story += [Spacer(1, 12), Paragraph("Savings Goals", styles["Heading2"]),
                      table([["Goal", "Target", "Saved", "Progress"]] +
                            [[g.name, f"{g.target_amount:,.2f}", f"{g.saved_amount:,.2f}", f"{g.progress:.1f}%"]
                             for g in goals], [6 * cm, 3.5 * cm, 3.5 * cm, 3 * cm])]

        doc.build(story)
        return path
