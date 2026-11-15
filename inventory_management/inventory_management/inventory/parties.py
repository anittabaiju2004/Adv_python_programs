"""Shared base for suppliers and customers (trading parties): GSTIN-aware
records with state detection, search, update and delete protection."""
from __future__ import annotations

from .auth import log_activity
from .database import JSONDatabase
from .utils import (BUSINESS_STATE, InventoryError, NotFoundError, ValidationError, now_str, validate_email,
                    validate_gstin, validate_name, validate_phone, validate_state, validate_text)


class PartyManager:
    collection = ""          # "suppliers" / "customers"
    id_field = ""            # "supplier_id" / "customer_id"
    prefix = ""              # "SUP" / "CUST"
    label = ""               # "Supplier" / "Customer"
    phone_required = True

    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def _next_id(self) -> str:
        nums = [int(r[self.id_field][len(self.prefix):]) for r in self.db.all(self.collection)]
        return f"{self.prefix}{(max(nums) + 1) if nums else 1:04d}"

    def _clean(self, data: dict, current: dict | None = None) -> dict:
        out = {}
        if "name" in data:
            out["name"] = validate_name(data["name"], f"{self.label} name")
        if "contact_person" in data:
            out["contact_person"] = validate_text(data["contact_person"], "Contact person", 60)
        if "phone" in data:
            out["phone"] = validate_phone(data["phone"], required=self.phone_required)
        if "email" in data:
            out["email"] = validate_email(data["email"])
        if "address" in data:
            out["address"] = validate_text(data["address"], "Address", 200)
        if "gstin" in data or "state" in data:
            gstin, gst_state = validate_gstin(data.get("gstin", current.get("gstin") if current else ""))
            state = validate_state(data["state"]) if data.get("state") else (current or {}).get("state") or BUSINESS_STATE
            if gst_state:
                if data.get("state") and state != gst_state:
                    raise ValidationError(f"GSTIN belongs to {gst_state}, not {state}.")
                state = gst_state
            out["gstin"], out["state"] = gstin, state
        for key in ("phone", "gstin"):
            if out.get(key):
                clash = next((r for r in self.db.all(self.collection) if r.get(key) == out[key]
                              and (not current or r[self.id_field] != current[self.id_field])), None)
                if clash:
                    raise ValidationError(f"{key.upper() if key == 'gstin' else 'Phone'} already belongs to "
                                          f"{clash[self.id_field]} ({clash['name']}).")
        return out

    def add(self, name: str, phone: str = "", email: str = "", gstin: str = "", state: str = "",
            address: str = "", contact_person: str = "") -> dict:
        clean = self._clean({"name": name, "phone": phone, "email": email, "gstin": gstin, "state": state,
                             "address": address, "contact_person": contact_person})
        rec = {self.id_field: self._next_id(), **clean, "active": True, "created_at": now_str()}
        self.db.insert(self.collection, rec)
        log_activity(self.db, self.actor, f"{self.label.upper()}_ADDED", f"{rec[self.id_field]} {rec['name']}")
        return rec

    def get(self, party_id: str) -> dict:
        r = self.db.find_one(self.collection, **{self.id_field: str(party_id or "").strip().upper()})
        if not r:
            raise NotFoundError(f"{self.label} '{party_id}' not found.")
        return r

    def list(self, include_inactive: bool = False) -> list[dict]:
        rs = self.db.all(self.collection)
        if not include_inactive:
            rs = [r for r in rs if r["active"]]
        return sorted(rs, key=lambda r: r[self.id_field])

    def search(self, keyword: str) -> list[dict]:
        k = str(keyword or "").strip().lower()
        digits = "".join(c for c in k if c.isdigit())
        return [r for r in self.list(include_inactive=True)
                if not k or k in r["name"].lower() or k == r[self.id_field].lower() or k.upper() == r["gstin"]
                or (len(digits) >= 4 and digits in r["phone"]) or k in r.get("contact_person", "").lower()]

    def update(self, party_id: str, **changes) -> dict:
        r = self.get(party_id)
        changes = {k: v for k, v in changes.items() if v is not None}
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = self._clean(changes, r)
        log_activity(self.db, self.actor, f"{self.label.upper()}_UPDATED", f"{r[self.id_field]}: {', '.join(clean)}")
        return self.db.update(self.collection, self.id_field, r[self.id_field], clean)

    def set_active(self, party_id: str, active: bool) -> dict:
        r = self.get(party_id)
        return self.db.update(self.collection, self.id_field, r[self.id_field], {"active": active})

    def _transactions(self, party_id: str) -> list[dict]:
        raise NotImplementedError

    def delete(self, party_id: str) -> None:
        r = self.get(party_id)
        if self._transactions(r[self.id_field]):
            raise InventoryError(f"{r['name']} has transactions; deactivate instead of deleting.")
        self.db.delete(self.collection, self.id_field, r[self.id_field])
        log_activity(self.db, self.actor, f"{self.label.upper()}_DELETED", r[self.id_field])
