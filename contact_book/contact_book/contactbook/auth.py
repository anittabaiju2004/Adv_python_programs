"""Authentication module: registration, login, password hashing and change."""
from __future__ import annotations

from .database import JSONDatabase
from .models import User
from .utils import (AuthenticationError, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, ValidationError,
                    hash_password, now_str, validate_name, validate_password, validate_username,
                    verify_password)

MAX_FAILED_LOGINS = 5


class AuthManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self._failed: dict[str, int] = {}        # failed attempts this session
        if not self.db.find("users", role="admin"):
            h, s = hash_password(DEFAULT_ADMIN_PASSWORD)
            self.db.insert("users", User(DEFAULT_ADMIN_USERNAME, h, s, "Administrator", "admin").to_dict())

    def get_user(self, username: str) -> User | None:
        data = self.db.find_one("users", username=str(username or "").strip().lower())
        return User.from_dict(data) if data else None

    def register(self, username: str, password: str, confirm: str, full_name: str = "",
                 role: str = "user") -> User:
        username = validate_username(username)
        validate_password(password)
        if password != confirm:
            raise ValidationError("Passwords do not match.")
        full_name = validate_name(full_name, "Full name", required=False, max_len=60)
        if role not in ("user", "admin"):
            raise ValidationError("Role must be 'user' or 'admin'.")
        if self.get_user(username):
            raise ValidationError(f"Username '{username}' is already taken.")
        h, s = hash_password(password)
        user = User(username, h, s, full_name, role)
        self.db.insert("users", user.to_dict())
        return user

    def login(self, username: str, password: str) -> User:
        key = str(username or "").strip().lower()
        if self._failed.get(key, 0) >= MAX_FAILED_LOGINS:
            raise AuthenticationError("Too many failed attempts. Restart the application to try again.")
        user = self.get_user(key)
        if not user or not verify_password(password, user.password_hash, user.salt):
            self._failed[key] = self._failed.get(key, 0) + 1
            raise AuthenticationError("Invalid username or password.")
        if not user.active:
            raise AuthenticationError("This account is deactivated. Please contact the administrator.")
        self._failed.pop(key, None)
        user.last_login = now_str()
        self.db.update("users", "username", user.username, {"last_login": user.last_login})
        return user

    def change_password(self, username: str, old: str, new: str, confirm: str) -> None:
        user = self.get_user(username)
        if not user or not verify_password(old, user.password_hash, user.salt):
            raise AuthenticationError("Current password is incorrect.")
        if new != confirm:
            raise ValidationError("New passwords do not match.")
        if new == old:
            raise ValidationError("New password must be different from the current one.")
        self.set_password(username, new)

    def set_password(self, username: str, new: str) -> None:
        validate_password(new)
        h, s = hash_password(new)
        if not self.db.update("users", "username", username, {"password_hash": h, "salt": s}):
            raise AuthenticationError(f"User '{username}' not found.")
