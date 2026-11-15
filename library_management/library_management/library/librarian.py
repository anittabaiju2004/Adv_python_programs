"""Librarian module: the circulation desk's daily view — today's activity,
books due soon, overdue books, holds waiting for pickup, expiring
memberships — and reminder notices."""
from __future__ import annotations

from .circulation import CirculationManager
from .database import JSONDatabase
from .fines import FineManager
from .members import MemberManager
from .reservations import ReservationManager
from .utils import add_days, parse_date, today


class LibrarianDesk:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.circ = CirculationManager(db, actor)
        self.members = MemberManager(db, actor)
        self.res = ReservationManager(db, actor)
        self.fines = FineManager(db, actor)

    def dashboard(self, on=None) -> dict:
        on = parse_date(on or today())
        d = on.isoformat()
        loans = self.db.all("loans")
        coll = self.fines.collections(d, d)
        return {
            "date": d,
            "issued_today": sum(1 for l in loans if l["issued_on"] == d),
            "returned_today": sum(1 for l in loans if l["returned_on"] == d and l["status"] == "RETURNED"),
            "on_loan": sum(1 for l in loans if l["status"] == "ISSUED"),
            "due_today": [l for l in self.circ.loans(status="ISSUED") if l["due_on"] == d],
            "due_next_3_days": self.circ.due_between(add_days(on, 1), add_days(on, 3)),
            "overdue": self.circ.overdue(on),
            "holds_ready": self.res.list(status="READY"),
            "waiting": len(self.res.list(status="WAITING")),
            "fines_collected_today": coll["collected"],
            "fines_outstanding": coll["outstanding_total"],
            "expiring_members": [m for m in self.members.list("ACTIVE") if m["expires_on"] <= add_days(on, 30)],
        }

    def reminders(self, on=None) -> list[dict]:
        """Reminder notices: due in the next 2 days, overdue, and holds ready for pickup."""
        on = parse_date(on or today())
        out = []
        for l in self.circ.due_between(on, add_days(on, 2)):
            m = self.members.get(l["member_id"])
            out.append({"member": m, "kind": "DUE SOON",
                        "message": f"Dear {m['name']}, '{l['title']}' ({l['accession']}) is due on {l['due_on']}. "
                                   "Please return or renew it on time."})
        for l in self.circ.overdue(on):
            m = self.members.get(l["member_id"])
            out.append({"member": m, "kind": "OVERDUE",
                        "message": f"Dear {m['name']}, '{l['title']}' ({l['accession']}) was due on {l['due_on']} and "
                                   f"is {l['days_overdue']} day(s) overdue. Fine so far: Rs. {l['fine_so_far']:,.2f}."})
        for r in self.res.list(status="READY"):
            m = self.members.get(r["member_id"])
            out.append({"member": m, "kind": "READY FOR PICKUP",
                        "message": f"Dear {m['name']}, your reserved book '{r['title']}' is ready. "
                                   f"Please collect it by {r['hold_until']}."})
        return out
