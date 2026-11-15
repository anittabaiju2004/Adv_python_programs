"""utils.py — bank configuration, exceptions, validation, PIN hashing and helpers."""
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
DATA_DIR = Path(os.environ.get("BANK_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("BANK_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("BANK_REPORT_DIR", BASE_DIR / "reports"))

BANK_NAME = "Python National Bank"
CURRENCY = "₹"

# Branch code -> (branch name, IFSC). The branch code prefixes account numbers.
BRANCHES = {
    "101": ("Thiruvananthapuram Main", "PYNB0000101"),
    "102": ("Kochi MG Road", "PYNB0000102"),
    "103": ("Kozhikode Beach Road", "PYNB0000103"),
    "104": ("Thrissur Round", "PYNB0000104"),
}

ACCOUNT_TYPES = ["Savings", "Current", "Salary"]
MIN_BALANCE = {"Savings": 1000.0, "Current": 5000.0, "Salary": 0.0}
MIN_OPENING_DEPOSIT = {"Savings": 1000.0, "Current": 5000.0, "Salary": 0.0}
MIN_AGE = 18

MAX_DEPOSIT_PER_TXN = 10_00_000.0
MAX_WITHDRAWAL_PER_TXN = 1_00_000.0
DAILY_WITHDRAWAL_LIMIT = 2_00_000.0
DAILY_TRANSFER_LIMIT = 10_00_000.0
# Transfer mode -> (minimum, maximum) per transaction
TRANSFER_MODES = {"IMPS": (1.0, 5_00_000.0), "NEFT": (1.0, 10_00_000.0), "RTGS": (2_00_000.0, 10_00_000.0)}
MAX_PIN_ATTEMPTS = 3                 # account is frozen after this many wrong PINs
MINI_STATEMENT_COUNT = 5

SAVINGS_INTEREST_RATE = 3.0          # % p.a., credited monthly by the admin

# Fixed deposit interest slabs: (min_months, max_months, annual_rate %)
FD_RATES = [(6, 11, 5.75), (12, 23, 6.8), (24, 59, 7.1), (60, 120, 6.5)]
FD_MIN_AMOUNT = 5000.0
FD_PREMATURE_PENALTY = 1.0           # % deducted from rate on early closure
SENIOR_CITIZEN_AGE = 60
SENIOR_CITIZEN_BONUS = 0.5           # extra % on FDs for senior citizens

# Loan type -> (annual rate %, max amount, max tenure months). EMI is reducing-balance.
LOAN_TYPES = {
    "Personal": (10.75, 15_00_000.0, 60),
    "Education": (9.0, 20_00_000.0, 120),
    "Home": (8.5, 75_00_000.0, 240),
    "Vehicle": (9.25, 15_00_000.0, 84),
    "Gold": (9.5, 5_00_000.0, 24),
}
LOAN_MIN = 10_000.0
LOAN_TENURE_MIN = 6
MAX_ACTIVE_LOANS = 2                 # active + pending applications

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class BankError(Exception):
    """Base class for all application errors."""


class ValidationError(BankError):
    pass


class AuthenticationError(BankError):
    pass


class AccountNotFoundError(BankError):
    pass


class AccountFrozenError(BankError):
    pass


class InsufficientFundsError(BankError):
    pass


class LimitExceededError(BankError):
    pass


class DatabaseError(BankError):
    pass


class BackupError(BankError):
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


PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_pan(pan: str) -> str:
    pan = str(pan or "").strip().upper()
    if not PAN_RE.match(pan):
        raise ValidationError("PAN must be in the format ABCDE1234F.")
    return pan


def validate_dob(dob: str, min_age: int = 18) -> str:
    try:
        d = datetime.strptime(str(dob).strip(), DATE_FMT).date()
    except ValueError:
        raise ValidationError("Date of birth must be in YYYY-MM-DD format.")
    age = age_on(d)
    if age < min_age:
        raise ValidationError(f"Customer must be at least {min_age} years old.")
    if age > 120:
        raise ValidationError("Please check the date of birth.")
    return d.strftime(DATE_FMT)


def validate_date(value: str, field: str = "Date") -> str:
    try:
        return datetime.strptime(str(value).strip(), DATE_FMT).strftime(DATE_FMT)
    except ValueError:
        raise ValidationError(f"{field} must be in YYYY-MM-DD format.")


def validate_month_str(value: str) -> str:
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise ValidationError("Month must be in YYYY-MM format.")


def age_on(dob: date | str, on: date | None = None) -> int:
    if isinstance(dob, str):
        dob = datetime.strptime(dob, DATE_FMT).date()
    on = on or date.today()
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


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
    return "XXXXXXX" + account_no[-4:]


def emi(principal: float, annual_rate: float, months: int) -> float:
    """Reducing-balance EMI:  P * r * (1+r)^n / ((1+r)^n - 1),  r = monthly rate."""
    r = annual_rate / 12 / 100
    if r == 0:
        return round(principal / months, 2)
    f = (1 + r) ** months
    return round(principal * r * f / (f - 1), 2)


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
