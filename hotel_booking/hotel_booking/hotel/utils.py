"""Utilities: hotel configuration, GST rules, exceptions, validation, hashing and helpers."""
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
DATA_DIR = Path(os.environ.get("HOTEL_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("HOTEL_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("HOTEL_REPORT_DIR", BASE_DIR / "reports"))

HOTEL_NAME = "Hotel Malabar Residency"
HOTEL_ADDRESS = "MG Road, Kochi, Kerala 682016"
HOTEL_PHONE = "+91 484 2345678"
HOTEL_GSTIN = "32ABCDE1234F1Z5"          # 32 = Kerala (sample GSTIN)
CURRENCY = "₹"
CHECK_IN_TIME = "12:00"
CHECK_OUT_TIME = "11:00"

# Room categories: base tariff per night, max guests, amenities
ROOM_CATEGORIES = {
    "Standard":  {"rate": 2500.0, "capacity": 2, "amenities": "AC, TV, Wi-Fi"},
    "Deluxe":    {"rate": 4500.0, "capacity": 3, "amenities": "AC, TV, Wi-Fi, Mini-bar, City view"},
    "Executive": {"rate": 6800.0, "capacity": 3, "amenities": "AC, TV, Wi-Fi, Mini-bar, Work desk, Bathtub"},
    "Suite":     {"rate": 9500.0, "capacity": 4, "amenities": "Living room, AC, TV, Wi-Fi, Mini-bar, Jacuzzi"},
}
WEEKEND_SURCHARGE = 10.0                  # % extra for Friday and Saturday nights
WEEKEND_NIGHTS = {4, 5}                   # Monday = 0 -> Friday, Saturday
EXTRA_BED_RATE = 800.0                    # per night; allows one extra guest
MAX_NIGHTS = 30
MAX_ADVANCE_DAYS = 365
MAX_DISCOUNT = 30.0                       # % (managers may give up to this)
FREE_CANCELLATION_HOURS = 48              # before check-in time; later cancellations forfeit the first night

# GST on accommodation (from 22 Sep 2025): tariff <= 7,500 per night -> 5 %, above -> 18 %.
GST_ROOM_THRESHOLD = 7500.0
GST_ROOM_LOW, GST_ROOM_HIGH = 5.0, 18.0
# A hotel with any room tariff above 7,500 is "specified premises": its restaurant / room
# service is taxed at 18 %, otherwise 5 %.
SPECIFIED_PREMISES = any(c["rate"] > GST_ROOM_THRESHOLD for c in ROOM_CATEGORIES.values())

# Extra services: SAC code and GST %
SERVICE_TYPES = {
    "Food & Beverage": {"sac": "996331", "gst": 18.0 if SPECIFIED_PREMISES else 5.0},
    "Laundry":         {"sac": "999712", "gst": 18.0},
    "Spa & Wellness":  {"sac": "999722", "gst": 18.0},
    "Other Services":  {"sac": "999799", "gst": 18.0},
}
SAC_ACCOMMODATION = "996311"

PAYMENT_MODES = ["Cash", "UPI", "Card", "Net Banking"]
ID_PROOFS = {  # type -> regex
    "Aadhaar": r"\d{12}",
    "Passport": r"[A-Z][0-9]{7}",
    "Driving Licence": r"[A-Z]{2}[0-9]{2}[ -]?[0-9]{4}[0-9]{7}",
    "Voter ID": r"[A-Z]{3}[0-9]{7}",
}
BOOKING_SOURCES = ["Walk-in", "Phone", "Website", "Travel Agent"]

ROLES = ["admin", "manager", "receptionist", "housekeeping"]
PERMISSIONS = {
    "admin":        {"*"},
    "manager":      {"rooms", "rooms.manage", "customers", "bookings", "billing", "reports", "housekeeping",
                     "discount", "noshow"},
    "receptionist": {"rooms", "customers", "bookings", "billing", "housekeeping"},
    "housekeeping": {"rooms", "housekeeping"},
}
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class HotelError(Exception):
    """Base class for all application errors."""


class ValidationError(HotelError):
    pass


class NotFoundError(HotelError):
    pass


class AuthenticationError(HotelError):
    pass


class PermissionDenied(HotelError):
    pass


class AvailabilityError(HotelError):
    pass


class DatabaseError(HotelError):
    pass


class BackupError(HotelError):
    pass


# ======================================================================= GST
def room_gst_rate(tariff_per_night: float) -> float:
    return GST_ROOM_LOW if tariff_per_night <= GST_ROOM_THRESHOLD else GST_ROOM_HIGH


def gst(amount: float, rate: float) -> float:
    return round(amount * rate / 100, 2)


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
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,59}$")


def validate_name(value: str, field: str = "Name") -> str:
    text = " ".join(str(value or "").split())
    if not NAME_RE.match(text):
        raise ValidationError(f"{field} must be 2-60 letters (spaces, . ' - allowed).")
    return " ".join(w.capitalize() if w.islower() or w.isupper() else w for w in text.split())


def validate_phone(value: str) -> str:
    """Indian mobiles -> 10 digits; international numbers kept as +<digits>."""
    s = re.sub(r"[\s\-()]", "", str(value or ""))
    m = re.fullmatch(r"(?:\+?91|0)?([6-9]\d{9})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"\+[1-9]\d{6,14}", s):
        return s
    raise ValidationError("Phone must be a 10-digit Indian mobile or an international number (+country code).")


def validate_email(value: str, required: bool = False) -> str:
    email = str(value or "").strip().lower()
    if not email and not required:
        return ""
    if not EMAIL_RE.match(email):
        raise ValidationError(f"'{value}' is not a valid email address.")
    return email


def validate_id_proof(id_type: str, number: str) -> tuple[str, str]:
    id_type = validate_choice(id_type, ID_PROOFS, "ID proof type")
    num = re.sub(r"\s", "", str(number or "")).upper()
    if not re.fullmatch(ID_PROOFS[id_type], num):
        raise ValidationError(f"Invalid {id_type} number.")
    if id_type == "Aadhaar" and num[0] in "01":
        raise ValidationError("Aadhaar numbers do not start with 0 or 1.")
    return id_type, num


def parse_date(value, field: str = "Date") -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), DATE_FMT).date()
    except ValueError:
        raise ValidationError(f"{field} must be in YYYY-MM-DD format.")


def validate_amount(value, field: str = "Amount", lo: float = 0.01, hi: float = 10_00_000.0) -> float:
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if not lo <= amount <= hi:
        raise ValidationError(f"{field} must be between {money(lo)} and {money(hi)}.")
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


# ================================================================= helpers
def now() -> datetime:
    return datetime.now()


def now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


def money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def nights_between(check_in: date, check_out: date) -> list[date]:
    return [check_in + timedelta(days=i) for i in range((check_out - check_in).days)]


def financial_year(d: date) -> str:
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def rupees_in_words(amount: float) -> str:
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
            "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two(n):
        return ones[n] if n < 20 else tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")

    def three(n):
        return (ones[n // 100] + " Hundred" + (" " + two(n % 100) if n % 100 else "")) if n >= 100 else two(n)

    def whole(n):
        if n == 0:
            return "Zero"
        parts = []
        for div, name in ((10_000_000, "Crore"), (100_000, "Lakh"), (1000, "Thousand")):
            if n >= div:
                parts.append(f"{whole(n // div) if div == 10_000_000 else three(n // div)} {name}")
                n %= div
        if n:
            parts.append(three(n))
        return " ".join(parts)

    rupees, paise = int(amount), round((amount - int(amount)) * 100)
    return f"{whole(rupees)} Rupees" + (f" and {two(paise)} Paise" if paise else "") + " Only"
