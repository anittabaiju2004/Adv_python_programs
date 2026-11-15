"""Staff Management: hotel staff records with their logins and roles."""
from __future__ import annotations

import re

from .auth import log_activity
from .database import JSONDatabase
from .utils import (ROLES, HotelError, NotFoundError, ValidationError, hash_password, now_str,
                    parse_date, temporary_password, validate_amount, validate_choice, validate_email,
                    validate_name, validate_phone)

SHIFTS = ["Morning (6-14)", "Evening (14-22)", "Night (22-6)", "General (9-18)"]


class StaffManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def add(self, username: str, name: str, role: str, phone: str, email: str = "",
            shift: str = "General (9-18)", salary=0, join_date: str | None = None) -> tuple[dict, str]:
        """Create a staff member and their login. Returns (staff, temporary_password)."""
        username = str(username or "").strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username):
            raise ValidationError("Username must be 3-30 lowercase letters, digits or underscores.")
        if self.db.find_one("users", username=username):
            raise ValidationError(f"Username '{username}' is already taken.")
        phone = validate_phone(phone)
        if self.db.find_one("users", phone=phone):
            raise ValidationError("Another staff member has this phone number.")
        temp = temporary_password()
        h, s = hash_password(temp)
        staff = {"username": username, "password_hash": h, "salt": s,
                 "role": validate_choice(role, ROLES, "role"), "name": validate_name(name), "phone": phone,
                 "email": validate_email(email), "shift": validate_choice(shift, SHIFTS, "shift"),
                 "salary": validate_amount(salary, "Salary", 0, 5_00_000) if salary else 0.0,
                 "join_date": parse_date(join_date or now_str()[:10]).isoformat(), "active": True,
                 "must_change_password": True, "failed_attempts": 0, "created_at": now_str(), "last_login": None}
        self.db.insert("users", staff)
        log_activity(self.db, self.actor, "STAFF_ADDED", f"{username} ({staff['role']})")
        return staff, temp

    def get(self, username: str) -> dict:
        u = self.db.find_one("users", username=str(username or "").strip().lower())
        if not u:
            raise NotFoundError(f"Staff '{username}' not found.")
        return u

    def list(self, include_inactive: bool = True) -> list[dict]:
        staff = self.db.all("users")
        if not include_inactive:
            staff = [s for s in staff if s["active"]]
        return sorted(staff, key=lambda s: (ROLES.index(s["role"]), s["name"]))

    def update(self, username: str, **changes) -> dict:
        s = self.get(username)
        clean = {}
        if changes.get("name"):
            clean["name"] = validate_name(changes["name"])
        if changes.get("phone"):
            clean["phone"] = validate_phone(changes["phone"])
            other = self.db.find_one("users", phone=clean["phone"])
            if other and other["username"] != s["username"]:
                raise ValidationError("Another staff member has this phone number.")
        if "email" in changes and changes["email"] is not None:
            clean["email"] = validate_email(changes["email"])
        if changes.get("shift"):
            clean["shift"] = validate_choice(changes["shift"], SHIFTS, "shift")
        if changes.get("salary") not in (None, ""):
            clean["salary"] = validate_amount(changes["salary"], "Salary", 0, 5_00_000)
        if changes.get("role"):
            role = validate_choice(changes["role"], ROLES, "role")
            if s["role"] == "admin" and role != "admin" and len([u for u in self.list(False) if u["role"] == "admin"]) == 1:
                raise HotelError("Cannot change the role of the only active admin.")
            clean["role"] = role
        if not clean:
            raise ValidationError("Nothing to update.")
        log_activity(self.db, self.actor, "STAFF_UPDATED", f"{s['username']}: {', '.join(clean)}")
        return self.db.update("users", "username", s["username"], clean)

    def set_active(self, username: str, active: bool) -> dict:
        s = self.get(username)
        if s["username"] == self.actor:
            raise HotelError("You cannot deactivate your own account.")
        if not active and s["role"] == "admin" and len([u for u in self.list(False) if u["role"] == "admin"]) == 1:
            raise HotelError("Cannot deactivate the only active admin.")
        log_activity(self.db, self.actor, "STAFF_ACTIVATED" if active else "STAFF_DEACTIVATED", s["username"])
        return self.db.update("users", "username", s["username"], {"active": active})

    def payroll_total(self) -> float:
        return round(sum(s["salary"] for s in self.list(False)), 2)
