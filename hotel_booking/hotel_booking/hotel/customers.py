"""Customer Management: guest registration with ID proof, search, update and
booking history."""
from __future__ import annotations

import re

from .auth import log_activity
from .database import JSONDatabase
from .utils import (HotelError, NotFoundError, ValidationError, now_str, validate_email, validate_id_proof,
                    validate_name, validate_phone, validate_text)


class CustomerManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def _next_id(self) -> str:
        nums = [int(c["customer_id"][1:]) for c in self.db.all("customers")]
        return f"C{(max(nums) + 1) if nums else 1001}"

    def add(self, name: str, phone: str, email: str = "", id_type: str = "", id_number: str = "",
            address: str = "", nationality: str = "Indian", gstin: str = "") -> dict:
        phone = validate_phone(phone)
        if self.find_by_phone(phone):
            raise ValidationError(f"A guest with phone {phone} is already registered "
                                  f"({self.find_by_phone(phone)['customer_id']}).")
        id_type, id_number = validate_id_proof(id_type, id_number) if id_type else ("", "")
        if id_number and any(c["id_number"] == id_number for c in self.db.all("customers")):
            raise ValidationError("A guest with this ID proof is already registered.")
        gstin = str(gstin or "").strip().upper()
        if gstin and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]", gstin):
            raise ValidationError("GSTIN must be 15 characters, e.g. 32ABCDE1234F1Z5.")
        c = {"customer_id": self._next_id(), "name": validate_name(name), "phone": phone,
             "email": validate_email(email), "id_type": id_type, "id_number": id_number,
             "address": validate_text(address, "Address", 200),
             "nationality": validate_text(nationality, "Nationality", 40) or "Indian",
             "gstin": gstin, "created_at": now_str()}
        self.db.insert("customers", c)
        log_activity(self.db, self.actor, "CUSTOMER_ADDED", f"{c['customer_id']} {c['name']}")
        return c

    def get(self, customer_id: str) -> dict:
        c = self.db.find_one("customers", customer_id=str(customer_id or "").strip().upper())
        if not c:
            raise NotFoundError(f"Customer '{customer_id}' not found.")
        return c

    def find_by_phone(self, phone: str) -> dict | None:
        try:
            return self.db.find_one("customers", phone=validate_phone(phone))
        except ValidationError:
            return None

    def list(self) -> list[dict]:
        return sorted(self.db.all("customers"), key=lambda c: c["customer_id"])

    def search(self, keyword: str) -> list[dict]:
        k = str(keyword or "").strip().lower()
        digits = "".join(ch for ch in k if ch.isdigit())
        return [c for c in self.list() if k in c["name"].lower() or k in c["customer_id"].lower()
                or k in c["email"] or (len(digits) >= 4 and digits in c["phone"])
                or (k and k.upper() == c["id_number"])]

    def update(self, customer_id: str, **changes) -> dict:
        c = self.get(customer_id)
        clean = {}
        if changes.get("name"):
            clean["name"] = validate_name(changes["name"])
        if changes.get("phone"):
            clean["phone"] = validate_phone(changes["phone"])
            other = self.find_by_phone(clean["phone"])
            if other and other["customer_id"] != c["customer_id"]:
                raise ValidationError("Another guest has this phone number.")
        if changes.get("email") is not None and "email" in changes:
            clean["email"] = validate_email(changes["email"])
        if changes.get("id_type"):
            clean["id_type"], clean["id_number"] = validate_id_proof(changes["id_type"], changes.get("id_number"))
        for key, n in (("address", 200), ("nationality", 40)):
            if changes.get(key):
                clean[key] = validate_text(changes[key], key.title(), n)
        if not clean:
            raise ValidationError("Nothing to update.")
        log_activity(self.db, self.actor, "CUSTOMER_UPDATED", f"{c['customer_id']}: {', '.join(clean)}")
        return self.db.update("customers", "customer_id", c["customer_id"], clean)

    def delete(self, customer_id: str) -> None:
        c = self.get(customer_id)
        if self.db.find("bookings", customer_id=c["customer_id"]):
            raise HotelError("Guests with booking history cannot be deleted (invoices must be kept).")
        self.db.delete("customers", "customer_id", c["customer_id"])
        log_activity(self.db, self.actor, "CUSTOMER_DELETED", c["customer_id"])

    def history(self, customer_id: str) -> dict:
        c = self.get(customer_id)
        bookings = sorted(self.db.find("bookings", customer_id=c["customer_id"]),
                          key=lambda b: b["check_in"], reverse=True)
        stays = [b for b in bookings if b["status"] == "CHECKED_OUT"]
        return {"customer": c, "bookings": bookings, "stays": len(stays),
                "nights": sum(b["nights"] for b in stays),
                "total_spent": round(sum((b.get("invoice") or {}).get("grand_total", 0) for b in stays), 2),
                "cancellations": sum(b["status"] in ("CANCELLED", "NO_SHOW") for b in bookings)}
