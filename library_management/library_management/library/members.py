"""Member Management: registration with login, membership renewal, suspension,
borrowing eligibility, and a printable member card with QR code."""
from __future__ import annotations

from pathlib import Path

from .auth import log_activity
from .database import JSONDatabase
from .fines import FineManager
from .utils import (FINE_BLOCK_LIMIT, LIBRARY_ADDRESS, LIBRARY_NAME, MEMBER_TYPES, MEMBERSHIP_DAYS,
                    LibraryError, NotFoundError, ValidationError, add_days, hash_password, now_str, parse_date,
                    temporary_password, today, validate_choice, validate_email, validate_name, validate_phone,
                    validate_text)


class MemberManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def _next_id(self) -> str:
        nums = [int(m["member_id"][1:]) for m in self.db.all("members")]
        return f"M{(max(nums) + 1) if nums else 1:04d}"

    # ---------------------------------------------------------------- crud
    def add(self, name: str, member_type: str, phone: str, email: str = "", address: str = "",
            id_number: str = "", department: str = "", on=None) -> tuple[dict, str]:
        """Register a member and create their portal login. Returns (member, temporary_password)."""
        mtype = validate_choice(member_type, MEMBER_TYPES, "member type")
        phone = validate_phone(phone)
        email = validate_email(email)
        id_number = validate_text(id_number, "Roll / employee / ID number", 30).upper()
        if mtype in ("Student", "Faculty", "Staff") and not id_number:
            raise ValidationError(f"{mtype} members need a roll number or employee ID.")
        for m in self.db.all("members"):
            if m["status"] != "CLOSED" and (m["phone"] == phone or (email and m["email"] == email)
                                            or (id_number and m["id_number"] == id_number)):
                raise ValidationError(f"Already registered as {m['member_id']} ({m['name']}).")
        joined = parse_date(on or today())
        member = {"member_id": self._next_id(), "name": validate_name(name), "type": mtype, "phone": phone,
                  "email": email, "address": validate_text(address, "Address", 200), "id_number": id_number,
                  "department": validate_text(department, "Department / class", 60), "joined_on": joined.isoformat(),
                  "expires_on": add_days(joined, MEMBERSHIP_DAYS), "status": "ACTIVE", "status_reason": None,
                  "fee_paid": MEMBER_TYPES[mtype]["fee"], "created_at": now_str()}
        self.db.insert("members", member)
        temp = temporary_password()
        h, s = hash_password(temp)
        self.db.insert("users", {"username": member["member_id"].lower(), "password_hash": h, "salt": s,
                                 "role": "member", "member_id": member["member_id"], "name": member["name"],
                                 "phone": phone, "email": email, "active": True, "must_change_password": True,
                                 "failed_attempts": 0, "created_at": now_str(), "last_login": None})
        log_activity(self.db, self.actor, "MEMBER_ADDED", f"{member['member_id']} {member['name']} ({mtype})")
        return member, temp

    def get(self, member_id: str) -> dict:
        m = self.db.find_one("members", member_id=str(member_id or "").strip().upper())
        if not m:
            raise NotFoundError(f"Member '{member_id}' not found.")
        return m

    def list(self, status: str | None = None, member_type: str | None = None) -> list[dict]:
        ms = self.db.all("members")
        if status:
            ms = [m for m in ms if self.effective_status(m) == status.upper()]
        if member_type:
            ms = [m for m in ms if m["type"] == validate_choice(member_type, MEMBER_TYPES, "member type")]
        return sorted(ms, key=lambda m: m["member_id"])

    def search(self, keyword: str) -> list[dict]:
        k = str(keyword or "").strip().lower()
        digits = "".join(c for c in k if c.isdigit())
        return [m for m in self.list() if not k or k in m["name"].lower() or k == m["member_id"].lower()
                or k == m["id_number"].lower() or (len(digits) >= 4 and digits in m["phone"]) or k == m["email"]]

    def update(self, member_id: str, **changes) -> dict:
        m = self.get(member_id)
        clean = {}
        if changes.get("name"):
            clean["name"] = validate_name(changes["name"])
        if changes.get("phone"):
            clean["phone"] = validate_phone(changes["phone"])
        if changes.get("email") is not None and "email" in changes:
            clean["email"] = validate_email(changes["email"])
        for key, label, n in (("address", "Address", 200), ("department", "Department", 60)):
            if changes.get(key) is not None and key in changes:
                clean[key] = validate_text(changes[key], label, n)
        if changes.get("type"):
            clean["type"] = validate_choice(changes["type"], MEMBER_TYPES, "member type")
            if len(self.active_loans(m["member_id"])) > MEMBER_TYPES[clean["type"]]["max_books"]:
                raise LibraryError("Member holds more books than the new type allows; return some first.")
        if not clean:
            raise ValidationError("Nothing to update.")
        for other in self.db.all("members"):
            if other["member_id"] != m["member_id"] and other["status"] != "CLOSED" and \
                    (clean.get("phone") and other["phone"] == clean["phone"]):
                raise ValidationError(f"Phone already used by {other['member_id']}.")
        log_activity(self.db, self.actor, "MEMBER_UPDATED", f"{m['member_id']}: {', '.join(clean)}")
        return self.db.update("members", "member_id", m["member_id"], clean)

    # ------------------------------------------------------------- status
    @staticmethod
    def effective_status(m: dict, on=None) -> str:
        if m["status"] == "ACTIVE" and m["expires_on"] < parse_date(on or today()).isoformat():
            return "EXPIRED"
        return m["status"]

    def renew(self, member_id: str, on=None) -> dict:
        m = self.get(member_id)
        if m["status"] == "CLOSED":
            raise LibraryError("Closed memberships cannot be renewed; register again.")
        start = max(parse_date(m["expires_on"]), parse_date(on or today()))
        log_activity(self.db, self.actor, "MEMBERSHIP_RENEWED", m["member_id"])
        return self.db.update("members", "member_id", m["member_id"],
                              {"expires_on": add_days(start, MEMBERSHIP_DAYS),
                               "fee_paid": round(m["fee_paid"] + MEMBER_TYPES[m["type"]]["fee"], 2)})

    def suspend(self, member_id: str, reason: str) -> dict:
        m = self.get(member_id)
        if m["status"] != "ACTIVE":
            raise LibraryError(f"Member is {m['status']}.")
        log_activity(self.db, self.actor, "MEMBER_SUSPENDED", f"{m['member_id']} ({reason})")
        self.db.update("users", "username", m["member_id"].lower(), {"active": False})
        return self.db.update("members", "member_id", m["member_id"],
                              {"status": "SUSPENDED", "status_reason": validate_text(reason, "Reason", 120, required=True)})

    def reactivate(self, member_id: str) -> dict:
        m = self.get(member_id)
        if m["status"] != "SUSPENDED":
            raise LibraryError("Only suspended members can be reactivated.")
        self.db.update("users", "username", m["member_id"].lower(), {"active": True})
        log_activity(self.db, self.actor, "MEMBER_REACTIVATED", m["member_id"])
        return self.db.update("members", "member_id", m["member_id"], {"status": "ACTIVE", "status_reason": None})

    def close(self, member_id: str, reason: str = "Left institution") -> dict:
        """Close a membership. All books must be returned and all fines cleared."""
        m = self.get(member_id)
        if self.active_loans(m["member_id"]):
            raise LibraryError("Member still has books on loan.")
        if FineManager(self.db).outstanding(m["member_id"]) > 0:
            raise LibraryError("Member has unpaid fines.")
        for r in self.db.find("reservations", member_id=m["member_id"]):
            if r["status"] in ("WAITING", "READY"):
                raise LibraryError("Cancel the member's active reservations first.")
        self.db.update("users", "username", m["member_id"].lower(), {"active": False})
        log_activity(self.db, self.actor, "MEMBER_CLOSED", m["member_id"])
        return self.db.update("members", "member_id", m["member_id"], {"status": "CLOSED", "status_reason": reason})

    # -------------------------------------------------------- eligibility
    def active_loans(self, member_id: str) -> list[dict]:
        return [l for l in self.db.find("loans", member_id=member_id.upper()) if l["status"] == "ISSUED"]

    def eligibility(self, member_id: str, on=None) -> dict:
        """Whether the member may borrow, with every reason that blocks it."""
        m = self.get(member_id)
        on = parse_date(on or today()).isoformat()
        rules = MEMBER_TYPES[m["type"]]
        loans = self.active_loans(m["member_id"])
        overdue = [l for l in loans if l["due_on"] < on]
        fines = FineManager(self.db).outstanding(m["member_id"])
        status = self.effective_status(m, on)
        reasons = []
        if status != "ACTIVE":
            reasons.append(f"membership is {status.lower()}" + (f" ({m['status_reason']})" if m["status_reason"] else ""))
        if len(loans) >= rules["max_books"]:
            reasons.append(f"borrowing limit reached ({len(loans)}/{rules['max_books']})")
        if overdue:
            reasons.append(f"{len(overdue)} overdue book(s) must be returned")
        if fines > FINE_BLOCK_LIMIT:
            reasons.append(f"unpaid fines {fines:,.2f} exceed {FINE_BLOCK_LIMIT:,.0f}")
        return {"member": m, "can_borrow": not reasons, "reasons": reasons, "loans": len(loans),
                "limit": rules["max_books"], "overdue": len(overdue), "fines": fines, "status": status}

    # ---------------------------------------------------------- card PDF
    def card_pdf(self, member_id: str, out_dir: Path | str) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.graphics import renderPDF
        from .qr import qr_drawing

        m = self.get(member_id)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"member_card_{m['member_id']}.pdf"
        w, h = 86 * mm, 54 * mm                       # ID-card size
        c = canvas.Canvas(str(path), pagesize=(w, h))
        c.setFillColor(colors.HexColor("#3b2f6b"))
        c.rect(0, h - 13 * mm, w, 13 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(4 * mm, h - 6.5 * mm, LIBRARY_NAME)
        c.setFont("Helvetica", 6)
        c.drawString(4 * mm, h - 10.5 * mm, LIBRARY_ADDRESS[:60])
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(4 * mm, h - 20 * mm, m["name"][:26])
        c.setFont("Helvetica", 7.5)
        lines = [f"Member ID: {m['member_id']}", f"Type: {m['type']}" + (f"  ·  {m['id_number']}" if m["id_number"] else ""),
                 f"Valid till: {m['expires_on']}", f"Phone: {m['phone']}"]
        for i, t in enumerate(lines):
            c.drawString(4 * mm, h - (26 + i * 4.6) * mm, t)
        renderPDF.draw(qr_drawing(f"LIB-MEMBER:{m['member_id']}", 24 * mm), c, w - 28 * mm, 4 * mm)
        c.setFont("Helvetica-Oblique", 5.5)
        c.drawString(4 * mm, 3 * mm, "Present this card when borrowing. Scan the QR code at the issue desk.")
        c.showPage()
        c.save()
        return path
