"""Utilities: quiz rules, grading, exceptions, validation, hashing and helpers."""
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
DATA_DIR = Path(os.environ.get("QUIZ_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("QUIZ_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("QUIZ_REPORT_DIR", BASE_DIR / "reports"))

APP_NAME = "Ociuz Online Quiz Portal"
ORGANISATION = "Ociuz Academy, Thiruvananthapuram"
CERT_SECRET = os.environ.get("QUIZ_CERT_SECRET", "change-this-secret-in-production")

DIFFICULTIES = ["Easy", "Medium", "Hard"]
DIFFICULTY_MARKS = {"Easy": 1, "Medium": 2, "Hard": 3}          # default marks per question
QUESTION_TYPES = ["MCQ", "True/False"]
MODES = ["Practice", "Exam"]
MIN_OPTIONS, MAX_OPTIONS = 2, 6

# Grade scale: (minimum percentage, grade, remark)
GRADES = [(90, "A+", "Outstanding"), (80, "A", "Excellent"), (70, "B", "Very Good"),
          (60, "C", "Good"), (50, "D", "Satisfactory"), (0, "F", "Needs Improvement")]
DEFAULT_PASS_PERCENT = 50.0
MAX_BOOKMARKS = 200

ROLES = ["admin", "instructor", "student"]
PERMISSIONS = {
    "admin":      {"*"},
    "instructor": {"categories", "questions", "quizzes", "results", "reports", "leaderboard"},
    "student":    {"take", "leaderboard"},
}
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class QuizError(Exception):
    """Base class for all application errors."""


class ValidationError(QuizError):
    pass


class NotFoundError(QuizError):
    pass


class AuthenticationError(QuizError):
    pass


class PermissionDenied(QuizError):
    pass


class QuizRuleError(QuizError):
    """Attempt limits, time-up, unpublished quiz, not enough questions..."""


class DatabaseError(QuizError):
    pass


class BackupError(QuizError):
    pass


# ================================================================== grading
def grade_for(percent: float) -> tuple[str, str]:
    for minimum, grade, remark in GRADES:
        if percent >= minimum:
            return grade, remark
    return "F", "Needs Improvement"


def certificate_code(result_id: str, username: str, percent: float) -> str:
    """Tamper-evident verification code printed on certificates."""
    msg = f"{result_id}|{username}|{percent:.2f}".encode()
    return hmac.new(CERT_SECRET.encode(), msg, hashlib.sha256).hexdigest()[:12].upper()


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


def validate_name(value: str, field: str = "Name", max_len: int = 60) -> str:
    text = " ".join(str(value or "").split())
    if len(text) < 2 or len(text) > max_len or not text[0].isalpha():
        raise ValidationError(f"{field} must be 2-{max_len} characters and start with a letter.")
    return " ".join(w.capitalize() if w.islower() or w.isupper() else w for w in text.split())


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


def validate_text(value: str, field: str, max_len: int = 200, required: bool = False) -> str:
    text = " ".join(str(value or "").split())
    if required and not text:
        raise ValidationError(f"{field} is required.")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    return text


def validate_int(value, field: str, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a whole number.")
    if not lo <= n <= hi:
        raise ValidationError(f"{field} must be between {lo} and {hi}.")
    return n


def validate_float(value, field: str, lo: float, hi: float) -> float:
    try:
        x = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if not lo <= x <= hi:
        raise ValidationError(f"{field} must be between {lo:g} and {hi:g}.")
    return x


def validate_choice(value: str, choices, field: str) -> str:
    for c in choices:
        if str(value).strip().lower() == str(c).lower():
            return c
    raise ValidationError(f"Invalid {field}. Choose from: {', '.join(map(str, choices))}")


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


def fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"
