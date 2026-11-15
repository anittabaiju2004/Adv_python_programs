"""Leave Management module: leave balances, applications, approval / rejection
and cancellation. Approved leave is written into attendance automatically."""
from __future__ import annotations

from datetime import date

from .attendance import AttendanceManager
from .database import JSONDatabase
from .employees import EmployeeManager
from .utils import (DATE_FMT, LEAVE_TYPES, EMSError, NotFoundError, PermissionDenied, ValidationError,
                    new_id, now_str, parse_date, validate_choice, validate_text, working_days_between)

MAX_ADVANCE_DAYS = 180


class LeaveManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.employees = EmployeeManager(db)
        self.attendance = AttendanceManager(db)

    # ------------------------------------------------------------- balance
    def entitlement(self, emp_id: str, year: int) -> dict[str, float | None]:
        """Yearly quota per leave type, prorated by months worked if the employee
        joined during that year (rounded down to the nearest half day)."""
        emp = self.employees.get(emp_id)
        join = parse_date(emp.join_date)
        months = 12 if join.year < year else (12 - join.month + 1 if join.year == year else 0)
        out = {}
        for t, quota in LEAVE_TYPES.items():
            out[t] = None if quota is None else int(quota * months / 12 * 2) / 2
        return out

    def balance(self, emp_id: str, year: int | None = None) -> dict[str, dict]:
        year = year or date.today().year
        ent = self.entitlement(emp_id, year)
        leaves = [l for l in self.list(emp_id) if l["start"][:4] == str(year)]
        out = {}
        for t, quota in ent.items():
            used = sum(l["days"] for l in leaves if l["leave_type"] == t and l["status"] == "APPROVED")
            pending = sum(l["days"] for l in leaves if l["leave_type"] == t and l["status"] == "PENDING")
            out[t] = {"entitled": quota, "used": used, "pending": pending,
                      "available": None if quota is None else quota - used - pending}
        return out

    # --------------------------------------------------------------- apply
    def apply(self, emp_id: str, leave_type: str, start: str, end: str, reason: str) -> dict:
        emp = self.employees.get(emp_id)
        if not emp.is_active:
            raise EMSError("Exited employees cannot apply for leave.")
        leave_type = validate_choice(leave_type, LEAVE_TYPES, "leave type")
        s, e = parse_date(start, "Start date"), parse_date(end, "End date")
        if e < s:
            raise ValidationError("End date is before start date.")
        if s.year != e.year:
            raise ValidationError("A leave cannot span two calendar years; apply separately for each year.")
        if s.strftime(DATE_FMT) < emp.join_date:
            raise ValidationError("Leave cannot start before the joining date.")
        if (e - date.today()).days > MAX_ADVANCE_DAYS:
            raise ValidationError(f"Leave can be applied at most {MAX_ADVANCE_DAYS} days in advance.")
        if (date.today() - s).days > 30:
            raise ValidationError("Leave older than 30 days cannot be applied for.")
        days = [d.strftime(DATE_FMT) for d in working_days_between(s, e)]
        if not days:
            raise ValidationError("The selected dates contain no working days.")
        reason = validate_text(reason, "Reason", 200, required=True)
        for l in self.list(emp.emp_id):
            if l["status"] in ("PENDING", "APPROVED") and not (e.strftime(DATE_FMT) < l["start"] or
                                                                 s.strftime(DATE_FMT) > l["end"]):
                raise ValidationError(f"Overlaps with leave {l['leave_id']} ({l['start']} to {l['end']}, {l['status']}).")
        worked = [r["date"] for r in self.db.find("attendance", emp_id=emp.emp_id)
                  if r["date"] in days and r["status"] in ("PRESENT", "HALF_DAY")]
        if worked:
            raise ValidationError(f"Attendance already shows you working on {', '.join(worked)}.")
        bal = self.balance(emp.emp_id, s.year)[leave_type]
        if bal["available"] is not None and len(days) > bal["available"]:
            raise ValidationError(f"Insufficient {leave_type} leave: {len(days)} day(s) requested, "
                                  f"{bal['available']} available. Consider Loss of Pay leave.")
        leave = {"leave_id": new_id("LV"), "emp_id": emp.emp_id, "leave_type": leave_type,
                 "start": s.strftime(DATE_FMT), "end": e.strftime(DATE_FMT), "days": len(days),
                 "dates": days, "reason": reason, "status": "PENDING", "applied_on": now_str(),
                 "decided_by": None, "decided_on": None, "remarks": None}
        self.db.insert("leaves", leave)
        return leave

    # ------------------------------------------------------------- decide
    def get(self, leave_id: str) -> dict:
        l = self.db.find_one("leaves", leave_id=str(leave_id or "").strip().upper())
        if not l:
            raise NotFoundError(f"Leave '{leave_id}' not found.")
        return l

    def approve(self, leave_id: str, by: str = "admin", remarks: str = "") -> dict:
        l = self.get(leave_id)
        if l["status"] != "PENDING":
            raise EMSError(f"Leave is {l['status']}, not pending.")
        bal = self.balance(l["emp_id"], int(l["start"][:4]))[l["leave_type"]]
        if bal["available"] is not None and bal["available"] < 0:   # pending already counted
            raise EMSError("Approving this would exceed the employee's leave balance.")
        self.attendance.apply_leave(l["emp_id"], l["dates"], l["leave_id"], l["leave_type"])
        return self.db.update("leaves", "leave_id", l["leave_id"],
                              {"status": "APPROVED", "decided_by": by, "decided_on": now_str(),
                               "remarks": validate_text(remarks, "Remarks", 120) or None})

    def reject(self, leave_id: str, by: str = "admin", remarks: str = "") -> dict:
        l = self.get(leave_id)
        if l["status"] != "PENDING":
            raise EMSError(f"Leave is {l['status']}, not pending.")
        return self.db.update("leaves", "leave_id", l["leave_id"],
                              {"status": "REJECTED", "decided_by": by, "decided_on": now_str(),
                               "remarks": validate_text(remarks, "Remarks", 120) or "Not approved"})

    def cancel(self, leave_id: str, by_emp: str | None = None) -> dict:
        """Employees can cancel their own pending leave, or approved leave that
        has not started. Admin (by_emp=None) can cancel any pending/approved leave."""
        l = self.get(leave_id)
        if by_emp and l["emp_id"] != by_emp.upper():
            raise PermissionDenied("You can only cancel your own leave.")
        if l["status"] not in ("PENDING", "APPROVED"):
            raise EMSError(f"Leave is already {l['status']}.")
        if by_emp and l["status"] == "APPROVED" and l["start"] <= date.today().strftime(DATE_FMT):
            raise PermissionDenied("Approved leave that has started can only be cancelled by the admin.")
        if l["status"] == "APPROVED":
            self.attendance.remove_leave(l["leave_id"])
        return self.db.update("leaves", "leave_id", l["leave_id"],
                              {"status": "CANCELLED", "decided_on": now_str(),
                               "decided_by": by_emp or "admin"})

    # ------------------------------------------------------------- queries
    def list(self, emp_id: str | None = None, status: str | None = None, year: int | None = None) -> list[dict]:
        leaves = self.db.find("leaves", **({"emp_id": emp_id.upper()} if emp_id else {}))
        if status:
            leaves = [l for l in leaves if l["status"] == status.upper()]
        if year:
            leaves = [l for l in leaves if l["start"].startswith(str(year))]
        return sorted(leaves, key=lambda l: l["start"], reverse=True)

    def pending(self) -> list[dict]:
        return sorted(self.list(status="PENDING"), key=lambda l: l["applied_on"])

    def on_leave(self, day=None) -> list[dict]:
        ds = (parse_date(day) if day else date.today()).strftime(DATE_FMT)
        return [l for l in self.list(status="APPROVED") if ds in l["dates"]]
