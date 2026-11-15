"""Issue & Return: issue, return (with overdue / damage fines), renew,
lost books, overdue tracking, and the PDF issue slip with QR code."""
from __future__ import annotations

from pathlib import Path

from .auth import log_activity
from .books import BookManager
from .database import JSONDatabase
from .fines import FineManager
from .members import MemberManager
from .reservations import ReservationManager
from .utils import (LIBRARY_ADDRESS, LIBRARY_NAME, LIBRARY_PHONE, LOST_PROCESSING_FEE, MAX_RENEWALS, MEMBER_TYPES,
                    CirculationError, NotFoundError, PermissionDenied, ValidationError, add_days, days_between,
                    now_str, parse_date, today, validate_amount, validate_text)


class CirculationManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.books = BookManager(db, actor)
        self.members = MemberManager(db, actor)
        self.fines = FineManager(db, actor)
        self.reservations = ReservationManager(db, actor)

    def _next_id(self) -> str:
        return f"L{len(self.db.all('loans')) + 1:05d}"

    def get(self, ref: str) -> dict:
        """Loan by loan ID, or the current loan of an accession number."""
        key = str(ref or "").strip().upper()
        loan = self.db.find_one("loans", loan_id=key)
        if not loan:
            loan = next((l for l in self.db.find("loans", accession=key) if l["status"] == "ISSUED"), None)
        if not loan:
            raise NotFoundError(f"No loan found for '{ref}'.")
        return loan

    @staticmethod
    def _due(member: dict, on) -> str:
        """Loan period by member type, but never beyond membership expiry."""
        return min(add_days(on, MEMBER_TYPES[member["type"]]["loan_days"]), member["expires_on"])

    # -------------------------------------------------------------- issue
    def issue(self, member_id: str, ref: str, on=None) -> dict:
        """Issue a copy (by accession number) or any free copy of a title (by book ID / ISBN)."""
        on = parse_date(on or today())
        elig = self.members.eligibility(member_id, on)
        m = elig["member"]
        if not elig["can_borrow"]:
            raise CirculationError(f"{m['name']} cannot borrow: " + "; ".join(elig["reasons"]) + ".")
        key = str(ref or "").strip().upper()
        if key.startswith("ACC"):
            copy = self.books.get_copy(key)
            book = self.books.get(copy["book_id"])
        else:
            book = self.books.get(key)
            cs = self.books.copies(book["book_id"])
            copy = next((c for c in cs if c["status"] == "ON_HOLD" and c["hold_for"] == m["member_id"]), None) or \
                next((c for c in cs if c["status"] == "AVAILABLE"), None)
            if not copy:
                q = len(self.reservations.queue(book["book_id"]))
                raise CirculationError(f"No copy of '{book['title']}' is available"
                                       + (f" ({q} reservation(s) waiting)" if q else "") + ". You can reserve it.")
        if book["reference_only"]:
            raise CirculationError("Reference books are for reading in the library only.")
        if any(l["book_id"] == book["book_id"] for l in self.members.active_loans(m["member_id"])):
            raise CirculationError("This member already has a copy of this title.")
        if copy["status"] == "ON_HOLD" and copy["hold_for"] != m["member_id"]:
            raise CirculationError(f"Copy {copy['accession']} is held for another member until {copy['hold_until']}.")
        if copy["status"] not in ("AVAILABLE", "ON_HOLD"):
            raise CirculationError(f"Copy {copy['accession']} is {copy['status']}.")
        if copy["status"] == "AVAILABLE":
            waiting = [r for r in self.reservations.queue(book["book_id"]) if r["member_id"] != m["member_id"]]
            if waiting:
                raise CirculationError("Other members are waiting for this title; the copy must be held for them.")
        loan = {"loan_id": self._next_id(), "accession": copy["accession"], "book_id": book["book_id"],
                "title": book["title"], "member_id": m["member_id"], "member_name": m["name"],
                "issued_on": on.isoformat(), "due_on": self._due(m, on), "renewals": 0, "returned_on": None,
                "status": "ISSUED", "fine": 0.0, "issued_by": self.actor, "returned_by": None, "return_note": None}
        self.db.insert("loans", loan)
        self.db.update("copies", "accession", copy["accession"], {"status": "ISSUED", "hold_for": None, "hold_until": None})
        self.reservations.fulfil(m["member_id"], book["book_id"], on)
        log_activity(self.db, self.actor, "ISSUED", f"{loan['loan_id']} {copy['accession']} to {m['member_id']}")
        return loan

    # ------------------------------------------------------------- return
    def overdue_fine(self, loan: dict, on=None) -> tuple[int, float]:
        """(days overdue, fine) — fine is capped at the book's price."""
        on = parse_date(on or today())
        days = max(0, days_between(loan["due_on"], on))
        if not days:
            return 0, 0.0
        m = self.members.get(loan["member_id"])
        price = self.books.get(loan["book_id"])["price"]
        return days, round(min(days * MEMBER_TYPES[m["type"]]["fine_per_day"], price), 2)

    def return_book(self, ref: str, on=None, damaged: bool = False, damage_fee=0, note: str = "") -> dict:
        loan = self.get(ref)
        if loan["status"] != "ISSUED":
            raise CirculationError(f"Loan {loan['loan_id']} is already {loan['status'].lower()}.")
        on = parse_date(on or today())
        if on.isoformat() < loan["issued_on"]:
            raise ValidationError("Return date is before the issue date.")
        days, fine = self.overdue_fine(loan, on)
        fines = []
        if fine:
            fines.append(self.fines.create(loan["member_id"], "OVERDUE", fine, loan["loan_id"], loan["accession"],
                                           f"{days} day(s) late", on))
        if damaged:
            fee = validate_amount(damage_fee, "Damage fee", 0, self.books.get(loan["book_id"])["price"]) if damage_fee else 0
            if fee:
                fines.append(self.fines.create(loan["member_id"], "DAMAGE", fee, loan["loan_id"], loan["accession"],
                                               validate_text(note, "Note", 120) or "Damaged on return", on))
        total = round(sum(f["amount"] for f in fines), 2)
        updated = self.db.update("loans", "loan_id", loan["loan_id"],
                                 {"status": "RETURNED", "returned_on": on.isoformat(), "fine": total,
                                  "returned_by": self.actor, "return_note": validate_text(note, "Note", 120) or None})
        hold = None
        if damaged:
            self.db.update("copies", "accession", loan["accession"], {"status": "DAMAGED", "note": note or "Damaged"})
        else:
            hold = self.reservations.allocate_copy(loan["accession"], on)
        log_activity(self.db, self.actor, "RETURNED", f"{loan['loan_id']} {loan['accession']} fine {total:.2f}")
        return {"loan": updated, "days_late": days, "fine": total, "hold_for": hold}

    # -------------------------------------------------------------- renew
    def renew(self, ref: str, on=None, by_member: str | None = None) -> dict:
        loan = self.get(ref)
        if by_member and loan["member_id"] != by_member.upper():
            raise PermissionDenied("You can only renew your own loans.")
        if loan["status"] != "ISSUED":
            raise CirculationError("Only books currently on loan can be renewed.")
        on = parse_date(on or today())
        if loan["due_on"] < on.isoformat():
            raise CirculationError("Overdue books cannot be renewed; please return the book and pay the fine.")
        if loan["renewals"] >= MAX_RENEWALS:
            raise CirculationError(f"Maximum {MAX_RENEWALS} renewals reached.")
        if self.reservations.queue(loan["book_id"]):
            raise CirculationError("Another member has reserved this book; it cannot be renewed.")
        elig = self.members.eligibility(loan["member_id"], on)
        blocking = [r for r in elig["reasons"] if not r.startswith("borrowing limit")]
        if blocking:
            raise CirculationError("Cannot renew: " + "; ".join(blocking) + ".")
        new_due = self._due(elig["member"], on)
        if new_due <= loan["due_on"]:
            reason = "the membership expires on " + elig["member"]["expires_on"] \
                if new_due == elig["member"]["expires_on"] else "the loan already runs to " + loan["due_on"]
            raise CirculationError(f"Renewing today would not extend the due date ({reason}).")
        log_activity(self.db, self.actor, "RENEWED", f"{loan['loan_id']} to {new_due}")
        return self.db.update("loans", "loan_id", loan["loan_id"], {"due_on": new_due, "renewals": loan["renewals"] + 1})

    # --------------------------------------------------------------- lost
    def mark_lost(self, ref: str, on=None) -> dict:
        """Lost copy: member pays book price + processing fee (+ any overdue fine to date)."""
        loan = self.get(ref)
        if loan["status"] != "ISSUED":
            raise CirculationError("Only books currently on loan can be reported lost.")
        on = parse_date(on or today())
        price = self.books.get(loan["book_id"])["price"]
        days, late = self.overdue_fine(loan, on)
        if late:
            self.fines.create(loan["member_id"], "OVERDUE", late, loan["loan_id"], loan["accession"],
                              f"{days} day(s) late (until reported lost)", on)
        f = self.fines.create(loan["member_id"], "LOST", price + LOST_PROCESSING_FEE, loan["loan_id"],
                              loan["accession"], f"Book price {price:,.2f} + processing {LOST_PROCESSING_FEE:,.2f}", on)
        self.db.update("copies", "accession", loan["accession"], {"status": "LOST", "note": f"Lost by {loan['member_id']}"})
        log_activity(self.db, self.actor, "LOST", f"{loan['loan_id']} {loan['accession']}")
        return self.db.update("loans", "loan_id", loan["loan_id"],
                              {"status": "LOST", "returned_on": on.isoformat(), "fine": round(f["amount"] + late, 2)})

    # ------------------------------------------------------------ queries
    def loans(self, member_id: str | None = None, status: str | None = None) -> list[dict]:
        ls = self.db.find("loans", **({"member_id": member_id.upper()} if member_id else {}))
        if status:
            ls = [l for l in ls if l["status"] == status.upper()]
        return sorted(ls, key=lambda l: l["loan_id"], reverse=True)

    def overdue(self, on=None) -> list[dict]:
        on = parse_date(on or today())
        out = []
        for l in self.loans(status="ISSUED"):
            days, fine = self.overdue_fine(l, on)
            if days:
                out.append({**l, "days_overdue": days, "fine_so_far": fine})
        return sorted(out, key=lambda l: -l["days_overdue"])

    def due_between(self, start, end) -> list[dict]:
        s, e = parse_date(start).isoformat(), parse_date(end).isoformat()
        return sorted((l for l in self.loans(status="ISSUED") if s <= l["due_on"] <= e), key=lambda l: l["due_on"])

    # ------------------------------------------------------------ slip PDF
    def issue_slip_pdf(self, loan_id: str, out_dir: Path | str) -> Path:
        """A6 issue slip with the loan details and a QR code (loan, copy, member, due date)."""
        from reportlab.graphics import renderPDF
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A6
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from .qr import qr_drawing

        loan = self.get(loan_id)
        book = self.books.get(loan["book_id"])
        m = self.members.get(loan["member_id"])
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"issue_slip_{loan['loan_id']}.pdf"
        w, h = A6
        c = canvas.Canvas(str(path), pagesize=A6)
        c.setFillColor(colors.HexColor("#3b2f6b"))
        c.rect(0, h - 18 * mm, w, 18 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 8 * mm, LIBRARY_NAME)
        c.setFont("Helvetica", 7)
        c.drawCentredString(w / 2, h - 12.5 * mm, LIBRARY_ADDRESS)
        c.drawCentredString(w / 2, h - 16 * mm, f"Phone {LIBRARY_PHONE}")
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        title = "BOOK ISSUE SLIP" if loan["status"] == "ISSUED" else f"LOAN RECORD ({loan['status']})"
        c.drawCentredString(w / 2, h - 26 * mm, title)
        rows = [("Loan No", loan["loan_id"]), ("Member", f"{m['name']} ({m['member_id']})"), ("Type", m["type"]),
                ("Title", book["title"][:38]), ("Author", book["authors"][:38]), ("Accession", loan["accession"]),
                ("Issued on", loan["issued_on"]), ("Renewals", f"{loan['renewals']} of {MAX_RENEWALS}")]
        y = h - 34 * mm
        for label, val in rows:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(8 * mm, y, f"{label}:")
            c.setFont("Helvetica", 8)
            c.drawString(28 * mm, y, str(val))
            y -= 5 * mm
        c.setFillColor(colors.HexColor("#efeaf9"))
        c.rect(8 * mm, y - 6 * mm, w - 16 * mm, 9 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3b2f6b"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, y - 3 * mm, f"DUE ON  {loan['due_on']}")
        data = f"LIB-LOAN:{loan['loan_id']}|{loan['accession']}|{m['member_id']}|DUE:{loan['due_on']}"
        renderPDF.draw(qr_drawing(data, 26 * mm), c, (w - 26 * mm) / 2, 14 * mm)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Oblique", 6.5)
        rate = MEMBER_TYPES[m["type"]]["fine_per_day"]
        c.drawCentredString(w / 2, 9 * mm, f"Late return fine: Rs. {rate:g} per day. Renew online before the due date.")
        c.drawCentredString(w / 2, 5.5 * mm, f"Issued by {loan['issued_by']} · {now_str().replace('T', ' ')}")
        c.showPage()
        c.save()
        return path
