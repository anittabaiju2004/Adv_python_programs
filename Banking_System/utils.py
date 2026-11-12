# utils.py (Part 1)

import hashlib
from datetime import datetime


# ==========================================
# Generate Account Number
# ==========================================

def generate_account_number(customers):

    if len(customers) == 0:

        return "100000001"

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
# Generate Reference Number
# ==========================================

def generate_reference_number(prefix="REF"):

    return (
        prefix +
        datetime.now().strftime("%Y%m%d%H%M%S")
    )


# ==========================================
# Generate Customer ID
# ==========================================

def generate_customer_id(customers):

    if len(customers) == 0:

        return "CUST001"

    numbers = []

    for customer in customers:

        customer_id = customer.get(
            "customer_id",
            "CUST000"
        )

        try:

            numbers.append(
                int(customer_id.replace("CUST", ""))
            )

        except ValueError:

            continue

    if not numbers:

        return "CUST001"

    return f"CUST{max(numbers)+1:03d}"


# ==========================================
# Generate Receipt Number
# ==========================================

def generate_receipt_number():

    return "RCT" + datetime.now().strftime("%Y%m%d%H%M%S")
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
# Format Currency
# ==========================================

def format_currency(amount):

    return f"₹{amount:,.2f}"


# ==========================================
# Print Transaction Receipt
# ==========================================

def print_receipt(

    account_number,
    transaction_type,
    amount,
    balance

):

    receipt_number = generate_receipt_number()

    print("\n")
    print("=" * 50)
    print("             BANK RECEIPT")
    print("=" * 50)

    print(f"Receipt No      : {receipt_number}")
    print(f"Account Number  : {account_number}")
    print(f"Transaction     : {transaction_type}")
    print(f"Amount          : {format_currency(amount)}")
    print(f"Balance         : {format_currency(balance)}")
    print(f"Date & Time     : {current_datetime()}")

    print("=" * 50)
    print("     THANK YOU FOR BANKING WITH US")
    print("=" * 50)


# ==========================================
# Display Customer Details
# ==========================================

def display_customer(customer):

    print("\n")
    print("=" * 60)
    print("          CUSTOMER DETAILS")
    print("=" * 60)

    print("Account Number :", customer["account_number"])

    if "customer_id" in customer:

        print("Customer ID    :", customer["customer_id"])

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
# Print Header
# ==========================================

def print_header(title):

    print("\n")
    print("=" * 60)
    print(title.center(60))
    print("=" * 60)


# ==========================================
# Print Divider
# ==========================================

def print_divider():

    print("-" * 60)


# ==========================================
# Display Account Balance
# ==========================================

def display_balance(balance):

    print("\nCurrent Available Balance")
    print("-" * 30)
    print(format_currency(balance))


# ==========================================
# Account Exists
# ==========================================

def account_exists(customers, account_number):

    for customer in customers:

        if customer["account_number"] == account_number:

            return True

    return False


# ==========================================
# Get Customer Name
# ==========================================

def get_customer_name(customers, account_number):

    customer = find_customer(customers, account_number)

    if customer:

        return customer["name"]

    return None

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

        return round(principal / months, 2)

    emi = (
        principal *
        monthly_rate *
        math.pow(1 + monthly_rate, months)
    ) / (
        math.pow(1 + monthly_rate, months) - 1
    )

    return round(emi, 2)


# ==========================================
# Customer Statistics
# ==========================================

def customer_statistics(customers):

    total_accounts = len(customers)

    active_accounts = 0
    frozen_accounts = 0
    total_balance = 0

    for customer in customers:

        total_balance += customer["balance"]

        if customer["status"] == "Active":

            active_accounts += 1

        else:

            frozen_accounts += 1

    print("\n")
    print("=" * 60)
    print("          CUSTOMER STATISTICS")
    print("=" * 60)

    print("Total Customers :", total_accounts)
    print("Active Accounts :", active_accounts)
    print("Frozen Accounts :", frozen_accounts)
    print("Total Balance   :", format_currency(total_balance))


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
# Welcome Banner
# ==========================================

def welcome_message():

    print("\n")
    print("=" * 60)
    print(greeting())
    print("WELCOME TO BANK MANAGEMENT SYSTEM")
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
# Success Message
# ==========================================

def success(message):

    print(f"\nSUCCESS : {message}")


# ==========================================
# Error Message
# ==========================================

def error(message):

    print(f"\nERROR : {message}")


# ==========================================
# Warning Message
# ==========================================

def warning(message):

    print(f"\nWARNING : {message}")


# ==========================================
# Confirmation Prompt
# ==========================================

def confirm_action(message):

    choice = input(f"{message} (Y/N): ").strip().upper()

    return choice == "Y"


# ==========================================
# Display Account Status
# ==========================================

def display_status(status):

    print(f"\nAccount Status : {status}")


# ==========================================
# Display Current Date & Time
# ==========================================

def show_datetime():

    print("Current Date & Time :", current_datetime())


# ==========================================
# Bank Information
# ==========================================

def bank_information():

    print("\n")
    print("=" * 60)
    print("BANK MANAGEMENT SYSTEM")
    print("=" * 60)
    print("Database : JSON File")
    print("Language : Python")
    print("Version  : 1.0")
    print("=" * 60)