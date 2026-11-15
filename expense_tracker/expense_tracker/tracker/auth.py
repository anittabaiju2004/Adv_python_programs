"""Authentication: registration, login and password hashing (PBKDF2-SHA256)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from .config import PBKDF2_ITERATIONS, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from .database import JSONDatabase
from .exceptions import AuthenticationError, ValidationError
from .models import User, now_iso
from .validators import validate_username, validate_password, validate_text


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return (hash_hex, salt_hex) using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


class AuthManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.ensure_default_admin()

    def ensure_default_admin(self) -> None:
        if not self.db.find("users", role="admin"):
            pw_hash, salt = hash_password(DEFAULT_ADMIN_PASSWORD)
            admin = User(DEFAULT_ADMIN_USERNAME, pw_hash, salt, role="admin", full_name="Administrator")
            self.db.insert("users", admin.to_dict())

    def get_user(self, username: str) -> User | None:
        data = self.db.find_one("users", username=username.lower().strip())
        return User.from_dict(data) if data else None

    def register(self, username: str, password: str, full_name: str = "", role: str = "user") -> User:
        username = validate_username(username)
        validate_password(password)
        full_name = validate_text(full_name, "Full name", 0, 60) if full_name else ""
        if role not in ("user", "admin"):
            raise ValidationError("Role must be 'user' or 'admin'.")
        if self.get_user(username):
            raise ValidationError(f"Username '{username}' is already taken.")
        pw_hash, salt = hash_password(password)
        user = User(username, pw_hash, salt, role=role, full_name=full_name)
        self.db.insert("users", user.to_dict())
        return user

    def login(self, username: str, password: str) -> User:
        user = self.get_user(username or "")
        if not user or not verify_password(password or "", user.password_hash, user.salt):
            raise AuthenticationError("Invalid username or password.")
        if not user.active:
            raise AuthenticationError("This account has been deactivated. Contact the admin.")
        user.last_login = now_iso()
        self.db.update("users", "username", user.username, {"last_login": user.last_login})
        return user

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        user = self.get_user(username)
        if not user or not verify_password(old_password, user.password_hash, user.salt):
            raise AuthenticationError("Current password is incorrect.")
        self.set_password(username, new_password)

    def set_password(self, username: str, new_password: str) -> None:
        validate_password(new_password)
        pw_hash, salt = hash_password(new_password)
        if not self.db.update("users", "username", username, {"password_hash": pw_hash, "salt": salt}):
            raise AuthenticationError(f"User '{username}' not found.")
