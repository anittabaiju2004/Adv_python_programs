"""Attendance Management: daily class attendance (all present except the
absentees you list), corrections, student and class summaries, shortage
list and monthly register."""
from __future__ import annotations

import calendar
from datetime import date

from .auth import log_activity
from .database import JSONDatabase
from .students import ClassManager, StudentManager
from .utils import (ATTENDANCE_STATUSES, HOLIDAYS, MIN_ATTENDANCE, NotFoundError, SMSError, ValidationError,
                    is_working_day, now_str, parse_date, validate_choice, working_days)


class AttendanceManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.classes = ClassManager(db, actor)
        self.students = StudentManager(db, actor)

    def _day(self, class_code: str, day) -> dict | None:
        return self.db.find_one("attendance", class_code=class_code, date=parse_date(day).isoformat())

    def _check_day(self, day) -> date:
        d = parse_date(day)
        if d > date.today():
            raise ValidationError("Attendance cannot be marked for a future date.")
        if not is_working_day(d):
            raise ValidationError(f"{d.isoformat()} is a {HOLIDAYS.get(d.isoformat(), 'Sunday')} — not a working day.")
        return d

    # ------------------------------------------------------------- marking
    def mark_class(self, class_code: str, day, absent: list[str] | None = None, leave: list[str] | None = None) -> dict:
        """Mark the whole class: everyone present except `absent` / `leave` roll numbers.
        Students admitted after the date are not included. Re-marking a day replaces it."""
        cls = self.classes.get(class_code)
        d = self._check_day(day)
        roster = [s for s in self.students.list(cls["code"]) if s["admission_date"] <= d.isoformat()]
        if not roster:
            raise SMSError(f"No active students in {cls['code']} on {d.isoformat()}.")
        rolls = {s["roll_no"] for s in roster}
        absent = {r.strip().upper() for r in (absent or []) if r.strip()}
        leave = {r.strip().upper() for r in (leave or []) if r.strip()}
        unknown = (absent | leave) - rolls
        if unknown:
            raise ValidationError(f"Not in {cls['code']} on that date: {', '.join(sorted(unknown))}.")
        if absent & leave:
            raise ValidationError(f"Marked both absent and on leave: {', '.join(sorted(absent & leave))}.")
        records = {r: ("A" if r in absent else "L" if r in leave else "P") for r in sorted(rolls)}
        existing = self._day(cls["code"], d)
        rec = {"id": f"{cls['code']}:{d.isoformat()}", "class_code": cls["code"], "date": d.isoformat(),
               "records": records, "marked_by": self.actor, "updated_at": now_str()}
        if existing:
            self.db.update("attendance", "id", existing["id"], rec)
        else:
            self.db.insert("attendance", rec)
        log_activity(self.db, self.actor, "ATTENDANCE_MARKED",
                     f"{cls['code']} {d.isoformat()} P{len(rolls) - len(absent) - len(leave)} A{len(absent)} L{len(leave)}")
        return rec

    def correct(self, roll_no: str, day, status: str) -> dict:
        s = self.students.get(roll_no)
        status = validate_choice(status, ATTENDANCE_STATUSES, "status (P/A/L)")
        rec = self._day(s["class_code"], day)
        if not rec:
            raise NotFoundError(f"Attendance for {s['class_code']} on {parse_date(day).isoformat()} has not been taken.")
        if s["roll_no"] not in rec["records"]:
            raise SMSError(f"{s['roll_no']} was not on the roll that day.")
        rec["records"][s["roll_no"]] = status
        log_activity(self.db, self.actor, "ATTENDANCE_CORRECTED", f"{s['roll_no']} {rec['date']} -> {status}")
        return self.db.update("attendance", "id", rec["id"], {"records": rec["records"], "updated_at": now_str()})

    def get_day(self, class_code: str, day) -> dict | None:
        return self._day(self.classes.get(class_code)["code"], day)

    # ------------------------------------------------------------- queries
    def _days(self, class_code: str, start=None, end=None) -> list[dict]:
        days = self.db.find("attendance", class_code=class_code)
        if start:
            days = [d for d in days if d["date"] >= parse_date(start).isoformat()]
        if end:
            days = [d for d in days if d["date"] <= parse_date(end).isoformat()]
        return sorted(days, key=lambda d: d["date"])

    def student_summary(self, roll_no: str, start=None, end=None) -> dict:
        s = self.students.get(roll_no)
        days = [d for d in self._days(s["class_code"], start, end) if s["roll_no"] in d["records"]]
        counts = {k: sum(1 for d in days if d["records"][s["roll_no"]] == k) for k in ATTENDANCE_STATUSES}
        total = len(days)
        pct = round(counts["P"] / total * 100, 1) if total else 100.0
        return {"roll_no": s["roll_no"], "name": s["name"], "days": total, "present": counts["P"],
                "absent": counts["A"], "leave": counts["L"], "percent": pct, "shortage": total > 0 and pct < MIN_ATTENDANCE,
                "absent_dates": [d["date"] for d in days if d["records"][s["roll_no"]] != "P"]}

    def class_summary(self, class_code: str, start=None, end=None) -> dict:
        cls = self.classes.get(class_code)
        rows = [self.student_summary(s["roll_no"], start, end) for s in self.students.list(cls["code"])]
        days = self._days(cls["code"], start, end)
        return {"class_code": cls["code"], "days_marked": len(days), "students": rows,
                "average": round(sum(r["percent"] for r in rows) / len(rows), 1) if rows else 0.0,
                "shortage": [r for r in rows if r["shortage"]]}

    def unmarked_days(self, class_code: str, start, end) -> list[str]:
        cls = self.classes.get(class_code)
        done = {d["date"] for d in self._days(cls["code"])}
        end = min(parse_date(end), date.today())
        return [d.isoformat() for d in working_days(parse_date(start), end) if d.isoformat() not in done]

    def monthly_register(self, class_code: str, month: str) -> dict:
        """Matrix of P/A/L per student per working day in the month."""
        cls = self.classes.get(class_code)
        try:
            y, m = map(int, month.split("-"))
            first, last = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
        except ValueError:
            raise ValidationError("Month must be in YYYY-MM format.")
        days = {d["date"]: d["records"] for d in self._days(cls["code"], first, last)}
        dates = [d.isoformat() for d in working_days(first, last)]
        rows = []
        for s in self.students.list(cls["code"]):
            marks = []
            for d in dates:
                if d in days:
                    marks.append(days[d].get(s["roll_no"], "-"))    # "-" = not on the roll yet
                elif d > date.today().isoformat():
                    marks.append(" ")                              # future
                else:
                    marks.append("?")                              # attendance not taken
            p = marks.count("P")
            taken = sum(1 for x in marks if x in ATTENDANCE_STATUSES)
            rows.append({"roll_no": s["roll_no"], "name": s["name"], "marks": marks, "present": p, "taken": taken,
                         "percent": round(p / taken * 100, 1) if taken else None})
        return {"class_code": cls["code"], "month": month, "dates": dates, "rows": rows}
