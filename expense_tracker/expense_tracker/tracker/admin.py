"""Admin module: user management and system-wide statistics."""
from __future__ import annotations

from .auth import AuthManager
from .database import JSONDatabase
from .exceptions import AuthenticationError, NotFoundError, ValidationError
from .models import User


class AdminManager:
    def __init__(self, db: JSONDatabase, admin: User):
        if not admin.is_admin:
            raise AuthenticationError("Admin privileges required.")
        self.db = db
        self.admin = admin
        self.auth = AuthManager(db)

    def list_users(self) -> list[User]:
        return sorted((User.from_dict(u) for u in self.db.all("users")), key=lambda u: u.username)

    def _get(self, username: str) -> User:
        user = self.auth.get_user(username)
        if not user:
            raise NotFoundError(f"User '{username}' not found.")
        return user

    def _guard_self(self, username: str, action: str) -> None:
        if username.lower() == self.admin.username:
            raise ValidationError(f"You cannot {action} your own account.")

    def set_active(self, username: str, active: bool) -> None:
        self._guard_self(username, "deactivate" if not active else "modify")
        user = self._get(username)
        self.db.update("users", "username", user.username, {"active": active})

    def set_role(self, username: str, role: str) -> None:
        self._guard_self(username, "change the role of")
        if role not in ("user", "admin"):
            raise ValidationError("Role must be 'user' or 'admin'.")
        user = self._get(username)
        self.db.update("users", "username", user.username, {"role": role})

    def reset_password(self, username: str, new_password: str) -> None:
        user = self._get(username)
        self.auth.set_password(user.username, new_password)

    def delete_user(self, username: str) -> dict:
        """Delete a user and all of their data. Returns counts removed per collection."""
        self._guard_self(username, "delete")
        user = self._get(username)
        removed = {c: self.db.delete_where(c, username=user.username)
                   for c in ("expenses", "incomes", "budgets", "savings", "bills")}
        self.db.delete("users", "username", user.username)
        return removed

    def system_stats(self) -> dict:
        users = self.db.all("users")
        expenses = self.db.all("expenses")
        incomes = self.db.all("incomes")
        per_user = {}
        for u in users:
            name = u["username"]
            per_user[name] = {
                "expenses": round(sum(e["amount"] for e in expenses if e["username"] == name), 2),
                "incomes": round(sum(i["amount"] for i in incomes if i["username"] == name), 2),
                "transactions": sum(1 for e in expenses if e["username"] == name)
                                + sum(1 for i in incomes if i["username"] == name),
            }
        return {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.get("active", True)),
            "admins": sum(1 for u in users if u["role"] == "admin"),
            "total_expense_records": len(expenses),
            "total_income_records": len(incomes),
            "total_expense_amount": round(sum(e["amount"] for e in expenses), 2),
            "total_income_amount": round(sum(i["amount"] for i in incomes), 2),
            "per_user": per_user,
        }
