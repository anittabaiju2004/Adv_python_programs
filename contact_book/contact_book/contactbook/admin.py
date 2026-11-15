"""Admin module: user management and system statistics.

The admin manages accounts but does not read users' private contact
details — only counts and summaries.
"""
from __future__ import annotations

from collections import Counter

from .auth import AuthManager
from .database import JSONDatabase
from .models import User
from .utils import AuthenticationError, NotFoundError, ValidationError


class AdminManager:
    def __init__(self, db: JSONDatabase, admin: User):
        if not admin.is_admin:
            raise AuthenticationError("Administrator privileges required.")
        self.db = db
        self.admin = admin
        self.auth = AuthManager(db)

    def list_users(self) -> list[dict]:
        contacts = self.db.all("contacts")
        out = []
        for u in sorted(self.db.all("users"), key=lambda u: u["username"]):
            count = sum(1 for c in contacts if c["owner"] == u["username"] and not c.get("deleted"))
            out.append({**User.from_dict(u).to_dict(), "contact_count": count})
        return out

    def _get(self, username: str) -> User:
        user = self.auth.get_user(username)
        if not user:
            raise NotFoundError(f"User '{username}' not found.")
        return user

    def _not_self(self, username: str, action: str) -> None:
        if str(username).strip().lower() == self.admin.username:
            raise ValidationError(f"You cannot {action} your own account.")

    def set_active(self, username: str, active: bool) -> None:
        self._not_self(username, "deactivate" if not active else "change")
        user = self._get(username)
        self.db.update("users", "username", user.username, {"active": active})

    def set_role(self, username: str, role: str) -> None:
        self._not_self(username, "change the role of")
        if role not in ("user", "admin"):
            raise ValidationError("Role must be 'user' or 'admin'.")
        user = self._get(username)
        self.db.update("users", "username", user.username, {"role": role})

    def reset_password(self, username: str, new_password: str) -> None:
        self.auth.set_password(self._get(username).username, new_password)

    def delete_user(self, username: str) -> int:
        """Delete a user and all their contacts. Returns the number of contacts removed."""
        self._not_self(username, "delete")
        user = self._get(username)
        removed = self.db.delete_where("contacts", owner=user.username)
        self.db.delete("users", "username", user.username)
        return removed

    def system_stats(self) -> dict:
        users = self.db.all("users")
        contacts = self.db.all("contacts")
        active = [c for c in contacts if not c.get("deleted")]
        per_user = Counter(c["owner"] for c in active)
        return {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.get("active", True)),
            "admins": sum(1 for u in users if u["role"] == "admin"),
            "total_contacts": len(active),
            "contacts_in_recycle_bins": len(contacts) - len(active),
            "favourite_contacts": sum(1 for c in active if c.get("favorite")),
            "avg_contacts_per_user": round(len(active) / len(users), 1) if users else 0,
            "contacts_by_category": dict(Counter(c["category"] for c in active).most_common()),
            "top_users": per_user.most_common(5),
        }
