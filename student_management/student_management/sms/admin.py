"""Admin Panel: dashboard statistics and the activity log."""
from __future__ import annotations

from datetime import date, timedelta

from .attendance import AttendanceManager
from .database import JSONDatabase
from .marks import MarksManager
from .results import ResultProcessor
from .students import ClassManager, StudentManager
from .utils import EXAMS, MIN_ATTENDANCE, SMSError


class AdminPanel:
    def __init__(self, db: JSONDatabase):
        self.db = db

    def dashboard(self) -> dict:
        classes = ClassManager(self.db).list()
        att, mm, rp = AttendanceManager(self.db), MarksManager(self.db), ResultProcessor(self.db)
        today = date.today().isoformat()
        per_class = []
        for c in classes:
            day = att.get_day(c["code"], today)
            summary = att.class_summary(c["code"])
            latest = None
            for exam in reversed(EXAMS):
                try:
                    res = rp.class_result(c["code"], exam)
                    if res["rows"]:
                        latest = res
                        break
                except SMSError:
                    continue
            per_class.append({
                "class": c, "students": len(StudentManager(self.db).list(c["code"])),
                "today": None if not day else {"present": list(day["records"].values()).count("P"),
                                               "total": len(day["records"])},
                "unmarked_last_7": len(att.unmarked_days(c["code"], date.today() - timedelta(days=7), date.today())),
                "attendance_avg": summary["average"], "shortage": len(summary["shortage"]),
                "latest_exam": latest["exam"] if latest else None,
                "pass_percent": latest["pass_percent"] if latest else None,
                "toppers": [t["name"] for t in latest["toppers"]] if latest else [],
                "marks_pending": {e: len(mm.missing(c["code"], e)) for e in EXAMS}})
        s = StudentManager(self.db).summary()
        return {"classes": len(classes), "students": s["active"], "by_gender": s["by_gender"], "per_class": per_class,
                "staff": sum(1 for u in self.db.all("users") if u["role"] != "student"),
                "min_attendance": MIN_ATTENDANCE}

    def record_counts(self) -> dict:
        return {n: len(self.db.all(n)) for n in ("users", "classes", "students", "attendance", "marks", "activity")}

    def activity(self, limit: int = 40, user: str | None = None) -> list[dict]:
        log = self.db.all("activity")
        if user:
            log = [a for a in log if a["user"] == user.lower()]
        return log[::-1][:limit]
