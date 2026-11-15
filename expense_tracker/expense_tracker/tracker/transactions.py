"""Expense Management and Income Management modules.

Both share a generic ``TransactionManager`` that provides add / update /
delete / search / filter; the subclasses plug in their model and choices.
"""
from __future__ import annotations

from collections import defaultdict

from .config import EXPENSE_CATEGORIES, INCOME_SOURCES, PAYMENT_MODES
from .database import JSONDatabase
from .exceptions import NotFoundError, ValidationError
from .models import Expense, Income, Transaction
from .validators import validate_amount, validate_choice, validate_date, validate_text


class TransactionManager:
    collection: str = ""
    model: type[Transaction] = Transaction
    categories: list[str] = []
    category_label = "category"

    def __init__(self, db: JSONDatabase, username: str):
        self.db = db
        self.username = username

    # -------------------------------------------------------------- helpers
    def _validate(self, data: dict) -> dict:
        clean = {}
        if "amount" in data:
            clean["amount"] = validate_amount(data["amount"])
        if "category" in data:
            clean["category"] = validate_choice(data["category"], self.categories, self.category_label)
        if "date" in data:
            clean["date"] = validate_date(data["date"])
        if "description" in data:
            clean["description"] = validate_text(data["description"], "Description", 0, 200)
        return clean

    def _get_raw(self, record_id: str) -> dict:
        rec = self.db.find_one(self.collection, id=record_id, username=self.username)
        if not rec:
            raise NotFoundError(f"No {self.model.__name__.lower()} with id '{record_id}'.")
        return rec

    # ----------------------------------------------------------------- crud
    def add(self, amount, category, date=None, description="", **extra) -> Transaction:
        clean = self._validate({"amount": amount, "category": category,
                                "date": date, "description": description})
        clean.update(self._validate_extra(extra))
        record = self.model(username=self.username, **clean)
        self.db.insert(self.collection, record.to_dict())
        return record

    def _validate_extra(self, extra: dict) -> dict:
        return {}

    def get(self, record_id: str) -> Transaction:
        return self.model.from_dict(self._get_raw(record_id))

    def update(self, record_id: str, **changes) -> Transaction:
        self._get_raw(record_id)
        changes = {k: v for k, v in changes.items() if v not in (None, "")}
        if not changes:
            raise ValidationError("Nothing to update.")
        extra = {k: v for k, v in changes.items() if k not in ("amount", "category", "date", "description")}
        clean = self._validate(changes)
        clean.update(self._validate_extra(extra))
        updated = self.db.update(self.collection, "id", record_id, clean)
        return self.model.from_dict(updated)

    def delete(self, record_id: str) -> None:
        self._get_raw(record_id)
        self.db.delete(self.collection, "id", record_id)

    # --------------------------------------------------------------- query
    def list(self, start: str | None = None, end: str | None = None,
             category: str | None = None) -> list[Transaction]:
        recs = self.db.find(self.collection, username=self.username)
        if start:
            recs = [r for r in recs if r["date"] >= start]
        if end:
            recs = [r for r in recs if r["date"] <= end]
        if category:
            recs = [r for r in recs if r["category"].lower() == category.lower()]
        recs.sort(key=lambda r: (r["date"], r["created_at"]), reverse=True)
        return [self.model.from_dict(r) for r in recs]

    def search(self, keyword: str = "", min_amount: float | None = None,
               max_amount: float | None = None, **filters) -> list[Transaction]:
        keyword = (keyword or "").lower().strip()
        results = []
        for t in self.list(**filters):
            if keyword and keyword not in t.description.lower() and keyword not in t.category.lower():
                continue
            if min_amount is not None and t.amount < min_amount:
                continue
            if max_amount is not None and t.amount > max_amount:
                continue
            results.append(t)
        return results

    def for_month(self, month: str) -> list[Transaction]:
        return [t for t in self.list() if t.date.startswith(month)]

    def total(self, month: str | None = None, year: str | None = None,
              category: str | None = None) -> float:
        items = self.list(category=category)
        if month:
            items = [t for t in items if t.date.startswith(month)]
        if year:
            items = [t for t in items if t.date.startswith(str(year))]
        return round(sum(t.amount for t in items), 2)

    def by_category(self, month: str | None = None, year: str | None = None) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        prefix = month or (str(year) if year else "")
        for t in self.list():
            if t.date.startswith(prefix):
                totals[t.category] += t.amount
        return {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda kv: -kv[1])}

    def by_month(self, year: str) -> dict[str, float]:
        totals = {f"{year}-{m:02d}": 0.0 for m in range(1, 13)}
        for t in self.list():
            key = t.date[:7]
            if key in totals:
                totals[key] += t.amount
        return {k: round(v, 2) for k, v in totals.items()}


class ExpenseManager(TransactionManager):
    collection = "expenses"
    model = Expense
    categories = EXPENSE_CATEGORIES

    def add(self, amount, category, date=None, description="", payment_mode="Cash") -> Expense:
        return super().add(amount, category, date, description, payment_mode=payment_mode)

    def _validate_extra(self, extra: dict) -> dict:
        if "payment_mode" in extra:
            return {"payment_mode": validate_choice(extra["payment_mode"], PAYMENT_MODES, "payment mode")}
        return {}


class IncomeManager(TransactionManager):
    collection = "incomes"
    model = Income
    categories = INCOME_SOURCES
    category_label = "income source"
