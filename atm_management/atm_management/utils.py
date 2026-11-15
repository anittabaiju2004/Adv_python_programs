"""utils.py — configuration, exceptions, validation, PIN hashing and helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import date, datetime
from pathlib import Path

# ============================================================== configuration
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("ATM_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("ATM_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("ATM_REPORT_DIR", BASE_DIR / "reports"))

BANK_NAME = "PyBank ATM"
CURRENCY = "₹"
ACCOUNT_TYPES = ["Savings", "Current"]
MIN_BALANCE = {"Savings": 500.0, "Current": 1000.0}
MIN_OPENING_DEPOSIT = 500.0

WITHDRAWAL_MULTIPLE = 100            # ATM dispenses notes in multiples of 100
MAX_WITHDRAWAL_PER_TXN = 20_000.0
DAILY_WITHDRAWAL_LIMIT = 50_000.0
MAX_DEPOSIT_PER_TXN = 2_00_000.0
DAILY_TRANSFER_LIMIT = 1_00_000.0
MAX_PIN_ATTEMPTS = 3                 # account is frozen after this many wrong PINs
MINI_STATEMENT_COUNT = 5

# Fixed deposit interest slabs: (min_months, max_months, annual_rate %)
FD_RATES = [(6, 11, 5.5), (12, 23, 6.5), (24, 59, 7.0), (60, 120, 7.25)]
FD_MIN_AMOUNT = 1000.0
FD_PREMATURE_PENALTY = 1.0           # % deducted from rate on early closure

LOAN_TYPES = {"Personal": 11.0, "Education": 8.5, "Home": 8.0, "Vehicle": 9.5}
LOAN_MIN, LOAN_MAX = 10_000.0, 10_00_000.0
LOAN_TENURE_MIN, LOAN_TENURE_MAX = 6, 240
MAX_ACTIVE_LOANS = 2

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class ATMError(Exception):
    """Base class for all application errors."""


class ValidationError(ATMError):
    pass


class AuthenticationError(ATMError):
    pass


class AccountNotFoundError(ATMError):
    pass


class AccountFrozenError(ATMError):
    pass


class InsufficientFundsError(ATMError):
    pass


class LimitExceededError(ATMError):
    pass


class DatabaseError(ATMError):
    pass


class BackupError(ATMError):
    pass


# ================================================================== hashing
def hash_secret(secret: str, salt: str | None = None) -> tuple[str, str]:
    """PBKDF2-HMAC-SHA256 hash of a PIN/password. Returns (hash_hex, salt_hex)."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", str(secret).encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_secret(secret: str, hashed: str, salt: str) -> bool:
    return hmac.compare_digest(hash_secret(secret, salt)[0], hashed)


# =============================================================== validation
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")         # Indian 10-digit mobile
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,59}$")


def validate_name(name: str) -> str:
    name = " ".join(str(name or "").split())
    if not NAME_RE.match(name):
        raise ValidationError("Name must be 2-60 letters (spaces, . ' - allowed).")
    return name.title()


def validate_phone(phone: str) -> str:
    phone = re.sub(r"[\s-]", "", str(phone or ""))
    if phone.startswith("+91"):
        phone = phone[3:]
    if not PHONE_RE.match(phone):
        raise ValidationError("Phone must be a valid 10-digit mobile number starting with 6-9.")
    return phone


def validate_email(email: str) -> str:
    email = str(email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError(f"'{email}' is not a valid email address.")
    return email


def validate_pin(pin: str) -> str:
    pin = str(pin or "").strip()
    if not (pin.isdigit() and len(pin) == 4):
        raise ValidationError("PIN must be exactly 4 digits.")
    if len(set(pin)) == 1 or pin in ("1234", "4321", "0123", "9876"):
        raise ValidationError("PIN is too easy to guess. Avoid repeated or sequential digits.")
    return pin


def validate_amount(value, field: str = "Amount") -> float:
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if amount <= 0:
        raise ValidationError(f"{field} must be greater than zero.")
    return amount


def validate_positive_int(value, field: str, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a whole number.")
    if not lo <= n <= hi:
        raise ValidationError(f"{field} must be between {lo} and {hi}.")
    return n


def validate_choice(value: str, choices, field: str) -> str:
    for c in choices:
        if str(value).strip().lower() == c.lower():
            return c
    raise ValidationError(f"Invalid {field}. Choose from: {', '.join(choices)}")


# ================================================================== helpers
def now_str() -> str:
    return datetime.now().strftime(DATETIME_FMT)


def today() -> date:
    return date.today()


def money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def new_id(prefix: str) -> str:
    """Unique, sortable-ish id like TXN20261114121530A1B2."""
    return f"{prefix}{datetime.now():%Y%m%d%H%M%S}{secrets.token_hex(2).upper()}"


def mask_account(account_no: str) -> str:
    return "XXXXXX" + account_no[-4:]


def simple_interest(principal: float, rate: float, years: float) -> tuple[float, float]:
    """Return (interest, maturity_amount) using SI = P * R * T / 100."""
    principal = validate_amount(principal, "Principal")
    if rate is None or float(rate) <= 0 or float(rate) > 50:
        raise ValidationError("Interest rate must be between 0 and 50 %.")
    if years is None or float(years) <= 0 or float(years) > 50:
        raise ValidationError("Duration must be between 0 and 50 years.")
    interest = round(principal * float(rate) * float(years) / 100, 2)
    return interest, round(principal + interest, 2)


def add_months(d: date, months: int) -> date:
    import calendar
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
