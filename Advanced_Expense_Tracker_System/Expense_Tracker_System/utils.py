# Utility functions
# utils.py

import uuid
import hashlib
from datetime import datetime


# ==========================================
# Current Date
# ==========================================

def current_date():
    return datetime.now().strftime("%Y-%m-%d")


# ==========================================
# Current Date & Time
# ==========================================

def current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ==========================================
# Generate Unique ID
# ==========================================

def generate_id(prefix="ID"):

    random_id = str(uuid.uuid4()).replace("-", "")[:6].upper()

    return f"{prefix}{random_id}"


# ==========================================
# Password Hashing
# ==========================================

def hash_password(password):

    return hashlib.sha256(password.encode()).hexdigest()


# ==========================================
# Verify Password
# ==========================================

def verify_password(password, hashed_password):

    return hash_password(password) == hashed_password


# ==========================================
# Validate Email
# ==========================================

def is_valid_email(email):

    return "@" in email and "." in email


# ==========================================
# Validate Phone Number
# ==========================================

def is_valid_phone(phone):

    return phone.isdigit() and len(phone) == 10


# ==========================================
# Validate Amount
# ==========================================

def is_valid_amount(amount):

    try:

        amount = float(amount)

        return amount > 0

    except:

        return False


# ==========================================
# Validate Date
# ==========================================

def is_valid_date(date_string):

    try:

        datetime.strptime(date_string, "%Y-%m-%d")

        return True

    except ValueError:

        return False


# ==========================================
# Currency Format
# ==========================================

def format_currency(amount):

    return f"₹{amount:,.2f}"


# ==========================================
# Print Heading
# ==========================================

def print_heading(title):

    print("\n" + "=" * 50)
    print(title.center(50))
    print("=" * 50)


# ==========================================
# Print Success Message
# ==========================================

def success(message):

    print(f"\n✅ {message}")


# ==========================================
# Print Error Message
# ==========================================

def error(message):

    print(f"\n❌ {message}")


# ==========================================
# Print Warning Message
# ==========================================

def warning(message):

    print(f"\n⚠ {message}")


# ==========================================
# Confirm Action
# ==========================================

def confirm(message):

    choice = input(f"{message} (Y/N): ")

    return choice.lower() == "y"


# ==========================================
# Pause Program
# ==========================================

def pause():

    input("\nPress Enter to Continue...")


# ==========================================
# Clear Screen
# ==========================================

def clear_screen():

    import os

    os.system("cls" if os.name == "nt" else "clear")


# ==========================================
# Percentage Calculator
# ==========================================

def calculate_percentage(part, total):

    if total == 0:
        return 0

    return round((part / total) * 100, 2)


# ==========================================
# Savings Progress
# ==========================================

def savings_progress(saved, target):

    if target == 0:
        return 0

    return round((saved / target) * 100, 2)


# ==========================================
# Financial Balance
# ==========================================

def calculate_balance(income, expense):

    return income - expense


# ==========================================
# Budget Remaining
# ==========================================

def remaining_budget(budget, expense):

    return budget - expense


# ==========================================
# Greeting
# ==========================================

def greeting():

    hour = datetime.now().hour

    if hour < 12:
        return "Good Morning"

    elif hour < 17:
        return "Good Afternoon"

    else:
        return "Good Evening"


# ==========================================
# Footer
# ==========================================

def footer():

    print("\n" + "=" * 50)
    print("Thank You For Using Expense Tracker")
    print("=" * 50)