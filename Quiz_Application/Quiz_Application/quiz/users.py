"""User Management: student self-registration, profiles and user search.
Staff account administration (roles, activation, resets) is in auth.UserManager."""
from __future__ import annotations

import re

from .auth import UserManager, log_activity
from .database import JSONDatabase
from .utils import (QuizError, NotFoundError, ValidationError, hash_password, now_str, validate_email,
                    validate_name, validate_password, validate_phone, validate_text)


class UserService(UserManager):
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        super().__init__(db, actor)

    def register_student(self, username: str, name: str, password: str, confirm: str, email: str = "",
                         phone: str = "", institution: str = "") -> dict:
        username = str(username or "").strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username):
            raise ValidationError("Username must be 3-30 lowercase letters, digits or underscores, starting with a letter.")
        if self.db.find_one("users", username=username):
            raise ValidationError(f"Username '{username}' is already taken.")
        validate_password(password)
        if password != confirm:
            raise ValidationError("Passwords do not match.")
        email = validate_email(email)
        if email and self.db.find_one("users", email=email):
            raise ValidationError("This email is already registered.")
        h, s = hash_password(password)
        user = {"username": username, "password_hash": h, "salt": s, "role": "student", "name": validate_name(name),
                "phone": validate_phone(phone, required=False), "email": email,
                "institution": validate_text(institution, "Institution", 80), "active": True,
                "must_change_password": False, "failed_attempts": 0, "created_at": now_str(), "last_login": None}
        self.db.insert("users", user)
        log_activity(self.db, username, "REGISTERED")
        return user

    def update_profile(self, username: str, name: str | None = None, email: str | None = None,
                       phone: str | None = None, institution: str | None = None) -> dict:
        u = self.get(username)
        changes = {}
        if name:
            changes["name"] = validate_name(name)
        if email is not None:
            changes["email"] = validate_email(email)
            other = self.db.find_one("users", email=changes["email"]) if changes["email"] else None
            if other and other["username"] != u["username"]:
                raise ValidationError("This email is already registered.")
        if phone is not None:
            changes["phone"] = validate_phone(phone, required=False)
        if institution is not None:
            changes["institution"] = validate_text(institution, "Institution", 80)
        if not changes:
            raise ValidationError("Nothing to update.")
        return self.db.update("users", "username", u["username"], changes)

    def students(self) -> list[dict]:
        return sorted(self.db.find("users", role="student"), key=lambda u: u["username"])

    def search(self, keyword: str) -> list[dict]:
        k = str(keyword or "").strip().lower()
        return [u for u in self.list() if not k or k in u["username"] or k in u["name"].lower() or k == u.get("email")]

    def delete_student(self, username: str) -> None:
        """Delete a student who has no quiz results (otherwise deactivate to keep history)."""
        u = self.get(username)
        if u["role"] != "student":
            raise QuizError("Only student accounts can be deleted; deactivate staff accounts instead.")
        if self.db.find("results", username=u["username"]):
            raise QuizError("This student has quiz results; deactivate the account instead of deleting.")
        self.db.delete_where("bookmarks", username=u["username"])
        self.db.delete("users", "username", u["username"])
        log_activity(self.db, self.actor, "USER_DELETED", u["username"])

    def get(self, username: str) -> dict:
        u = self.db.find_one("users", username=str(username or "").strip().lower())
        if not u:
            raise NotFoundError(f"User '{username}' not found.")
        return u
