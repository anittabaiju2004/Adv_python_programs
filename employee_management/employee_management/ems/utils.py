"""Utilities module: configuration, exceptions, validation, hashing and date helpers."""
from __future__ import annotations

import calendar
import hashlib
import hmac
import os
import re
import secrets
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

# ============================================================== configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("EMS_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("EMS_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("EMS_REPORT_DIR", BASE_DIR / "reports"))

COMPANY_NAME = "Ociuz Technologies Pvt. Ltd."
COMPANY_ADDRESS = "Technopark, Thiruvananthapuram, Kerala"
CURRENCY = "₹"

EMP_ID_PREFIX = "EMP"
EMP_ID_START = 1001
EMPLOYMENT_TYPES = ["Permanent", "Contract", "Intern"]
GENDERS = ["Male", "Female", "Other"]
MIN_AGE, MAX_AGE = 18, 60
MIN_BASIC, MAX_BASIC = 5_000.0, 10_00_000.0

DEFAULT_DEPARTMENTS = {
    "Engineering": ["Software Engineer", "Senior Software Engineer", "Tech Lead", "QA Engineer"],
    "Human Resources": ["HR Executive", "HR Manager"],
    "Finance": ["Accountant", "Finance Manager"],
    "Sales & Marketing": ["Sales Executive", "Marketing Manager"],
    "Operations": ["Operations Executive", "Office Administrator"],
}

# Attendance
OFFICE_START = "09:30"                 # check-in after this time is marked late
HALF_DAY_HOURS = 4.0                   # fewer hours than this on check-out -> half day
WEEKLY_OFF = {6}                       # Sunday (Monday = 0)
HOLIDAYS = {                           # company holidays (YYYY-MM-DD: name)
    "2026-01-26": "Republic Day", "2026-04-14": "Vishu", "2026-08-15": "Independence Day",
    "2026-08-26": "Thiruvonam", "2026-10-02": "Gandhi Jayanti", "2026-12-25": "Christmas",
    "2027-01-26": "Republic Day",
}
ATTENDANCE_STATUSES = ["PRESENT", "ABSENT", "HALF_DAY", "LEAVE"]

# Leave types -> days per calendar year (None = unlimited, unpaid)
LEAVE_TYPES = {"Casual": 12, "Sick": 10, "Earned": 15, "Loss of Pay": None}

# Payroll (all % of basic unless noted)
HRA_PERCENT = 40.0
DA_PERCENT = 10.0
CONVEYANCE = 1600.0                    # fixed per month
MEDICAL_ALLOWANCE = 1250.0             # fixed per month
PF_PERCENT = 12.0                      # employee share, on basic
PF_WAGE_CEILING = 15_000.0             # PF is calculated on basic up to this ceiling
ESI_PERCENT = 0.75                     # on gross, only if gross <= ESI_LIMIT
ESI_LIMIT = 21_000.0
PROFESSIONAL_TAX = [(0, 11_999, 0.0), (12_000, 17_999, 120.0), (18_000, float("inf"), 208.0)]  # monthly slabs

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class EMSError(Exception):
    """Base class for all application errors."""


class ValidationError(EMSError):
    pass


class NotFoundError(EMSError):
    pass


class AuthenticationError(EMSError):
    pass


class PermissionDenied(EMSError):
    pass


class DatabaseError(EMSError):
    pass


class BackupError(EMSError):
    pass


# ================================================================== hashing
def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    return hmac.compare_digest(hash_password(password or "", salt)[0], hashed)


def temporary_password() -> str:
    """Readable one-time password, e.g. 'Kx7m-42Qa'."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(4)) + "-" + \
        "".join(secrets.choice(alphabet) for _ in range(4)) + str(secrets.randbelow(10))


# =============================================================== validation
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,59}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_name(value: str, field: str = "Name") -> str:
    text = " ".join(str(value or "").split())
    if not NAME_RE.match(text):
        raise ValidationError(f"{field} must be 2-60 letters (spaces, . ' - allowed).")
    # Fix words typed all-lower or ALL-UPPER; keep deliberate casing like "McDonald".
    return " ".join(w.capitalize() if w.islower() or w.isupper() else w for w in text.split())


def validate_phone(value: str) -> str:
    s = re.sub(r"[\s\-()]", "", str(value or ""))
    m = re.fullmatch(r"(?:\+?91|0)?([6-9]\d{9})", s)
    if not m:
        raise ValidationError("Phone must be a valid 10-digit Indian mobile number.")
    return m.group(1)


def validate_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError(f"'{value}' is not a valid email address.")
    return email


def validate_pan(value: str, required: bool = False) -> str:
    pan = str(value or "").strip().upper()
    if not pan and not required:
        return ""
    if not PAN_RE.match(pan):
        raise ValidationError("PAN must be in the format ABCDE1234F.")
    return pan


def parse_date(value, field: str = "Date") -> date:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), DATE_FMT).date()
    except ValueError:
        raise ValidationError(f"{field} must be in YYYY-MM-DD format.")


def validate_date(value, field: str = "Date", allow_future: bool = True) -> str:
    d = parse_date(value, field)
    if not allow_future and d > date.today():
        raise ValidationError(f"{field} cannot be in the future.")
    return d.strftime(DATE_FMT)


def validate_month(value: str) -> str:
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise ValidationError("Month must be in YYYY-MM format.")


def validate_amount(value, field: str = "Amount", lo: float = 0.01, hi: float = float("inf")) -> float:
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if not lo <= amount <= hi:
        raise ValidationError(f"{field} must be between {money(lo)} and {money(hi)}.")
    return amount


def validate_choice(value: str, choices, field: str) -> str:
    for c in choices:
        if str(value).strip().lower() == c.lower():
            return c
    raise ValidationError(f"Invalid {field}. Choose from: {', '.join(choices)}")


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


# ============================================================ date helpers
def age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def is_working_day(d: date) -> bool:
    return d.weekday() not in WEEKLY_OFF and d.strftime(DATE_FMT) not in HOLIDAYS


def working_days_between(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if is_working_day(d):
            days.append(d)
        d += timedelta(days=1)
    return days


def month_bounds(month: str) -> tuple[date, date]:
    y, m = map(int, month.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def working_days_in_month(month: str) -> list[date]:
    return working_days_between(*month_bounds(month))


# ================================================================= helpers
def new_id(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex[:8].upper()


def now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


def money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def rupees_in_words(amount: float) -> str:
    """Indian numbering: 123456.5 -> 'One Lakh Twenty Three Thousand Four Hundred Fifty Six Rupees and Fifty Paise Only'."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
            "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two(n):
        return ones[n] if n < 20 else (tens[n // 10] + (" " + ones[n % 10] if n % 10 else ""))

    def three(n):
        return (ones[n // 100] + " Hundred" + (" " + two(n % 100) if n % 100 else "")) if n >= 100 else two(n)

    rupees, paise = int(amount), round((amount - int(amount)) * 100)
    if rupees == 0:
        words = "Zero"
    else:
        parts = []
        for div, name in ((10_000_000, "Crore"), (100_000, "Lakh"), (1000, "Thousand")):
            if rupees >= div:
                parts.append(f"{three(rupees // div) if div != 10_000_000 else rupees_in_words_int(rupees // div)} {name}")
                rupees %= div
        if rupees:
            parts.append(three(rupees))
        words = " ".join(parts)
    return f"{words} Rupees" + (f" and {two(paise)} Paise" if paise else "") + " Only"


def rupees_in_words_int(n: int) -> str:
    """Whole-number words (used for crores above 999)."""
    return rupees_in_words(n).replace(" Rupees Only", "")
