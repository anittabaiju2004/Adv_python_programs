"""Reservation Management: a first-come queue per title. When a copy comes
back it is held for the next member in the queue for HOLD_DAYS days."""
from __future__ import annotations

from .auth import log_activity
from .books import BookManager
from .database import JSONDatabase
from .members import MemberManager
from .utils import (HOLD_DAYS, MAX_RESERVATIONS, CirculationError, LibraryError, NotFoundError, PermissionDenied,
                    add_days, now_str, parse_date, today)

ACTIVE = ("WAITING", "READY")


class ReservationManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.books = BookManager(db, actor)
        self.members = MemberManager(db, actor)

    def _next_id(self) -> str:
        return f"R{len(self.db.all('reservations')) + 1:05d}"

    def get(self, res_id: str) -> dict:
        r = self.db.find_one("reservations", res_id=str(res_id or "").strip().upper())
        if not r:
            raise NotFoundError(f"Reservation '{res_id}' not found.")
        return r

    def queue(self, book_id: str) -> list[dict]:
        return sorted((r for r in self.db.find("reservations", book_id=book_id, status="WAITING")),
                      key=lambda r: (r["reserved_on"], r["res_id"]))

    def list(self, member_id: str | None = None, status: str | None = None, book_id: str | None = None) -> list[dict]:
        rs = self.db.all("reservations")
        if member_id:
            rs = [r for r in rs if r["member_id"] == member_id.upper()]
        if status:
            rs = [r for r in rs if r["status"] == status.upper()]
        if book_id:
            rs = [r for r in rs if r["book_id"] == book_id.upper()]
        return sorted(rs, key=lambda r: r["res_id"], reverse=True)

    def position(self, res_id: str) -> int | None:
        r = self.get(res_id)
        if r["status"] != "WAITING":
            return None
        return [x["res_id"] for x in self.queue(r["book_id"])].index(r["res_id"]) + 1

    # ------------------------------------------------------------ reserve
    def reserve(self, member_id: str, book_ref: str, on=None) -> dict:
        m = self.members.get(member_id)
        book = self.books.get(book_ref)
        on = parse_date(on or today())
        status = self.members.effective_status(m, on)
        if status != "ACTIVE":
            raise CirculationError(f"Membership is {status.lower()}.")
        if book["reference_only"]:
            raise CirculationError("Reference books cannot be borrowed or reserved.")
        if any(l["book_id"] == book["book_id"] for l in self.members.active_loans(m["member_id"])):
            raise CirculationError("You already have this book on loan.")
        mine = [r for r in self.list(m["member_id"]) if r["status"] in ACTIVE]
        if any(r["book_id"] == book["book_id"] for r in mine):
            raise CirculationError("You have already reserved this book.")
        if len(mine) >= MAX_RESERVATIONS:
            raise CirculationError(f"At most {MAX_RESERVATIONS} active reservations are allowed.")
        avail = self.books.availability(book["book_id"])
        if avail["available"] and not self.queue(book["book_id"]):
            raise CirculationError(f"{avail['available']} copy(ies) available on the shelf — borrow it directly.")
        if not avail["total"]:
            raise CirculationError("The library has no copies of this title in its collection.")
        r = {"res_id": self._next_id(), "book_id": book["book_id"], "title": book["title"],
             "member_id": m["member_id"], "reserved_on": on.isoformat(), "status": "WAITING", "accession": None,
             "ready_on": None, "hold_until": None, "closed_on": None, "created_at": now_str()}
        self.db.insert("reservations", r)
        log_activity(self.db, self.actor, "RESERVED", f"{r['res_id']} {book['book_id']} for {m['member_id']}")
        self.allocate(book["book_id"], on)     # a copy may already be free (e.g. after holds expired)
        return self.get(r["res_id"])

    # -------------------------------------------------------- allocation
    def allocate_copy(self, accession: str, on=None) -> dict | None:
        """Give a freshly returned / available copy to the first member in the queue.
        Returns the reservation that is now READY, or None (copy back on the shelf)."""
        c = self.books.get_copy(accession)
        on = parse_date(on or today())
        q = self.queue(c["book_id"])
        if not q:
            self.db.update("copies", "accession", c["accession"], {"status": "AVAILABLE", "hold_for": None,
                                                                   "hold_until": None})
            return None
        r = q[0]
        until = add_days(on, HOLD_DAYS)
        self.db.update("copies", "accession", c["accession"], {"status": "ON_HOLD", "hold_for": r["member_id"],
                                                               "hold_until": until})
        log_activity(self.db, self.actor, "HOLD_READY", f"{r['res_id']} {c['accession']} for {r['member_id']}")
        return self.db.update("reservations", "res_id", r["res_id"],
                              {"status": "READY", "accession": c["accession"], "ready_on": on.isoformat(),
                               "hold_until": until})

    def allocate(self, book_id: str, on=None) -> list[dict]:
        """Hold available copies for waiting members (e.g. after adding new copies)."""
        ready = []
        for c in self.books.copies(book_id):
            if not self.queue(c["book_id"]):
                break
            if c["status"] == "AVAILABLE":
                r = self.allocate_copy(c["accession"], on)
                if r:
                    ready.append(r)
        return ready

    def fulfil(self, member_id: str, book_id: str, on=None) -> None:
        for r in self.list(member_id, book_id=book_id):
            if r["status"] in ACTIVE:
                self.db.update("reservations", "res_id", r["res_id"],
                               {"status": "FULFILLED", "closed_on": parse_date(on or today()).isoformat()})

    def cancel(self, res_id: str, by_member: str | None = None, on=None) -> dict:
        r = self.get(res_id)
        if by_member and r["member_id"] != by_member.upper():
            raise PermissionDenied("You can only cancel your own reservations.")
        if r["status"] not in ACTIVE:
            raise LibraryError(f"Reservation is already {r['status'].lower()}.")
        updated = self.db.update("reservations", "res_id", r["res_id"],
                                 {"status": "CANCELLED", "closed_on": parse_date(on or today()).isoformat()})
        if r["status"] == "READY":
            self.allocate_copy(r["accession"], on)             # pass the copy to the next member
        log_activity(self.db, self.actor, "RESERVATION_CANCELLED", r["res_id"])
        return updated

    def expire_holds(self, on=None) -> list[dict]:
        """READY reservations whose hold period has passed expire; the copy moves on."""
        on = parse_date(on or today())
        expired = []
        for r in self.list(status="READY"):
            if r["hold_until"] < on.isoformat():
                expired.append(self.db.update("reservations", "res_id", r["res_id"],
                                              {"status": "EXPIRED", "closed_on": on.isoformat()}))
                self.allocate_copy(r["accession"], on)
                log_activity(self.db, self.actor, "HOLD_EXPIRED", r["res_id"])
        return expired
