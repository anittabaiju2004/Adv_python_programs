"""Utilities: business configuration, GST rules, exceptions, validation, hashing and helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import date, datetime
from pathlib import Path

# ============================================================== configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("INV_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("INV_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("INV_REPORT_DIR", BASE_DIR / "reports"))

BUSINESS_NAME = "Malabar Wholesale Traders"
BUSINESS_ADDRESS = "Market Road, Kozhikode, Kerala 673001"
BUSINESS_PHONE = "+91 495 2701234"
BUSINESS_GSTIN = "32AAFCM1234B1ZQ"        # sample GSTIN (32 = Kerala)
BUSINESS_STATE = "Kerala"
CURRENCY = "₹"

# GST rates allowed (GST 2.0 slabs from 22 Sep 2025, plus nil and special rates)
GST_RATES = [0.0, 0.25, 3.0, 5.0, 18.0, 40.0]
UNITS = ["pcs", "box", "pack", "dozen", "kg", "g", "litre", "ml", "metre"]
DECIMAL_UNITS = {"kg", "g", "litre", "ml", "metre"}      # quantities may have decimals
PAYMENT_MODES = ["Cash", "UPI", "Card", "Bank Transfer", "Credit"]
MAX_LINE_DISCOUNT = 50.0                                  # %
WALK_IN_CUSTOMER = "CUST0001"

ROLES = ["admin", "manager", "cashier", "storekeeper"]
PERMISSIONS = {
    "admin":       {"*"},
    "manager":     {"products", "products.manage", "categories", "suppliers", "customers", "purchases",
                    "sales", "sales.cancel", "stock.adjust", "reports", "discount"},
    "cashier":     {"products", "customers", "sales", "discount"},
    "storekeeper": {"products", "products.manage", "categories", "suppliers", "purchases", "stock.adjust"},
}
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"

# GST state codes (first two digits of a GSTIN)
STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand",
    "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
    "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}
STATES = sorted(STATE_CODES.values())


# ================================================================= exceptions
class InventoryError(Exception):
    """Base class for all application errors."""


class ValidationError(InventoryError):
    pass


class NotFoundError(InventoryError):
    pass


class AuthenticationError(InventoryError):
    pass


class PermissionDenied(InventoryError):
    pass


class StockError(InventoryError):
    pass


class DatabaseError(InventoryError):
    pass


class BackupError(InventoryError):
    pass


# ======================================================================= GST
def gst_split(taxable: float, rate: float, inter_state: bool) -> dict:
    """GST on a taxable amount: IGST for inter-state supply, else CGST + SGST (half each)."""
    tax = round(taxable * rate / 100, 2)
    if inter_state:
        return {"cgst": 0.0, "sgst": 0.0, "igst": tax, "tax": tax}
    half = round(tax / 2, 2)
    return {"cgst": half, "sgst": round(tax - half, 2), "igst": 0.0, "tax": tax}


def is_inter_state(state: str) -> bool:
    return bool(state) and state != BUSINESS_STATE


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
GSTIN_RE = re.compile(r"^(\d{2})[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def validate_name(value: str, field: str = "Name", max_len: int = 80) -> str:
    text = " ".join(str(value or "").split())
    if len(text) < 2 or len(text) > max_len or not text[0].isalnum():
        raise ValidationError(f"{field} must be 2-{max_len} characters and start with a letter or digit.")
    return text


def validate_phone(value: str, required: bool = True) -> str:
    s = re.sub(r"[\s\-()]", "", str(value or ""))
    if not s and not required:
        return ""
    m = re.fullmatch(r"(?:\+?91|0)?([6-9]\d{9})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"0\d{9,10}", s):                    # landline with STD code
        return s
    raise ValidationError("Phone must be a 10-digit mobile number or a landline with STD code.")


def validate_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if email and not EMAIL_RE.match(email):
        raise ValidationError(f"'{value}' is not a valid email address.")
    return email


def validate_gstin(value: str) -> tuple[str, str]:
    """Returns (gstin, state). Empty input returns ('', '')."""
    g = str(value or "").strip().upper()
    if not g:
        return "", ""
    m = GSTIN_RE.match(g)
    if not m or m.group(1) not in STATE_CODES:
        raise ValidationError("GSTIN must be 15 characters like 32ABCDE1234F1Z5 with a valid state code.")
    return g, STATE_CODES[m.group(1)]


def validate_state(value: str) -> str:
    return validate_choice(value, STATES, "state")


def validate_hsn(value: str) -> str:
    h = str(value or "").strip()
    if h and not re.fullmatch(r"\d{4}|\d{6}|\d{8}", h):
        raise ValidationError("HSN code must be 4, 6 or 8 digits.")
    return h


def validate_gst_rate(value) -> float:
    try:
        rate = float(value)
    except (TypeError, ValueError):
        raise ValidationError("GST rate must be a number.")
    if rate not in GST_RATES:
        raise ValidationError(f"GST rate must be one of {', '.join(f'{r:g}' for r in GST_RATES)} %.")
    return rate


def validate_amount(value, field: str = "Amount", lo: float = 0.01, hi: float = 1_00_00_000.0) -> float:
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if not lo <= amount <= hi:
        raise ValidationError(f"{field} must be between {lo:,.2f} and {hi:,.2f}.")
    return amount


def validate_qty(value, unit: str, field: str = "Quantity", allow_zero: bool = False) -> float:
    try:
        q = round(float(value), 3)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if q < 0 or (q == 0 and not allow_zero):
        raise ValidationError(f"{field} must be greater than zero.")
    if unit not in DECIMAL_UNITS and q != int(q):
        raise ValidationError(f"{field} must be a whole number for unit '{unit}'.")
    if q > 1_000_000:
        raise ValidationError(f"{field} is too large.")
    return q


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
def now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


def money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def fmt_qty(q: float) -> str:
    return f"{q:g}"


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
