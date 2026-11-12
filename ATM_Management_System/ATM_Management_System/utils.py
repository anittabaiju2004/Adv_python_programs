# Utility functions
# utils.py

import hashlib
from datetime import datetime


# ==========================================
# Generate Account Number
# ==========================================

def generate_account_number(customers):

    if len(customers) == 0:

        return "1001"

    last_account = max(
        int(customer["account_number"])
        for customer in customers
    )

    return str(last_account + 1)


# ==========================================
# Generate Transaction ID
# ==========================================

def generate_transaction_id():

    return "TXN" + datetime.now().strftime("%Y%m%d%H%M%S")


# ==========================================
# Generate Loan ID
# ==========================================

def generate_loan_id():

    return "LN" + datetime.now().strftime("%Y%m%d%H%M%S")


# ==========================================
# Generate Fixed Deposit ID
# ==========================================

def generate_fd_id():

    return "FD" + datetime.now().strftime("%Y%m%d%H%M%S")


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
# Hash PIN
# ==========================================

def hash_pin(pin):

    return hashlib.sha256(
        pin.encode()
    ).hexdigest()


# ==========================================
# Verify PIN
# ==========================================

def verify_pin(pin, hashed_pin):

    return hash_pin(pin) == hashed_pin
# ==========================================
# Validate Phone Number
# ==========================================

def is_valid_phone(phone):

    if len(phone) != 10:
        return False

    if not phone.isdigit():
        return False

    return True


# ==========================================
# Validate Email Address
# ==========================================

def is_valid_email(email):

    if "@" not in email:
        return False

    if "." not in email:
        return False

    return True


# ==========================================
# Validate PIN
# ==========================================

def is_valid_pin(pin):

    if len(pin) != 4:
        return False

    if not pin.isdigit():
        return False

    return True


# ==========================================
# Validate Amount
# ==========================================

def is_valid_amount(amount):

    try:

        amount = float(amount)

        if amount <= 0:
            return False

        return True

    except ValueError:

        return False


# ==========================================
# Find Customer
# ==========================================

def find_customer(customers, account_number):

    for customer in customers:

        if customer["account_number"] == account_number:

            return customer

    return None


# ==========================================
# Currency Formatter
# ==========================================

def format_currency(amount):

    return f"₹{amount:,.2f}"


# ==========================================
# Print ATM Receipt
# ==========================================

def print_receipt(

    account_number,
    transaction_type,
    amount,
    balance

):

    print("\n")
    print("=" * 45)
    print("            ATM RECEIPT")
    print("=" * 45)

    print(f"Account Number : {account_number}")
    print(f"Transaction    : {transaction_type}")
    print(f"Amount         : {format_currency(amount)}")
    print(f"Balance        : {format_currency(balance)}")
    print(f"Date           : {current_datetime()}")

    print("=" * 45)
    print(" Thank You For Banking With Us ")
    print("=" * 45)


# ==========================================
# Display Customer Details
# ==========================================

def display_customer(customer):

    print("\n========== CUSTOMER DETAILS ==========\n")

    print("Account Number :", customer["account_number"])
    print("Name           :", customer["name"])
    print("Age            :", customer["age"])
    print("Gender         :", customer["gender"])
    print("Phone          :", customer["phone"])
    print("Email          :", customer["email"])
    print("Address        :", customer["address"])
    print("Balance        :", format_currency(customer["balance"]))
    print("Status         :", customer["status"])
    print("Created Date   :", customer["created_date"])


# ==========================================
# Print Section Header
# ==========================================

def print_header(title):

    print("\n")
    print("=" * 60)
    print(title.center(60))
    print("=" * 60)
import os
import math


# ==========================================
# Calculate Simple Interest
# ==========================================

def calculate_interest(principal, rate, years):

    interest = (principal * rate * years) / 100

    maturity = principal + interest

    return interest, maturity


# ==========================================
# Calculate Loan EMI
# ==========================================

def calculate_emi(principal, annual_rate, years):

    months = years * 12

    monthly_rate = annual_rate / (12 * 100)

    if monthly_rate == 0:

        emi = principal / months

        return round(emi, 2)

    emi = (
        principal
        * monthly_rate
        * math.pow(1 + monthly_rate, months)
    ) / (
        math.pow(1 + monthly_rate, months) - 1
    )

    return round(emi, 2)


# ==========================================
# Customer Statistics
# ==========================================

def customer_statistics(customers):

    total_accounts = len(customers)

    active = 0
    frozen = 0

    total_balance = 0

    for customer in customers:

        total_balance += customer["balance"]

        if customer["status"] == "Active":

            active += 1

        else:

            frozen += 1

    print("\n========== CUSTOMER STATISTICS ==========\n")

    print("Total Customers :", total_accounts)
    print("Active Accounts :", active)
    print("Frozen Accounts :", frozen)
    print("Total Balance   :", format_currency(total_balance))


# ==========================================
# Greeting Message
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
# Welcome Banner
# ==========================================

def welcome_message():

    print("\n")
    print("=" * 60)
    print(greeting())
    print("WELCOME TO ATM MANAGEMENT SYSTEM")
    print("=" * 60)


# ==========================================
# Clear Screen
# ==========================================

def clear_screen():

    os.system("cls" if os.name == "nt" else "clear")


# ==========================================
# Pause Program
# ==========================================

def pause():

    input("\nPress Enter To Continue...")


# ==========================================
# Footer
# ==========================================

def footer():

    print("\n")
    print("=" * 60)
    print("Thank You For Banking With Us")
    print("=" * 60)


# ==========================================
# Confirm Action
# ==========================================

def confirm_action(message):

    choice = input(f"{message} (Y/N): ")

    return choice.upper() == "Y"


# ==========================================
# Print Success Message
# ==========================================

def success(message):

    print(f"\nSUCCESS : {message}")


# ==========================================
# Print Error Message
# ==========================================

def error(message):

    print(f"\nERROR : {message}")


# ==========================================
# Print Warning Message
# ==========================================

def warning(message):

    print(f"\nWARNING : {message}")


# ==========================================
# Display Balance
# ==========================================

def display_balance(balance):

    print(f"\nAvailable Balance : {format_currency(balance)}")


# ==========================================
# Display Account Status
# ==========================================

def display_status(status):

    print(f"\nAccount Status : {status}")


# ==========================================
# End of Utils
# ==========================================