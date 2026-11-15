"""Data models (OOP layer). Each model converts to / from a JSON dict."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

from .utils import DEFAULT_CATEGORIES, format_phone, new_id, now_str


@dataclass
class Record:
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class User(Record):
    username: str
    password_hash: str
    salt: str
    full_name: str = ""
    role: str = "user"                       # "user" | "admin"
    active: bool = True
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))
    created_at: str = field(default_factory=now_str)
    last_login: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass
class Contact(Record):
    owner: str                               # username the contact belongs to
    first_name: str
    phone: str
    last_name: str = ""
    alt_phone: str = ""
    email: str = ""
    company: str = ""
    job_title: str = ""
    address: str = ""
    birthday: str = ""                       # YYYY-MM-DD
    category: str = "Other"
    favorite: bool = False
    notes: str = ""
    deleted: bool = False                    # soft delete (recycle bin)
    deleted_at: str | None = None
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_str)
    updated_at: str = field(default_factory=now_str)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_phone(self) -> str:
        return format_phone(self.phone)

    def matches(self, keyword: str) -> bool:
        """Case-insensitive search across name, phones, email, company, notes and category."""
        k = keyword.lower().strip()
        digits = "".join(ch for ch in k if ch.isdigit())
        text = " ".join([self.full_name, self.email, self.company, self.job_title, self.address,
                         self.notes, self.category]).lower()
        if k in text:
            return True
        return bool(digits) and len(digits) >= 3 and (digits in self.phone or digits in self.alt_phone)
