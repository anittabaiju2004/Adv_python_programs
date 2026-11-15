"""Budget Management: monthly limits per category (or overall) with alerts."""
from __future__ import annotations

from dataclasses import dataclass

from .config import BUDGET_WARNING_THRESHOLD, EXPENSE_CATEGORIES
from .database import JSONDatabase
from .exceptions import NotFoundError
from .models import Budget
from .transactions import ExpenseManager
from .validators import validate_amount, validate_choice, validate_month

OVERALL = "Overall"


@dataclass
class BudgetStatus:
    budget: Budget
    spent: float

    @property
    def remaining(self) -> float:
        return round(self.budget.limit - self.spent, 2)

    @property
    def percent(self) -> float:
        return round(self.spent / self.budget.limit * 100, 1) if self.budget.limit else 0.0

    @property
    def level(self) -> str:
        ratio = self.spent / self.budget.limit if self.budget.limit else 0
        if ratio >= 1:
            return "EXCEEDED"
        if ratio >= BUDGET_WARNING_THRESHOLD:
            return "WARNING"
        return "OK"


class BudgetManager:
    def __init__(self, db: JSONDatabase, username: str):
        self.db = db
        self.username = username
        self.expenses = ExpenseManager(db, username)

    def set_budget(self, month: str, limit, category: str = OVERALL) -> Budget:
        """Create or replace the budget for a month/category pair."""
        month = validate_month(month)
        limit = validate_amount(limit)
        category = validate_choice(category, [OVERALL] + EXPENSE_CATEGORIES, "category")
        existing = self.db.find_one("budgets", username=self.username, month=month, category=category)
        if existing:
            self.db.update("budgets", "id", existing["id"], {"limit": limit})
            existing["limit"] = limit
            return Budget.from_dict(existing)
        budget = Budget(self.username, month, category, limit)
        self.db.insert("budgets", budget.to_dict())
        return budget

    def delete_budget(self, budget_id: str) -> None:
        if not self.db.find_one("budgets", id=budget_id, username=self.username):
            raise NotFoundError(f"No budget with id '{budget_id}'.")
        self.db.delete("budgets", "id", budget_id)

    def list_budgets(self, month: str | None = None) -> list[Budget]:
        match = {"username": self.username}
        if month:
            match["month"] = validate_month(month)
        recs = self.db.find("budgets", **match)
        recs.sort(key=lambda r: (r["month"], r["category"] != OVERALL, r["category"]))
        return [Budget.from_dict(r) for r in recs]

    def status(self, month: str) -> list[BudgetStatus]:
        month = validate_month(month)
        out = []
        for b in self.list_budgets(month):
            cat = None if b.category == OVERALL else b.category
            out.append(BudgetStatus(b, self.expenses.total(month=month, category=cat)))
        return out

    def alerts(self, month: str) -> list[str]:
        msgs = []
        for s in self.status(month):
            if s.level == "EXCEEDED":
                msgs.append(f"[!] {s.budget.category} budget EXCEEDED for {month}: "
                            f"spent {s.spent:.2f} of {s.budget.limit:.2f} ({s.percent}%)")
            elif s.level == "WARNING":
                msgs.append(f"[*] {s.budget.category} budget at {s.percent}% for {month}: "
                            f"{s.remaining:.2f} left")
        return msgs
