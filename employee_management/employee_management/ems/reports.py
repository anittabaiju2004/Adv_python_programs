"""Reports module: CSV and PDF reports for employees, departments, attendance,
leave, payroll and highest salaries, plus individual PDF payslips."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .attendance import AttendanceManager
from .database import JSONDatabase
from .employees import EmployeeManager
from .leaves import LeaveManager
from .payroll import PayrollManager
from .utils import COMPANY_ADDRESS, COMPANY_NAME, EMSError, rupees_in_words, validate_month


class ReportGenerator:
    def __init__(self, db: JSONDatabase, report_dir: Path | str):
        self.db = db
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.employees = EmployeeManager(db)
        self.attendance = AttendanceManager(db)
        self.leaves = LeaveManager(db)
        self.payroll = PayrollManager(db)

    def _path(self, stem: str, ext: str, sub: str = "") -> Path:
        folder = self.report_dir / sub if sub else self.report_dir
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"

    @staticmethod
    def _write_csv(path: Path, header: list[str], rows: list[list]) -> Path:
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return path

    # ================================================================== CSV
    def employees_csv(self, status: str | None = "ACTIVE") -> Path:
        emps = self.employees.list(status=status)
        if not emps:
            raise EMSError("No employees to export.")
        return self._write_csv(self._path(f"employees_{(status or 'all').lower()}", "csv"),
                               ["Emp ID", "Name", "Gender", "DOB", "Phone", "Email", "Department", "Designation",
                                "Type", "Joining Date", "Basic Salary", "Experience (yrs)", "Status", "Exit Date"],
                               [[e.emp_id, e.name, e.gender, e.dob, e.phone, e.email, e.department, e.designation,
                                 e.employment_type, e.join_date, f"{e.basic_salary:.2f}", e.experience_years,
                                 e.status, e.exit_date or ""] for e in emps])

    def highest_salary_csv(self, top: int = 10, department: str | None = None) -> Path:
        rows = self.payroll.highest_salaries(top, department)
        if not rows:
            raise EMSError("No employees found.")
        return self._write_csv(self._path("highest_salaries", "csv"),
                               ["Rank", "Emp ID", "Name", "Department", "Designation", "Basic", "Monthly Gross",
                                "Monthly Net", "Annual CTC"],
                               [[i, r["employee"].emp_id, r["employee"].name, r["employee"].department,
                                 r["employee"].designation, f"{r['employee'].basic_salary:.2f}", f"{r['gross']:.2f}",
                                 f"{r['net']:.2f}", f"{r['annual_ctc']:.2f}"] for i, r in enumerate(rows, 1)])

    def attendance_csv(self, month: str) -> Path:
        month = validate_month(month)
        rows = []
        for e in self.employees.list(status=None):
            if e.join_date[:7] > month or (e.exit_date and e.exit_date[:7] < month):
                continue
            s = self.attendance.monthly_summary(e.emp_id, month)
            rows.append([e.emp_id, e.name, e.department, s["working_days"], s["present"], s["half_day"],
                         s["absent"], s["leave_paid"], s["leave_unpaid"], s["late"], s["unmarked"],
                         s["lop_days"], s["attendance_percent"]])
        return self._write_csv(self._path(f"attendance_{month}", "csv"),
                               ["Emp ID", "Name", "Department", "Working Days", "Present", "Half Days", "Absent",
                                "Paid Leave", "Unpaid Leave", "Late", "Unmarked", "LOP Days", "Attendance %"], rows)

    def leaves_csv(self, year: int | None = None) -> Path:
        leaves = self.leaves.list(year=year)
        names = {e.emp_id: e.name for e in self.employees.list(status=None)}
        return self._write_csv(self._path(f"leaves_{year or 'all'}", "csv"),
                               ["Leave ID", "Emp ID", "Name", "Type", "From", "To", "Days", "Reason", "Status",
                                "Applied On", "Decided By", "Remarks"],
                               [[l["leave_id"], l["emp_id"], names.get(l["emp_id"], ""), l["leave_type"], l["start"],
                                 l["end"], l["days"], l["reason"], l["status"], l["applied_on"][:10],
                                 l.get("decided_by") or "", l.get("remarks") or ""] for l in leaves])

    def payroll_csv(self, month: str) -> Path:
        slips = self.payroll.list(month)
        if not slips:
            raise EMSError(f"No payroll generated for {month}.")
        return self._write_csv(self._path(f"payroll_{month}", "csv"),
                               ["Emp ID", "Name", "Department", "Basic", "HRA", "DA", "Conveyance", "Medical",
                                "Gross", "LOP Days", "LOP Deduction", "PF", "ESI", "Prof. Tax", "Deductions",
                                "Net Pay", "Bank Account", "Status", "Paid On"],
                               [[p["emp_id"], p["name"], p["department"], p["basic"], p["hra"], p["da"],
                                 p["conveyance"], p["medical"], p["gross"], p["lop_days"], p["lop_deduction"],
                                 p["pf"], p["esi"], p["professional_tax"], p["total_deductions"], p["net"],
                                 p.get("bank_account") or "", p["status"], p.get("paid_on") or ""] for p in slips])

    # ================================================================== PDF
    def _pdf_kit(self):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        styles = getSampleStyleSheet()
        k = type("Kit", (), {})()
        k.colors, k.A4, k.landscape, k.cm = colors, A4, landscape, cm
        k.Paragraph, k.Doc, k.Spacer, k.Table, k.TableStyle = Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        k.styles = styles
        k.cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=10.5)
        k.brand = colors.HexColor("#22577a")

        def table(rows, widths, right=(), zebra=True):
            t = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            st = [("BACKGROUND", (0, 0), (-1, 0), k.brand), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                  ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b8c4ce")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
            if zebra:
                st.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4f8")]))
            st += [("ALIGN", (c, 1), (c, -1), "RIGHT") for c in right]
            t.setStyle(TableStyle(st))
            return t
        k.table = table

        def header(title: str, subtitle: str = ""):
            out = [Paragraph(COMPANY_NAME, styles["Title"]),
                   Paragraph(COMPANY_ADDRESS, ParagraphStyle("addr", parent=styles["Normal"], alignment=1,
                                                             textColor=colors.grey)),
                   Spacer(1, 8), Paragraph(title, styles["Heading2"])]
            if subtitle:
                out.append(Paragraph(subtitle, styles["Normal"]))
            return out + [Spacer(1, 8)]
        k.header = header
        return k

    def employees_pdf(self) -> Path:
        k = self._pdf_kit()
        emps = self.employees.list(sort_by="department")
        if not emps:
            raise EMSError("No active employees.")
        path = self._path("employee_directory", "pdf")
        doc = k.Doc(str(path), pagesize=k.landscape(k.A4), leftMargin=1.3 * k.cm, rightMargin=1.3 * k.cm,
                    topMargin=1.2 * k.cm, bottomMargin=1.2 * k.cm, title="Employee Directory")
        story = k.header("Employee Directory", f"{len(emps)} active employees · generated {datetime.now():%d %b %Y}")
        summary = [["Department", "Headcount", "Total Monthly Gross", "Average Gross", "Highest", "Lowest"]] + \
            [[d["department"], d["employees"], f"{d['total_gross']:,.2f}", f"{d['average_gross']:,.2f}",
              f"{d['highest']:,.2f}", f"{d['lowest']:,.2f}"] for d in self.payroll.department_salary_summary()]
        story += [k.Paragraph("Department Summary", k.styles["Heading3"]),
                  k.table(summary, [6 * k.cm, 2.4 * k.cm, 4.2 * k.cm, 3.8 * k.cm, 3.4 * k.cm, 3.4 * k.cm],
                          right=(1, 2, 3, 4, 5)), k.Spacer(1, 12),
                  k.Paragraph("Employees", k.styles["Heading3"])]
        rows = [["Emp ID", "Name", "Department", "Designation", "Phone", "Email", "Joined", "Basic"]] + \
            [[e.emp_id, k.Paragraph(escape(e.name), k.cell), k.Paragraph(escape(e.department), k.cell),
              k.Paragraph(escape(e.designation), k.cell), e.phone, k.Paragraph(escape(e.email), k.cell),
              e.join_date, f"{e.basic_salary:,.2f}"] for e in emps]
        story.append(k.table(rows, [2 * k.cm, 4 * k.cm, 3.8 * k.cm, 4.2 * k.cm, 2.6 * k.cm, 5.6 * k.cm,
                                    2.3 * k.cm, 2.5 * k.cm], right=(7,)))
        doc.build(story)
        return path

    def payroll_register_pdf(self, month: str) -> Path:
        k = self._pdf_kit()
        slips = self.payroll.list(month)
        if not slips:
            raise EMSError(f"No payroll generated for {month}.")
        t = self.payroll.register_totals(month)
        path = self._path(f"payroll_register_{month}", "pdf")
        doc = k.Doc(str(path), pagesize=k.landscape(k.A4), leftMargin=1.2 * k.cm, rightMargin=1.2 * k.cm,
                    topMargin=1.2 * k.cm, bottomMargin=1.2 * k.cm, title=f"Payroll Register {month}")
        label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        story = k.header(f"Payroll Register — {label}",
                         f"{t['payslips']} payslips · {t['paid']} paid · total net pay {t['net']:,.2f}")
        rows = [["Emp ID", "Name", "Department", "Gross", "LOP Days", "LOP Amt", "PF", "ESI", "PT", "Net Pay", "Status"]]
        for p in slips:
            rows.append([p["emp_id"], k.Paragraph(escape(p["name"]), k.cell), k.Paragraph(escape(p["department"]), k.cell),
                         f"{p['gross_full']:,.2f}", f"{p['lop_days']:g}", f"{p['lop_deduction']:,.2f}",
                         f"{p['pf']:,.2f}", f"{p['esi']:,.2f}", f"{p['professional_tax']:,.0f}",
                         f"{p['net']:,.2f}", p["status"]])
        rows.append(["", "TOTAL", "", f"{sum(p['gross_full'] for p in slips):,.2f}", "", f"{t['lop_deduction']:,.2f}",
                     f"{t['pf']:,.2f}", f"{t['esi']:,.2f}", f"{t['professional_tax']:,.0f}", f"{t['net']:,.2f}", ""])
        tbl = k.table(rows, [2 * k.cm, 4.2 * k.cm, 3.8 * k.cm, 2.7 * k.cm, 1.8 * k.cm, 2.4 * k.cm, 2.2 * k.cm,
                             1.9 * k.cm, 1.5 * k.cm, 2.8 * k.cm, 2.2 * k.cm], right=(3, 4, 5, 6, 7, 8, 9))
        tbl.setStyle(k.TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                                   ("BACKGROUND", (0, -1), (-1, -1), k.colors.HexColor("#d9e6ef"))]))
        story.append(tbl)
        doc.build(story)
        return path

    def payslip_pdf(self, emp_id: str, month: str) -> Path:
        k = self._pdf_kit()
        p = self.payroll.get(emp_id, month)
        emp = self.employees.get(emp_id)
        path = self._path(f"payslip_{p['emp_id']}_{month}", "pdf", sub="payslips")
        doc = k.Doc(str(path), pagesize=k.A4, leftMargin=1.8 * k.cm, rightMargin=1.8 * k.cm,
                    topMargin=1.5 * k.cm, bottomMargin=1.5 * k.cm, title=f"Payslip {p['emp_id']} {month}")
        label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        story = k.header(f"Payslip for {label}")
        info = [["Employee ID", p["emp_id"], "Name", p["name"]],
                ["Department", p["department"], "Designation", p["designation"]],
                ["Date of Joining", emp.join_date, "PAN", p.get("pan") or "-"],
                ["Bank Account", p.get("bank_account") or "-", "Status",
                 f"{p['status']}" + (f" on {p['paid_on']}" if p.get("paid_on") else "")],
                ["Working Days", str(p["working_days"]), "LOP Days", f"{p['lop_days']:g}"],
                ["Days Paid", f"{p['working_days'] - p['lop_days']:g}", "Paid Leave Taken", str(p["leave_paid"])]]
        it = k.Table(info, colWidths=[3.4 * k.cm, 5 * k.cm, 3.4 * k.cm, 5.6 * k.cm], hAlign="LEFT")
        it.setStyle(k.TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                                  ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                                  ("BOX", (0, 0), (-1, -1), 0.5, k.colors.grey),
                                  ("INNERGRID", (0, 0), (-1, -1), 0.25, k.colors.HexColor("#d0d7de"))]))
        earnings = [("Basic", "basic"), ("House Rent Allowance", "hra"), ("Dearness Allowance", "da"),
                    ("Conveyance", "conveyance"), ("Medical Allowance", "medical")]
        deductions = [("Provident Fund", p["pf"]), ("ESI", p["esi"]), ("Professional Tax", p["professional_tax"])]
        rows = [["Earnings", "Full Month", "Earned", "Deductions", "Amount"]]
        for i in range(max(len(earnings), len(deductions))):
            e = earnings[i] if i < len(earnings) else None
            d = deductions[i] if i < len(deductions) else None
            rows.append([e[0] if e else "", f"{p[e[1] + '_full']:,.2f}" if e else "", f"{p[e[1]]:,.2f}" if e else "",
                         d[0] if d else "", f"{d[1]:,.2f}" if d else ""])
        rows.append(["Gross Earnings", f"{p['gross_full']:,.2f}", f"{p['gross']:,.2f}", "Total Deductions",
                     f"{p['total_deductions']:,.2f}"])
        tbl = k.table(rows, [4.6 * k.cm, 2.9 * k.cm, 2.9 * k.cm, 4.2 * k.cm, 2.8 * k.cm], right=(1, 2, 4), zebra=False)
        tbl.setStyle(k.TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                                   ("BACKGROUND", (0, -1), (-1, -1), k.colors.HexColor("#eef4f8"))]))
        net = k.Table([["NET PAY", f"{p['net']:,.2f}"], [rupees_in_words(p["net"]), ""]],
                      colWidths=[13.6 * k.cm, 3.8 * k.cm], hAlign="LEFT")
        net.setStyle(k.TableStyle([("BACKGROUND", (0, 0), (-1, 0), k.brand), ("TEXTCOLOR", (0, 0), (-1, 0), k.colors.white),
                                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 11),
                                   ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("SPAN", (0, 1), (1, 1)),
                                   ("FONTSIZE", (0, 1), (-1, 1), 8.5), ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Oblique"),
                                   ("BOX", (0, 0), (-1, -1), 0.5, k.brand)]))
        story += [it, k.Spacer(1, 14), tbl, k.Spacer(1, 10), net]
        if p["lop_deduction"]:
            story += [k.Spacer(1, 8), k.Paragraph(
                f"Loss of pay: {p['lop_days']:g} day(s) of {p['working_days']} working days "
                f"(absent {p['absent']}, half days {p['half_day']}, unpaid leave {p['leave_unpaid']}"
                + (f", not yet employed / exited {p['not_employed_days']}" if p["not_employed_days"] else "")
                + f") — {p['lop_deduction']:,.2f} deducted.", k.cell)]
        story += [k.Spacer(1, 24), k.Paragraph("This is a computer-generated payslip and does not require a signature.",
                                              k.styles["Italic"])]
        doc.build(story)
        return path
