"""Authentication: user logins, password hashing, role permissions, lockout,
forced password change, user management and the activity log."""
from __future__ import annotations

from .database import JSONDatabase
import re

from .utils import (DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, PERMISSIONS, ROLES, AuthenticationError,
                    SMSError, validate_choice, validate_email, validate_name, validate_phone,
                    NotFoundError, PermissionDenied, ValidationError, hash_password, now_str,
                    temporary_password, validate_password, verify_password)

MAX_FAILED_ATTEMPTS = 5


def can(user: dict | None, permission: str) -> bool:
    if not user:
        return False
    perms = PERMISSIONS.get(user.get("role"), set())
    return "*" in perms or permission in perms


def require(user: dict | None, permission: str) -> None:
    if not can(user, permission):
        raise PermissionDenied(f"Your role ({(user or {}).get('role', 'guest')}) cannot do this.")


def log_activity(db: JSONDatabase, user: str, action: str, details: str = "") -> None:
    db.insert("activity", {"at": now_str(), "user": user, "action": action, "details": details[:200]})


class AuthManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        if not self.db.find("users", role="admin"):
            h, s = hash_password(DEFAULT_ADMIN_PASSWORD)
            self.db.insert("users", {"username": DEFAULT_ADMIN_USERNAME, "password_hash": h, "salt": s,
                                     "role": "admin", "name": "Administrator", "phone": "", "email": "",
                                     "active": True, "must_change_password": False, "failed_attempts": 0,
                                     "created_at": now_str(), "last_login": None})

    def get(self, username: str) -> dict | None:
        return self.db.find_one("users", username=str(username or "").strip().lower())

    def login(self, username: str, password: str) -> dict:
        user = self.get(username)
        if not user:
            raise AuthenticationError("Invalid username or password.")
        if user["failed_attempts"] >= MAX_FAILED_ATTEMPTS:
            raise AuthenticationError("Account locked after too many failed attempts. Ask the admin to reset it.")
        if not verify_password(password, user["password_hash"], user["salt"]):
            attempts = user["failed_attempts"] + 1
            self.db.update("users", "username", user["username"], {"failed_attempts": attempts})
            left = MAX_FAILED_ATTEMPTS - attempts
            raise AuthenticationError("Invalid username or password." +
                                      (f" {left} attempt(s) left." if left else " Account is now locked."))
        if not user["active"]:
            raise AuthenticationError("This account is disabled.")
        changes = {"failed_attempts": 0, "last_login": now_str()}
        self.db.update("users", "username", user["username"], changes)
        log_activity(self.db, user["username"], "LOGIN")
        return {**user, **changes}

    def change_password(self, username: str, old: str, new: str, confirm: str) -> None:
        user = self.get(username)
        if not user or not verify_password(old, user["password_hash"], user["salt"]):
            raise AuthenticationError("Current password is incorrect.")
        if new != confirm:
            raise ValidationError("New passwords do not match.")
        if new == old:
            raise ValidationError("New password must be different from the current one.")
        validate_password(new)
        h, s = hash_password(new)
        self.db.update("users", "username", user["username"],
                       {"password_hash": h, "salt": s, "must_change_password": False})
        log_activity(self.db, user["username"], "PASSWORD_CHANGED")

    def reset_password(self, username: str, by: str) -> str:
        user = self.get(username)
        if not user:
            raise NotFoundError(f"No user '{username}'.")
        temp = temporary_password()
        h, s = hash_password(temp)
        self.db.update("users", "username", user["username"],
                       {"password_hash": h, "salt": s, "must_change_password": True, "failed_attempts": 0})
        log_activity(self.db, by, "PASSWORD_RESET", user["username"])
        return temp


class UserManager:
    """Admin-only management of user accounts."""

    def __init__(self, db: JSONDatabase, actor: str = "admin"):
        self.db = db
        self.actor = actor

    def list(self) -> list[dict]:
        """Staff accounts only (member logins are managed from Member Management)."""
        return sorted((u for u in self.db.all("users") if u["role"] in ROLES),
                      key=lambda u: (ROLES.index(u["role"]), u["username"]))

    def get(self, username: str) -> dict:
        u = self.db.find_one("users", username=str(username or "").strip().lower())
        if not u:
            raise NotFoundError(f"User '{username}' not found.")
        return u

    def add(self, username: str, name: str, role: str, phone: str = "", email: str = "") -> tuple[dict, str]:
        username = str(username or "").strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username):
            raise ValidationError("Username must be 3-30 lowercase letters, digits or underscores.")
        if self.db.find_one("users", username=username):
            raise ValidationError(f"Username '{username}' is already taken.")
        temp = temporary_password()
        h, s = hash_password(temp)
        user = {"username": username, "password_hash": h, "salt": s, "role": validate_choice(role, ROLES, "role"),
                "name": validate_name(name), "phone": validate_phone(phone, required=False),
                "email": validate_email(email), "active": True, "must_change_password": True,
                "failed_attempts": 0, "created_at": now_str(), "last_login": None}
        self.db.insert("users", user)
        log_activity(self.db, self.actor, "USER_ADDED", f"{username} ({user['role']})")
        return user, temp

    def _active_admins(self) -> int:
        return sum(1 for u in self.db.all("users") if u["role"] == "admin" and u["active"])

    def set_role(self, username: str, role: str) -> dict:
        u = self.get(username)
        role = validate_choice(role, ROLES, "role")
        if u["role"] == "admin" and role != "admin" and self._active_admins() == 1:
            raise SMSError("Cannot change the role of the only active admin.")
        log_activity(self.db, self.actor, "USER_ROLE", f"{u['username']}: {u['role']} -> {role}")
        return self.db.update("users", "username", u["username"], {"role": role})

    def set_active(self, username: str, active: bool) -> dict:
        u = self.get(username)
        if u["username"] == self.actor:
            raise SMSError("You cannot deactivate your own account.")
        if not active and u["role"] == "admin" and self._active_admins() == 1:
            raise SMSError("Cannot deactivate the only active admin.")
        log_activity(self.db, self.actor, "USER_ACTIVATED" if active else "USER_DEACTIVATED", u["username"])
        return self.db.update("users", "username", u["username"], {"active": active})
