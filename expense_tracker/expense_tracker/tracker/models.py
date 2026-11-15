"""Domain models (OOP layer). Each model serialises to / from a JSON dict."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class BaseRecord:
    """Common fields shared by every persisted record."""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class User(BaseRecord):
    username: str
    password_hash: str
    salt: str
    role: str = "user"          # "user" or "admin"
    full_name: str = ""
    active: bool = True
    created_at: str = field(default_factory=now_iso)
    last_login: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass
class Transaction(BaseRecord):
    username: str
    amount: float
    category: str
    date: str
    description: str = ""
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)


@dataclass
class Expense(Transaction):
    payment_mode: str = "Cash"


@dataclass
class Income(Transaction):
    """For income, `category` holds the income source."""


@dataclass
class Budget(BaseRecord):
    username: str
    month: str                  # YYYY-MM
    category: str               # a category name or "Overall"
    limit: float
    id: str = field(default_factory=new_id)


@dataclass
class SavingsGoal(BaseRecord):
    username: str
    name: str
    target_amount: float
    saved_amount: float = 0.0
    deadline: str | None = None
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)

    @property
    def progress(self) -> float:
        return min(100.0, self.saved_amount / self.target_amount * 100) if self.target_amount else 0.0

    @property
    def remaining(self) -> float:
        return max(0.0, round(self.target_amount - self.saved_amount, 2))

    @property
    def completed(self) -> bool:
        return self.saved_amount >= self.target_amount


@dataclass
class Bill(BaseRecord):
    username: str
    name: str
    amount: float
    due_date: str
    recurring: str = "none"     # none | monthly | yearly
    paid: bool = False
    id: str = field(default_factory=new_id)
