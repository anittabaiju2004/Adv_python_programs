"""Utilities module: configuration, exceptions, validation, hashing and helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import uuid
from datetime import date, datetime
from pathlib import Path

# ============================================================== configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("CB_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("CB_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("CB_REPORT_DIR", BASE_DIR / "reports"))

APP_NAME = "Contact Book Management System"
DEFAULT_CATEGORIES = ["Family", "Friends", "Work", "Business", "Emergency", "Other"]
FALLBACK_CATEGORY = "Other"
MAX_CATEGORIES = 20
BIRTHDAY_WINDOW_DAYS = 30
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class ContactBookError(Exception):
    """Base class for all application errors."""


class ValidationError(ContactBookError):
    pass


class NotFoundError(ContactBookError):
    pass


class DuplicateError(ContactBookError):
    pass


class AuthenticationError(ContactBookError):
    pass


class DatabaseError(ContactBookError):
    pass


class BackupError(ContactBookError):
    pass


# ================================================================== hashing
def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """PBKDF2-HMAC-SHA256 with a random 16-byte salt. Returns (hash_hex, salt_hex)."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    return hmac.compare_digest(hash_password(password or "", salt)[0], hashed)


# =============================================================== validation
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[^\W\d_][\w .'\-]*$", re.UNICODE)


def validate_name(value: str, field: str = "Name", required: bool = True, max_len: int = 50) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        if required:
            raise ValidationError(f"{field} is required.")
        return ""
    if len(text) > max_len or not NAME_RE.match(text):
        raise ValidationError(f"{field} must start with a letter and be at most {max_len} characters.")
    return text


def validate_phone(value: str, required: bool = True) -> str:
    """Normalise a phone number.

    * Indian mobiles (10 digits starting 6-9, optionally with 0/91/+91) -> +91XXXXXXXXXX
    * International numbers in E.164 form (+ and 7-15 digits) are kept
    * Indian landlines with STD code (0 + 9-10 digits) are kept as typed
    """
    raw = str(value or "").strip()
    if not raw:
        if required:
            raise ValidationError("Phone number is required.")
        return ""
    s = re.sub(r"[\s\-().]", "", raw)
    if s.startswith("00"):
        s = "+" + s[2:]
    m = re.fullmatch(r"(?:\+?91|0)?([6-9]\d{9})", s)
    if m:
        return "+91" + m.group(1)
    if re.fullmatch(r"\+[1-9]\d{6,14}", s):
        return s
    if re.fullmatch(r"0[1-9]\d{8,9}", s):
        return s
    raise ValidationError(f"'{raw}' is not a valid phone number. "
                          "Use a 10-digit mobile, a landline with STD code, or +<country code><number>.")


def validate_email(value: str, required: bool = False) -> str:
    email = str(value or "").strip().lower()
    if not email:
        if required:
            raise ValidationError("Email is required.")
        return ""
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValidationError(f"'{value}' is not a valid email address.")
    return email


def validate_date(value: str, field: str = "Date", required: bool = False, past_only: bool = True) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValidationError(f"{field} is required.")
        return ""
    try:
        d = datetime.strptime(text, DATE_FMT).date()
    except ValueError:
        raise ValidationError(f"{field} must be in YYYY-MM-DD format.")
    if past_only and d > date.today():
        raise ValidationError(f"{field} cannot be in the future.")
    return d.strftime(DATE_FMT)


def validate_text(value: str, field: str, max_len: int = 200) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    return text


def validate_username(value: str) -> str:
    name = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,30}", name):
        raise ValidationError("Username must be 3-30 characters: letters, digits or underscore.")
    return name


def validate_password(value: str) -> str:
    if not value or len(value) < 6 or value.isdigit() or value.isalpha():
        raise ValidationError("Password must be at least 6 characters and contain letters and digits.")
    return value


def validate_category_name(value: str) -> str:
    name = " ".join(str(value or "").split()).title()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 &\-]{0,24}", name):
        raise ValidationError("Category name must start with a letter (max 25 characters).")
    return name


# ================================================================== helpers
def new_id() -> str:
    return uuid.uuid4().hex[:8]


def now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_phone(phone: str) -> str:
    """+919876543210 -> +91 98765 43210 (other formats unchanged)."""
    if phone.startswith("+91") and len(phone) == 13:
        return f"+91 {phone[3:8]} {phone[8:]}"
    return phone


def days_until_birthday(birthday: str, today: date | None = None) -> int | None:
    if not birthday:
        return None
    today = today or date.today()
    b = datetime.strptime(birthday, DATE_FMT).date()
    for year in (today.year, today.year + 1):
        try:
            nxt = b.replace(year=year)
        except ValueError:            # 29 Feb in a non-leap year -> 28 Feb
            nxt = date(year, 2, 28)
        if nxt >= today:
            return (nxt - today).days
    return None


def age_on_next_birthday(birthday: str, today: date | None = None) -> int:
    """Age the person turns on their next birthday."""
    from datetime import timedelta
    today = today or date.today()
    born = datetime.strptime(birthday, DATE_FMT).date()
    return (today + timedelta(days=days_until_birthday(birthday, today))).year - born.year
