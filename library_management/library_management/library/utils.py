"""Utilities: library rules, exceptions, validation (incl. ISBN checksums), hashing and helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

# ============================================================== configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("LIB_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("LIB_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("LIB_REPORT_DIR", BASE_DIR / "reports"))

LIBRARY_NAME = "Ociuz Central Library"
LIBRARY_ADDRESS = "Technopark Campus, Thiruvananthapuram, Kerala"
LIBRARY_PHONE = "+91 471 2700123"
CURRENCY = "₹"

# Borrowing rules per member type
MEMBER_TYPES = {
    #            max books, loan days, fine per overdue day, membership fee
    "Student":  {"max_books": 3, "loan_days": 14, "fine_per_day": 2.0, "fee": 200.0},
    "Faculty":  {"max_books": 6, "loan_days": 30, "fine_per_day": 1.0, "fee": 0.0},
    "Staff":    {"max_books": 4, "loan_days": 21, "fine_per_day": 1.0, "fee": 0.0},
    "Public":   {"max_books": 2, "loan_days": 14, "fine_per_day": 5.0, "fee": 500.0},
}
MAX_RENEWALS = 2
MEMBERSHIP_DAYS = 365
FINE_BLOCK_LIMIT = 100.0          # unpaid fines above this block new issues / renewals
LOST_PROCESSING_FEE = 100.0       # added to the book price when a copy is lost
MAX_RESERVATIONS = 3              # active reservations per member
HOLD_DAYS = 3                     # days a returned copy is held for the next reserver
REFERENCE_LOAN = False            # reference-only copies can never be issued

CATEGORIES = ["Computer Science", "Engineering", "Mathematics", "Science", "Management", "Fiction",
              "Literature", "History", "Reference", "Self-Help", "Children", "Malayalam", "Other"]
LANGUAGES = ["English", "Malayalam", "Hindi", "Tamil", "Other"]
PAYMENT_MODES = ["Cash", "UPI", "Card"]

STAFF_ROLES = ["admin", "librarian", "assistant"]
ROLES = STAFF_ROLES                 # roles manageable from the admin panel
PERMISSIONS = {
    "admin":     {"*"},
    "librarian": {"books", "books.manage", "members", "members.manage", "circulation", "reservations",
                  "fines", "fines.waive", "reports", "desk"},
    "assistant": {"books", "members", "circulation", "reservations", "fines", "desk"},
    "member":    {"portal"},
}
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class LibraryError(Exception):
    """Base class for all application errors."""


class ValidationError(LibraryError):
    pass


class NotFoundError(LibraryError):
    pass


class AuthenticationError(LibraryError):
    pass


class PermissionDenied(LibraryError):
    pass


class CirculationError(LibraryError):
    """Issue / return / renew / reservation rule violations."""


class DatabaseError(LibraryError):
    pass


class BackupError(LibraryError):
    pass


# ================================================================== hashing
def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    return hmac.compare_digest(hash_password(password or "", salt)[0], hashed)


def temporary_password() -> str:
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(4)) + "-" + \
        "".join(secrets.choice(alphabet) for _ in range(4)) + str(secrets.randbelow(10))


# =============================================================== validation
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def validate_isbn(value: str, required: bool = False) -> str:
    """Validate ISBN-10 or ISBN-13 including the check digit. Returns the ISBN-13 form."""
    raw = re.sub(r"[\s\-]", "", str(value or "")).upper()
    if not raw:
        if required:
            raise ValidationError("ISBN is required.")
        return ""
    if re.fullmatch(r"\d{9}[\dX]", raw):
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(raw))
        if total % 11:
            raise ValidationError(f"'{value}' is not a valid ISBN-10 (check digit mismatch).")
        core = "978" + raw[:9]
        check = (10 - sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core)) % 10) % 10
        return core + str(check)
    if re.fullmatch(r"97[89]\d{10}", raw):
        if sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(raw)) % 10:
            raise ValidationError(f"'{value}' is not a valid ISBN-13 (check digit mismatch).")
        return raw
    raise ValidationError("ISBN must be 10 digits (last may be X) or 13 digits starting with 978/979.")


def validate_name(value: str, field: str = "Name", max_len: int = 60) -> str:
    text = " ".join(str(value or "").split())
    if len(text) < 2 or len(text) > max_len or not text[0].isalpha():
        raise ValidationError(f"{field} must be 2-{max_len} characters and start with a letter.")
    if any(ch.isdigit() for ch in text):
        raise ValidationError(f"{field} cannot contain digits.")
    return " ".join(w.capitalize() if w.islower() or w.isupper() else w for w in text.split())


def validate_title(value: str, field: str = "Title", max_len: int = 150) -> str:
    text = " ".join(str(value or "").split())
    if not text or len(text) > max_len:
        raise ValidationError(f"{field} is required (max {max_len} characters).")
    return text


def validate_phone(value: str, required: bool = True) -> str:
    s = re.sub(r"[\s\-()]", "", str(value or ""))
    if not s and not required:
        return ""
    m = re.fullmatch(r"(?:\+?91|0)?([6-9]\d{9})", s)
    if not m:
        raise ValidationError("Phone must be a valid 10-digit mobile number.")
    return m.group(1)


def validate_email(value: str, required: bool = False) -> str:
    email = str(value or "").strip().lower()
    if not email:
        if required:
            raise ValidationError("Email is required.")
        return ""
    if not EMAIL_RE.match(email):
        raise ValidationError(f"'{value}' is not a valid email address.")
    return email


def validate_amount(value, field: str = "Amount", lo: float = 0.01, hi: float = 1_00_000.0) -> float:
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if not lo <= amount <= hi:
        raise ValidationError(f"{field} must be between {lo:,.2f} and {hi:,.2f}.")
    return amount


def validate_int(value, field: str, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a whole number.")
    if not lo <= n <= hi:
        raise ValidationError(f"{field} must be between {lo} and {hi}.")
    return n


def validate_choice(value: str, choices, field: str) -> str:
    for c in choices:
        if str(value).strip().lower() == str(c).lower():
            return c
    raise ValidationError(f"Invalid {field}. Choose from: {', '.join(map(str, choices))}")


def validate_text(value: str, field: str, max_len: int = 200, required: bool = False) -> str:
    text = " ".join(str(value or "").split())
    if required and not text:
        raise ValidationError(f"{field} is required.")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    return text


def validate_password(value: str) -> str:
    if not value or len(value) < 6 or value.isdigit() or value.isalpha():
        raise ValidationError("Password must be at least 6 characters and contain letters and digits.")
    return value


def parse_date(value, field: str = "Date") -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), DATE_FMT).date()
    except ValueError:
        raise ValidationError(f"{field} must be in YYYY-MM-DD format.")


# ================================================================= helpers
def today() -> date:
    return date.today()


def now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


def money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def add_days(d, days: int) -> str:
    return (parse_date(d) + timedelta(days=days)).isoformat()


def days_between(a, b) -> int:
    return (parse_date(b) - parse_date(a)).days
