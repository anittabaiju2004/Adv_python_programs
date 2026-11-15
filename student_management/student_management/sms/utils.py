"""Utilities: academic rules (subjects, grading, attendance), exceptions,
validation, hashing and date helpers."""
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
DATA_DIR = Path(os.environ.get("SMS_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("SMS_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("SMS_REPORT_DIR", BASE_DIR / "reports"))

INSTITUTION = "Ociuz College of Applied Sciences"
INSTITUTION_ADDRESS = "Technopark, Thiruvananthapuram, Kerala 695581"

# Subjects and marks scheme
SUBJECTS = ["Python", "Java", "DBMS"]
SUBJECT_MAX = 100
PASS_MARK = 40                       # minimum marks per subject to pass
EXAMS = ["Internal Test 1", "Internal Test 2", "Semester Exam"]
FINAL_EXAM = "Semester Exam"         # attendance eligibility applies to this exam
ABSENT = "AB"                        # entered when a student is absent for a subject (counts as 0, fail)

# Grade scale on percentage: (minimum %, grade, grade point, description)
GRADES = [(90, "O", 10, "Outstanding"), (80, "A+", 9, "Excellent"), (70, "A", 8, "Very Good"),
          (60, "B+", 7, "Good"), (50, "B", 6, "Above Average"), (40, "C", 5, "Average"), (0, "F", 0, "Fail")]
DISTINCTION = 75.0                   # overall % for "First Class with Distinction"
FIRST_CLASS = 60.0

# Attendance
MIN_ATTENDANCE = 75.0                # % required to be eligible for the semester exam
ATTENDANCE_STATUSES = ["P", "A", "L"]            # Present, Absent, Leave (approved; counted as absent for %)
WEEKLY_OFF = {6}                     # Sunday
HOLIDAYS = {"2026-01-26": "Republic Day", "2026-04-14": "Vishu", "2026-08-15": "Independence Day",
            "2026-08-26": "Thiruvonam", "2026-10-02": "Gandhi Jayanti", "2026-12-25": "Christmas"}

GENDERS = ["Male", "Female", "Other"]
STUDENT_STATUSES = ["ACTIVE", "LEFT", "GRADUATED"]

ROLES = ["admin", "teacher"]
PERMISSIONS = {
    "admin":   {"*"},
    "teacher": {"students", "attendance", "marks", "results", "reports"},
    "student": {"self"},
}
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
PBKDF2_ITERATIONS = 100_000
DATE_FMT = "%Y-%m-%d"


# ================================================================= exceptions
class SMSError(Exception):
    """Base class for all application errors."""


class ValidationError(SMSError):
    pass


class NotFoundError(SMSError):
    pass


class AuthenticationError(SMSError):
    pass


class PermissionDenied(SMSError):
    pass


class DatabaseError(SMSError):
    pass


class BackupError(SMSError):
    pass


# ================================================================== grading
def grade_for(percent: float) -> tuple[str, int, str]:
    for minimum, grade, point, desc in GRADES:
        if percent >= minimum:
            return grade, point, desc
    return "F", 0, "Fail"


def division(percent: float, passed: bool) -> str:
    if not passed:
        return "Failed"
    if percent >= DISTINCTION:
        return "First Class with Distinction"
    if percent >= FIRST_CLASS:
        return "First Class"
    return "Second Class" if percent >= 50 else "Pass Class"


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
    if len(text) < 2 or len(text) > max_len or not text[0].isalpha() or any(c.isdigit() for c in text):
        raise ValidationError(f"{field} must be 2-{max_len} letters (no digits).")
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


def age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def is_working_day(d: date) -> bool:
    return d.weekday() not in WEEKLY_OFF and d.isoformat() not in HOLIDAYS


def working_days(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if is_working_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out
