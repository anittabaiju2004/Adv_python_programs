"""Fine Management: overdue, lost and damage fines; part payments, waivers,
outstanding balances and receipts."""
from __future__ import annotations

from .auth import log_activity
from .database import JSONDatabase
from .utils import (PAYMENT_MODES, LibraryError, NotFoundError, ValidationError, now_str, parse_date,
                    validate_amount, validate_choice, validate_text)

FINE_TYPES = ["OVERDUE", "LOST", "DAMAGE"]


class FineManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def create(self, member_id: str, ftype: str, amount: float, loan_id: str | None = None,
               accession: str | None = None, note: str = "", on=None) -> dict | None:
        amount = round(float(amount), 2)
        if amount <= 0:
            return None
        f = {"fine_id": f"F{len(self.db.all('fines')) + 1:05d}", "member_id": member_id,
             "type": validate_choice(ftype, FINE_TYPES, "fine type"), "amount": amount, "paid": 0.0, "waived": 0.0,
             "status": "UNPAID", "loan_id": loan_id, "accession": accession, "note": note,
             "created_on": parse_date(on).isoformat() if on else now_str()[:10], "payments": [],
             "waived_by": None, "waive_reason": None}
        self.db.insert("fines", f)
        log_activity(self.db, self.actor, "FINE_RAISED", f"{f['fine_id']} {member_id} {ftype} {amount:.2f}")
        return f

    def get(self, fine_id: str) -> dict:
        f = self.db.find_one("fines", fine_id=str(fine_id or "").strip().upper())
        if not f:
            raise NotFoundError(f"Fine '{fine_id}' not found.")
        return f

    @staticmethod
    def balance(f: dict) -> float:
        return round(f["amount"] - f["paid"] - f["waived"], 2)

    @staticmethod
    def _status(f: dict) -> str:
        bal = FineManager.balance(f)
        if bal <= 0.005:
            return "WAIVED" if f["waived"] and not f["paid"] else "PAID"
        return "PARTIAL" if f["paid"] or f["waived"] else "UNPAID"

    def pay(self, fine_id: str, amount, mode: str = "Cash", reference: str = "") -> dict:
        f = self.get(fine_id)
        bal = self.balance(f)
        if bal <= 0.005:
            raise LibraryError("This fine is already settled.")
        amount = validate_amount(amount, "Amount", 0.01, bal)
        mode = validate_choice(mode, PAYMENT_MODES, "payment mode")
        if mode != "Cash" and not str(reference or "").strip():
            raise ValidationError(f"Enter the transaction reference for {mode} payments.")
        f["paid"] = round(f["paid"] + amount, 2)
        f["payments"].append({"at": now_str(), "amount": amount, "mode": mode,
                              "reference": validate_text(reference, "Reference", 40), "by": self.actor,
                              "receipt": f"RC{len([p for x in self.db.all('fines') for p in x['payments']]) + 1:05d}"})
        f["status"] = self._status(f)
        log_activity(self.db, self.actor, "FINE_PAID", f"{f['fine_id']} {amount:.2f} {mode}")
        return self.db.update("fines", "fine_id", f["fine_id"], f)

    def pay_all(self, member_id: str, mode: str = "Cash", reference: str = "") -> float:
        total = 0.0
        for f in self.outstanding_fines(member_id):
            bal = self.balance(f)
            self.pay(f["fine_id"], bal, mode, reference)
            total += bal
        if not total:
            raise LibraryError("No outstanding fines.")
        return round(total, 2)

    def waive(self, fine_id: str, reason: str, amount=None) -> dict:
        f = self.get(fine_id)
        bal = self.balance(f)
        if bal <= 0.005:
            raise LibraryError("This fine is already settled.")
        amount = bal if amount in (None, "") else validate_amount(amount, "Waiver amount", 0.01, bal)
        f["waived"] = round(f["waived"] + amount, 2)
        f["waived_by"] = self.actor
        f["waive_reason"] = validate_text(reason, "Reason", 120, required=True)
        f["status"] = self._status(f)
        log_activity(self.db, self.actor, "FINE_WAIVED", f"{f['fine_id']} {amount:.2f} ({reason})")
        return self.db.update("fines", "fine_id", f["fine_id"], f)

    def list(self, member_id: str | None = None, status: str | None = None) -> list[dict]:
        fs = self.db.find("fines", **({"member_id": member_id.upper()} if member_id else {}))
        if status:
            fs = [f for f in fs if f["status"] == status.upper()]
        return sorted(fs, key=lambda f: f["fine_id"], reverse=True)

    def outstanding_fines(self, member_id: str) -> list[dict]:
        return [f for f in self.list(member_id) if self.balance(f) > 0.005]

    def outstanding(self, member_id: str) -> float:
        return round(sum(self.balance(f) for f in self.outstanding_fines(member_id)), 2)

    def collections(self, start, end) -> dict:
        s, e = parse_date(start).isoformat(), parse_date(end).isoformat()
        pays = [(f, p) for f in self.db.all("fines") for p in f["payments"] if s <= p["at"][:10] <= e]
        by_mode, by_type = {}, {}
        for f, p in pays:
            by_mode[p["mode"]] = round(by_mode.get(p["mode"], 0) + p["amount"], 2)
            by_type[f["type"]] = round(by_type.get(f["type"], 0) + p["amount"], 2)
        raised = [f for f in self.db.all("fines") if s <= f["created_on"] <= e]
        return {"start": s, "end": e, "collected": round(sum(p["amount"] for _, p in pays), 2),
                "receipts": len(pays), "by_mode": by_mode, "by_type": by_type,
                "raised": round(sum(f["amount"] for f in raised), 2),
                "waived": round(sum(f["waived"] for f in raised), 2),
                "outstanding_total": round(sum(self.balance(f) for f in self.db.all("fines")), 2)}
