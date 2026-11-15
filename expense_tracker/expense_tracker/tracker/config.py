"""Central configuration for the Expense Tracker."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Allow overriding storage locations (used by the test-suite).
DATA_DIR = Path(os.environ.get("ET_DATA_DIR", BASE_DIR / "data"))
BACKUP_DIR = Path(os.environ.get("ET_BACKUP_DIR", BASE_DIR / "backups"))
REPORT_DIR = Path(os.environ.get("ET_REPORT_DIR", BASE_DIR / "reports"))

DATE_FORMAT = "%Y-%m-%d"
CURRENCY = "₹"

EXPENSE_CATEGORIES = [
    "Food", "Transport", "Shopping", "Bills", "Health",
    "Entertainment", "Education", "Rent", "Travel", "Other",
]
INCOME_SOURCES = ["Salary", "Business", "Freelance", "Investment", "Gift", "Other"]
PAYMENT_MODES = ["Cash", "UPI", "Card", "Net Banking", "Other"]

# Budget alert fires once spending reaches this fraction of the limit.
BUDGET_WARNING_THRESHOLD = 0.80

# How many days ahead a bill counts as "upcoming".
BILL_REMINDER_DAYS = 7

# Default admin account created on first run.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

PBKDF2_ITERATIONS = 100_000
