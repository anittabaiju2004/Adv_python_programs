"""Payroll module: salary calculator, monthly payroll generation with loss of
pay (LOP) from attendance, payment status, and salary reports."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .attendance import AttendanceManager
from .database import JSONDatabase
from .employees import Employee, EmployeeManager
from .utils import (CONVEYANCE, DA_PERCENT, DATE_FMT, ESI_LIMIT, ESI_PERCENT, HRA_PERCENT, MAX_BASIC,
                    MEDICAL_ALLOWANCE, MIN_BASIC, PF_PERCENT, PF_WAGE_CEILING, PROFESSIONAL_TAX, EMSError,
                    NotFoundError, ValidationError, month_bounds, new_id, now_str, parse_date,
                    validate_amount, validate_month, working_days_between, working_days_in_month)


def professional_tax(gross: float) -> float:
    for lo, hi, tax in PROFESSIONAL_TAX:
        if lo <= gross <= hi:
            return tax
    return 0.0


def calculate_salary(basic, working_days: int = 0, lop_days: float = 0) -> dict:
    """Salary calculator. With working_days and lop_days, loss-of-pay is deducted
    proportionally from every earning before statutory deductions."""
    basic = validate_amount(basic, "Basic salary", MIN_BASIC, MAX_BASIC)
    if lop_days < 0 or (working_days and lop_days > working_days):
        raise ValidationError("LOP days must be between 0 and the number of working days.")
    full = {"basic": basic, "hra": round(basic * HRA_PERCENT / 100, 2), "da": round(basic * DA_PERCENT / 100, 2),
            "conveyance": CONVEYANCE, "medical": MEDICAL_ALLOWANCE}
    gross_full = round(sum(full.values()), 2)
    factor = 1 - (lop_days / working_days) if working_days else 1.0
    earned = {k: round(v * factor, 2) for k, v in full.items()}
    gross = round(sum(earned.values()), 2)
    pf = round(min(earned["basic"], PF_WAGE_CEILING) * PF_PERCENT / 100, 2)
    esi = round(gross * ESI_PERCENT / 100, 2) if gross_full <= ESI_LIMIT else 0.0
    pt = professional_tax(gross)
    deductions = round(pf + esi + pt, 2)
    employer_pf = round(min(basic, PF_WAGE_CEILING) * PF_PERCENT / 100, 2)
    return {**{f"{k}_full": v for k, v in full.items()}, **earned,
            "gross_full": gross_full, "lop_days": lop_days, "working_days": working_days,
            "lop_deduction": round(gross_full - gross, 2), "gross": gross,
            "pf": pf, "esi": esi, "professional_tax": pt, "total_deductions": deductions,
            "net": round(gross - deductions, 2),
            "annual_ctc": round((gross_full + employer_pf) * 12, 2)}


class PayrollManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.employees = EmployeeManager(db)
        self.attendance = AttendanceManager(db)

    # ----------------------------------------------------------- generation
    def _eligible(self, month: str) -> list[Employee]:
        first, last = month_bounds(month)
        out = []
        for e in self.employees.list(status=None):
            if e.join_date > last.strftime(DATE_FMT):
                continue
            if e.exit_date and e.exit_date < first.strftime(DATE_FMT):
                continue
            out.append(e)
        return out

    def generate(self, month: str, emp_ids: list[str] | None = None, unmarked_as_absent: bool = False) -> dict:
        """Generate (or regenerate, if not yet paid) payslips for a month.

        LOP days = absences + half of half-days + unpaid leave
                   + working days in the month before joining / after exit
                   (+ unmarked days if `unmarked_as_absent`).
        """
        month = validate_month(month)
        if month > date.today().strftime("%Y-%m"):
            raise ValidationError("Payroll cannot be generated for a future month.")
        first, last = month_bounds(month)
        total_wd = len(working_days_in_month(month))
        wanted = {i.upper() for i in emp_ids} if emp_ids else None
        result = {"generated": 0, "skipped_paid": 0, "total_net": 0.0, "month": month}
        for emp in self._eligible(month):
            if wanted and emp.emp_id not in wanted:
                continue
            existing = self.db.find_one("payroll", emp_id=emp.emp_id, month=month)
            if existing and existing["status"] == "PAID":
                result["skipped_paid"] += 1
                continue
            s = self.attendance.monthly_summary(emp.emp_id, month, unmarked_as_absent)
            start, end = parse_date(emp.join_date), parse_date(emp.exit_date) if emp.exit_date else last
            not_employed = len([d for d in working_days_in_month(month) if d < start or d > end])
            lop = min(total_wd, s["lop_days"] + not_employed)
            calc = calculate_salary(emp.basic_salary, total_wd, lop)
            slip = {"payslip_id": existing["payslip_id"] if existing else new_id("PS"), "emp_id": emp.emp_id,
                    "name": emp.name, "department": emp.department, "designation": emp.designation,
                    "pan": emp.pan, "bank_account": emp.bank_account, "month": month, **calc,
                    "present": s["present"], "half_day": s["half_day"], "absent": s["absent"],
                    "leave_paid": s["leave_paid"], "leave_unpaid": s["leave_unpaid"],
                    "not_employed_days": not_employed, "status": "GENERATED",
                    "generated_at": now_str(), "paid_on": None}
            if existing:
                self.db.update("payroll", "payslip_id", existing["payslip_id"], slip)
            else:
                self.db.insert("payroll", slip)
            result["generated"] += 1
            result["total_net"] = round(result["total_net"] + calc["net"], 2)
        return result

    # --------------------------------------------------------------- status
    def list(self, month: str) -> list[dict]:
        month = validate_month(month)
        return sorted(self.db.find("payroll", month=month), key=lambda p: p["emp_id"])

    def get(self, emp_id: str, month: str) -> dict:
        p = self.db.find_one("payroll", emp_id=emp_id.upper(), month=validate_month(month))
        if not p:
            raise NotFoundError(f"No payslip for {emp_id.upper()} in {month}. Generate payroll first.")
        return p

    def payslips_for(self, emp_id: str) -> list[dict]:
        return sorted(self.db.find("payroll", emp_id=emp_id.upper()), key=lambda p: p["month"], reverse=True)

    def mark_paid(self, month: str, emp_ids: list[str] | None = None, paid_on: str | None = None) -> int:
        slips = [p for p in self.list(month) if p["status"] == "GENERATED"
                 and (not emp_ids or p["emp_id"] in {i.upper() for i in emp_ids})]
        if not slips:
            raise EMSError("No unpaid payslips found for that selection.")
        d = paid_on or date.today().strftime(DATE_FMT)
        for p in slips:
            self.db.update("payroll", "payslip_id", p["payslip_id"], {"status": "PAID", "paid_on": d})
        return len(slips)

    def register_totals(self, month: str) -> dict:
        slips = self.list(month)
        keys = ("gross", "lop_deduction", "pf", "esi", "professional_tax", "total_deductions", "net")
        totals = {k: round(sum(p[k] for p in slips), 2) for k in keys}
        by_dept = defaultdict(lambda: {"employees": 0, "net": 0.0})
        for p in slips:
            by_dept[p["department"]]["employees"] += 1
            by_dept[p["department"]]["net"] = round(by_dept[p["department"]]["net"] + p["net"], 2)
        return {"month": month, "payslips": len(slips), "paid": sum(p["status"] == "PAID" for p in slips),
                **totals, "by_department": dict(sorted(by_dept.items()))}

    # -------------------------------------------------------------- reports
    def highest_salaries(self, top: int = 10, department: str | None = None) -> list[dict]:
        """Active employees ranked by monthly gross salary (from current basic)."""
        rows = []
        for e in self.employees.list(department=department):
            c = calculate_salary(e.basic_salary)
            rows.append({"employee": e, "gross": c["gross_full"], "net": c["net"], "annual_ctc": c["annual_ctc"]})
        rows.sort(key=lambda r: (-r["gross"], r["employee"].emp_id))
        return rows[:top]

    def department_salary_summary(self) -> list[dict]:
        groups = defaultdict(list)
        for e in self.employees.list():
            groups[e.department].append(calculate_salary(e.basic_salary)["gross_full"])
        return [{"department": d, "employees": len(v), "total_gross": round(sum(v), 2),
                 "average_gross": round(sum(v) / len(v), 2), "highest": max(v), "lowest": min(v)}
                for d, v in sorted(groups.items())]
