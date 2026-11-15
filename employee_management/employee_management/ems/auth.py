"""Authentication module: admin and employee logins, password hashing,
temporary passwords, forced password change and account lockout."""
from __future__ import annotations

from .database import JSONDatabase
from .utils import (AuthenticationError, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, NotFoundError,
                    ValidationError, hash_password, now_str, temporary_password, validate_password,
                    verify_password)

MAX_FAILED_ATTEMPTS = 5


class AuthManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        if not self.db.find("users", role="admin"):
            self._create(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, "admin",
                         must_change=False)

    def _create(self, username: str, password: str, role: str, emp_id: str | None = None,
                must_change: bool = True) -> dict:
        h, s = hash_password(password)
        user = {"username": username.lower(), "password_hash": h, "salt": s, "role": role, "emp_id": emp_id,
                "active": True, "must_change_password": must_change, "failed_attempts": 0,
                "created_at": now_str(), "last_login": None}
        self.db.insert("users", user)
        return user

    def get(self, username: str) -> dict | None:
        return self.db.find_one("users", username=str(username or "").strip().lower())

    # ----------------------------------------------------------- accounts
    def create_admin(self, username: str, password: str) -> dict:
        username = str(username or "").strip().lower()
        if not username.isidentifier() or not 3 <= len(username) <= 30:
            raise ValidationError("Username must be 3-30 letters, digits or underscores.")
        if self.get(username):
            raise ValidationError(f"Username '{username}' already exists.")
        validate_password(password)
        return self._create(username, password, "admin", must_change=False)

    def create_employee_login(self, emp_id: str) -> str:
        """Create a login for an employee (username = employee ID). Returns the
        one-time password; the employee must change it on first login."""
        if self.get(emp_id):
            raise ValidationError(f"A login for {emp_id} already exists.")
        password = temporary_password()
        self._create(emp_id, password, "employee", emp_id=emp_id.upper())
        return password

    def reset_password(self, username: str) -> str:
        """Admin reset: issue a new temporary password and unlock the account."""
        user = self.get(username)
        if not user:
            raise NotFoundError(f"No login '{username}'.")
        password = temporary_password()
        h, s = hash_password(password)
        self.db.update("users", "username", user["username"],
                       {"password_hash": h, "salt": s, "must_change_password": True, "failed_attempts": 0})
        return password

    def set_active(self, username: str, active: bool) -> None:
        if not self.db.update("users", "username", str(username).lower(), {"active": active}):
            raise NotFoundError(f"No login '{username}'.")

    def delete_login(self, username: str) -> None:
        self.db.delete("users", "username", str(username).lower())

    # -------------------------------------------------------------- login
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
