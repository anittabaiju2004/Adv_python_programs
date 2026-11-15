"""Reusable validation helpers."""
from datetime import datetime, date

from .config import DATE_FORMAT
from .exceptions import ValidationError


def validate_amount(value) -> float:
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"'{value}' is not a valid amount.")
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    return amount


def validate_date(value: str | None) -> str:
    """Return an ISO date string. Empty input means today."""
    if value is None or str(value).strip() == "":
        return date.today().strftime(DATE_FORMAT)
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid date (use YYYY-MM-DD).")


def validate_month(value: str) -> str:
    """Validate a YYYY-MM month string."""
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid month (use YYYY-MM).")


def validate_choice(value: str, choices: list[str], field: str) -> str:
    for c in choices:
        if c.lower() == str(value).strip().lower():
            return c
    raise ValidationError(f"Invalid {field} '{value}'. Choose from: {', '.join(choices)}")


def validate_text(value: str, field: str, min_len: int = 1, max_len: int = 100) -> str:
    text = str(value or "").strip()
    if not (min_len <= len(text) <= max_len):
        raise ValidationError(f"{field} must be {min_len}-{max_len} characters.")
    return text


def validate_username(value: str) -> str:
    name = validate_text(value, "Username", 3, 30)
    if not name.replace("_", "").isalnum():
        raise ValidationError("Username may contain only letters, digits and underscores.")
    return name.lower()


def validate_password(value: str) -> str:
    if value is None or len(value) < 6:
        raise ValidationError("Password must be at least 6 characters.")
    if not any(ch.isdigit() for ch in value) or not any(ch.isalpha() for ch in value):
        raise ValidationError("Password must contain both letters and digits.")
    return value
