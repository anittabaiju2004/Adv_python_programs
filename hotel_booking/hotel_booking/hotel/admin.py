"""Admin Panel: front-desk dashboard, system statistics and the activity log."""
from __future__ import annotations

from datetime import date

from .bookings import BookingManager
from .database import JSONDatabase
from .rooms import RoomManager


class AdminPanel:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.bookings = BookingManager(db)
        self.rooms = RoomManager(db)

    def dashboard(self, today: date | None = None) -> dict:
        today = today or date.today()
        rooms = self.rooms.summary()
        in_house = self.bookings.in_house()
        ds = today.isoformat()
        sold_tonight = sum(1 for b in self.db.all("bookings") if b["status"] in ("CONFIRMED", "CHECKED_IN")
                           and b["check_in"] <= ds < b["check_out"])
        pay_today = [p for p in self.db.all("payments") if p["at"][:10] == ds]
        return {
            "date": ds, "rooms": rooms["total"], "status": rooms["by_status"],
            "arrivals": self.bookings.arrivals(today), "departures": self.bookings.departures(today),
            "in_house": len(in_house), "guests_in_house": sum(b["adults"] + b["children"] for b in in_house),
            "sold_tonight": sold_tonight,
            "occupancy_tonight": round(sold_tonight / rooms["total"] * 100, 1) if rooms["total"] else 0.0,
            "overdue_departures": [b for b in in_house if b["check_out"] < ds],
            "pending_no_shows": [b for b in self.bookings.list("CONFIRMED") if b["check_in"] < ds],
            "collected_today": round(sum(p["amount"] for p in pay_today), 2),
            "upcoming_7_days": len([b for b in self.bookings.list("CONFIRMED") if ds <= b["check_in"] <=
                                    date.fromordinal(today.toordinal() + 7).isoformat()]),
        }

    def system_stats(self) -> dict:
        return {name: len(self.db.all(name)) for name in ("users", "rooms", "customers", "bookings", "payments",
                                                           "activity")}

    def activity(self, limit: int = 30, user: str | None = None, action: str | None = None) -> list[dict]:
        log = self.db.all("activity")
        if user:
            log = [a for a in log if a["user"] == user.lower()]
        if action:
            log = [a for a in log if action.upper() in a["action"]]
        return log[::-1][:limit]
