"""Admin Panel: dashboard statistics and the activity log."""
from __future__ import annotations

from collections import Counter
from datetime import date

from .categories import CategoryManager
from .database import JSONDatabase
from .leaderboard import Leaderboard


class AdminPanel:
    def __init__(self, db: JSONDatabase):
        self.db = db

    def dashboard(self) -> dict:
        users = self.db.all("users")
        qs = self.db.all("questions")
        rs = self.db.all("results")
        exams = [r for r in rs if r["mode"] == "Exam"]
        today = date.today().isoformat()
        return {
            "students": sum(1 for u in users if u["role"] == "student"),
            "active_today": len({r["username"] for r in rs if r["submitted_at"][:10] == today}),
            "staff": sum(1 for u in users if u["role"] != "student"),
            "questions": sum(1 for q in qs if q["active"]), "disabled_questions": sum(1 for q in qs if not q["active"]),
            "by_difficulty": dict(Counter(q["difficulty"] for q in qs if q["active"])),
            "categories": CategoryManager(self.db).stats(),
            "quizzes": len(self.db.all("quizzes")), "published": sum(1 for q in self.db.all("quizzes") if q["published"]),
            "attempts": len(rs), "attempts_today": sum(1 for r in rs if r["submitted_at"][:10] == today),
            "exam_attempts": len(exams), "practice_attempts": len(rs) - len(exams),
            "average": round(sum(r["percent"] for r in exams) / len(exams), 1) if exams else 0.0,
            "pass_rate": round(sum(r["passed"] for r in exams) / len(exams) * 100, 1) if exams else 0.0,
            "certificates": sum(1 for r in exams if r["certificate_code"]),
            "top_students": Leaderboard(self.db).overall(top=5),
            "recent": sorted(rs, key=lambda r: r["submitted_at"], reverse=True)[:5],
        }

    def record_counts(self) -> dict:
        return {n: len(self.db.all(n)) for n in ("users", "categories", "questions", "quizzes", "results", "bookmarks",
                                                  "activity")}

    def activity(self, limit: int = 40, user: str | None = None) -> list[dict]:
        log = self.db.all("activity")
        if user:
            log = [a for a in log if a["user"] == user.lower()]
        return log[::-1][:limit]
