"""Attendance Management module: admin marking (single / whole team), employee
check-in and check-out with late and half-day detection, daily register and
monthly summaries."""
from __future__ import annotations

from datetime import date, datetime

from .database import JSONDatabase
from .employees import EmployeeManager
from .utils import (ATTENDANCE_STATUSES, DATE_FMT, HALF_DAY_HOURS, HOLIDAYS, OFFICE_START, EMSError,
                    ValidationError, is_working_day, month_bounds, new_id, now_str, parse_date,
                    validate_choice, validate_month, working_days_between)

MARKABLE = [s for s in ATTENDANCE_STATUSES if s != "LEAVE"]   # LEAVE comes only from approved leave


class AttendanceManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.employees = EmployeeManager(db)

    # ------------------------------------------------------------- helpers
    def _record(self, emp_id: str, day: str) -> dict | None:
        return self.db.find_one("attendance", emp_id=emp_id, date=day)

    def _check_day(self, emp_id: str, day) -> tuple[str, str]:
        emp = self.employees.get(emp_id)
        d = parse_date(day)
        ds = d.strftime(DATE_FMT)
        if not emp.is_active and (not emp.exit_date or ds > emp.exit_date):
            raise EMSError(f"{emp.emp_id} is not active on {ds}.")
        if ds < emp.join_date:
            raise ValidationError(f"{emp.emp_id} joined on {emp.join_date}.")
        if d > date.today():
            raise ValidationError("Attendance cannot be marked for a future date.")
        if not is_working_day(d):
            raise ValidationError(f"{ds} is a {HOLIDAYS.get(ds, 'weekly off')} — not a working day.")
        return emp.emp_id, ds

    def _upsert(self, emp_id: str, day: str, changes: dict) -> dict:
        existing = self._record(emp_id, day)
        if existing:
            return self.db.update("attendance", "id", existing["id"], {**changes, "updated_at": now_str()})
        rec = {"id": new_id("AT"), "emp_id": emp_id, "date": day, "status": "PRESENT", "check_in": None,
               "check_out": None, "hours": None, "late": False, "leave_id": None, "leave_type": None,
               "marked_by": "admin", "updated_at": now_str(), **changes}
        return self.db.insert("attendance", rec)

    # ------------------------------------------------------------- marking
    def mark(self, emp_id: str, day, status: str, by: str = "admin") -> dict:
        emp_id, ds = self._check_day(emp_id, day)
        status = validate_choice(status, MARKABLE, "status")
        existing = self._record(emp_id, ds)
        if existing and existing["status"] == "LEAVE":
            raise EMSError(f"{emp_id} is on approved leave on {ds}. Cancel the leave to change attendance.")
        return self._upsert(emp_id, ds, {"status": status, "marked_by": by})

    def mark_all(self, day, status: str = "PRESENT", exceptions: dict | None = None, by: str = "admin") -> dict:
        """Mark every active employee for a day. `exceptions` maps emp_id -> status.
        Employees on approved leave, not yet joined, or already checked in are left alone."""
        status = validate_choice(status, MARKABLE, "status")
        exceptions = {k.upper(): validate_choice(v, MARKABLE, "status") for k, v in (exceptions or {}).items()}
        counts = {"marked": 0, "on_leave": 0, "skipped": 0}
        for emp in self.employees.list():
            try:
                existing = self._record(emp.emp_id, parse_date(day).strftime(DATE_FMT))
                if existing and existing["status"] == "LEAVE":
                    counts["on_leave"] += 1
                    continue
                if existing and existing.get("check_in") and emp.emp_id not in exceptions:
                    counts["skipped"] += 1          # employee already checked in themselves
                    continue
                self.mark(emp.emp_id, day, exceptions.get(emp.emp_id, status), by)
                counts["marked"] += 1
            except ValidationError as exc:
                if "working day" in str(exc) or "future" in str(exc):
                    raise
                counts["skipped"] += 1              # e.g. joined after this date
        return counts

    def check_in(self, emp_id: str, at: datetime | None = None) -> dict:
        at = at or datetime.now()
        emp_id, ds = self._check_day(emp_id, at.date())
        existing = self._record(emp_id, ds)
        if existing and existing["status"] == "LEAVE":
            raise EMSError("You are on approved leave today.")
        if existing and existing.get("check_in"):
            raise EMSError(f"Already checked in at {existing['check_in']}.")
        t = at.strftime("%H:%M:%S")
        return self._upsert(emp_id, ds, {"status": "PRESENT", "check_in": t, "late": t[:5] > OFFICE_START,
                                         "marked_by": "self"})

    def check_out(self, emp_id: str, at: datetime | None = None) -> dict:
        at = at or datetime.now()
        emp_id, ds = self._check_day(emp_id, at.date())
        rec = self._record(emp_id, ds)
        if not rec or not rec.get("check_in"):
            raise EMSError("You have not checked in today.")
        if rec.get("check_out"):
            raise EMSError(f"Already checked out at {rec['check_out']}.")
        start = datetime.strptime(f"{ds} {rec['check_in']}", f"{DATE_FMT} %H:%M:%S")
        hours = round((at - start).total_seconds() / 3600, 2)
        if hours < 0:
            raise ValidationError("Check-out time is before check-in time.")
        status = "HALF_DAY" if hours < HALF_DAY_HOURS else "PRESENT"
        return self._upsert(emp_id, ds, {"check_out": at.strftime("%H:%M:%S"), "hours": hours, "status": status})

    # -------------------------------------------------- used by leave module
    def apply_leave(self, emp_id: str, days: list[str], leave_id: str, leave_type: str) -> None:
        for ds in days:
            self._upsert(emp_id, ds, {"status": "LEAVE", "leave_id": leave_id, "leave_type": leave_type,
                                      "check_in": None, "check_out": None, "hours": None, "late": False,
                                      "marked_by": "leave"})

    def remove_leave(self, leave_id: str) -> int:
        return self.db.delete_where("attendance", leave_id=leave_id)

    # ------------------------------------------------------------- queries
    def records(self, emp_id: str, month: str) -> list[dict]:
        month = validate_month(month)
        return sorted((r for r in self.db.find("attendance", emp_id=emp_id.upper()) if r["date"].startswith(month)),
                      key=lambda r: r["date"])

    def register(self, day) -> list[dict]:
        """Daily register: every active employee with their record (or None)."""
        ds = parse_date(day).strftime(DATE_FMT)
        recs = {r["emp_id"]: r for r in self.db.find("attendance", date=ds)}
        return [{"employee": e, "record": recs.get(e.emp_id)} for e in self.employees.list()
                if e.join_date <= ds]

    def monthly_summary(self, emp_id: str, month: str, unmarked_as_absent: bool = False) -> dict:
        """Counts for one employee and month. Only working days from the joining
        date (and up to today / exit date) are considered."""
        emp = self.employees.get(emp_id)
        month = validate_month(month)
        first, last = month_bounds(month)
        start = max(first, parse_date(emp.join_date))
        end = min(last, date.today(), parse_date(emp.exit_date) if emp.exit_date else last)
        days = [d.strftime(DATE_FMT) for d in working_days_between(start, end)] if start <= end else []
        recs = {r["date"]: r for r in self.records(emp.emp_id, month)}
        s = {"month": month, "working_days": len(days), "present": 0, "half_day": 0, "absent": 0,
             "leave_paid": 0, "leave_unpaid": 0, "late": 0, "unmarked": 0}
        for ds in days:
            r = recs.get(ds)
            if not r:
                s["unmarked"] += 1
            elif r["status"] == "PRESENT":
                s["present"] += 1
            elif r["status"] == "HALF_DAY":
                s["half_day"] += 1
            elif r["status"] == "ABSENT":
                s["absent"] += 1
            elif r["status"] == "LEAVE":
                s["leave_unpaid" if r.get("leave_type") == "Loss of Pay" else "leave_paid"] += 1
            if r and r.get("late"):
                s["late"] += 1
        s["lop_days"] = s["absent"] + 0.5 * s["half_day"] + s["leave_unpaid"] + \
            (s["unmarked"] if unmarked_as_absent else 0)
        attended = s["present"] + 0.5 * s["half_day"]
        s["attendance_percent"] = round(attended / (len(days) - s["leave_paid"] - s["leave_unpaid"]) * 100, 1) \
            if len(days) - s["leave_paid"] - s["leave_unpaid"] > 0 else 0.0
        return s
