"""Admin Panel: library-wide statistics, activity log and staff accounts
(user management itself lives in auth.UserManager)."""
from __future__ import annotations

from collections import Counter

from .books import BookManager
from .database import JSONDatabase
from .fines import FineManager
from .members import MemberManager


class AdminPanel:
    def __init__(self, db: JSONDatabase):
        self.db = db

    def statistics(self) -> dict:
        members = MemberManager(self.db)
        ms = self.db.all("members")
        loans = self.db.all("loans")
        return {
            **BookManager(self.db).stats(),
            "members": len(ms),
            "members_by_status": dict(Counter(members.effective_status(m) for m in ms)),
            "members_by_type": dict(Counter(m["type"] for m in ms)),
            "loans_total": len(loans),
            "loans_active": sum(1 for l in loans if l["status"] == "ISSUED"),
            "reservations_active": sum(1 for r in self.db.all("reservations") if r["status"] in ("WAITING", "READY")),
            "fines_outstanding": round(sum(FineManager.balance(f) for f in self.db.all("fines")), 2),
            "fines_collected": round(sum(f["paid"] for f in self.db.all("fines")), 2),
            "membership_fees": round(sum(m["fee_paid"] for m in ms), 2),
        }

    def record_counts(self) -> dict:
        return {name: len(self.db.all(name)) for name in ("users", "books", "copies", "members", "loans",
                                                           "reservations", "fines", "activity")}

    def activity(self, limit: int = 40, user: str | None = None) -> list[dict]:
        log = self.db.all("activity")
        if user:
            log = [a for a in log if a["user"] == user.lower()]
        return log[::-1][:limit]
