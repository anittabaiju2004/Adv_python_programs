"""Savings Management: goals with targets, deposits, withdrawals and progress."""
from __future__ import annotations

from datetime import date, datetime

from .config import DATE_FORMAT
from .database import JSONDatabase
from .exceptions import NotFoundError, ValidationError
from .models import SavingsGoal
from .validators import validate_amount, validate_date, validate_text


class SavingsManager:
    def __init__(self, db: JSONDatabase, username: str):
        self.db = db
        self.username = username

    def _raw(self, goal_id: str) -> dict:
        rec = self.db.find_one("savings", id=goal_id, username=self.username)
        if not rec:
            raise NotFoundError(f"No savings goal with id '{goal_id}'.")
        return rec

    def create_goal(self, name: str, target_amount, deadline: str | None = None,
                    initial: float = 0) -> SavingsGoal:
        name = validate_text(name, "Goal name", 1, 60)
        target = validate_amount(target_amount)
        dl = validate_date(deadline) if deadline else None
        if dl and dl < date.today().strftime(DATE_FORMAT):
            raise ValidationError("Deadline cannot be in the past.")
        saved = validate_amount(initial) if initial else 0.0
        goal = SavingsGoal(self.username, name, target, saved, dl)
        self.db.insert("savings", goal.to_dict())
        return goal

    def get(self, goal_id: str) -> SavingsGoal:
        return SavingsGoal.from_dict(self._raw(goal_id))

    def list_goals(self) -> list[SavingsGoal]:
        return [SavingsGoal.from_dict(r) for r in self.db.find("savings", username=self.username)]

    def deposit(self, goal_id: str, amount) -> SavingsGoal:
        goal = self.get(goal_id)
        goal.saved_amount = round(goal.saved_amount + validate_amount(amount), 2)
        self.db.update("savings", "id", goal_id, {"saved_amount": goal.saved_amount})
        return goal

    def withdraw(self, goal_id: str, amount) -> SavingsGoal:
        goal = self.get(goal_id)
        amount = validate_amount(amount)
        if amount > goal.saved_amount:
            raise ValidationError(f"Cannot withdraw {amount:.2f}; only {goal.saved_amount:.2f} saved.")
        goal.saved_amount = round(goal.saved_amount - amount, 2)
        self.db.update("savings", "id", goal_id, {"saved_amount": goal.saved_amount})
        return goal

    def delete_goal(self, goal_id: str) -> None:
        self._raw(goal_id)
        self.db.delete("savings", "id", goal_id)

    @staticmethod
    def monthly_required(goal: SavingsGoal) -> float | None:
        """Amount to save per month to hit the deadline (None if no deadline)."""
        if not goal.deadline or goal.completed:
            return None
        days = (datetime.strptime(goal.deadline, DATE_FORMAT).date() - date.today()).days
        months = max(1, round(days / 30.44))
        return round(goal.remaining / months, 2)
