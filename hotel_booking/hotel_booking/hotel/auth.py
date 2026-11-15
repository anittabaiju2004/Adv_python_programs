"""Authentication: staff logins, password hashing, role permissions, lockout,
forced password change, and the activity log used by the admin panel."""
from __future__ import annotations

from .database import JSONDatabase
from .utils import (DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, PERMISSIONS, AuthenticationError,
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
                                     "shift": "General", "salary": 0.0, "join_date": now_str()[:10],
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
