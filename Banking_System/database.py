# database.py

import json
import os

# ===========================
# Database File Paths
# ===========================

CUSTOMERS_FILE = "data/customers.json"
TRANSACTIONS_FILE = "data/transactions.json"
LOANS_FILE = "data/loans.json"
FD_FILE = "data/fixed_deposits.json"
ADMINS_FILE = "data/admins.json"


# ===========================
# Create Database Files
# ===========================

def initialize_database():
    """Create data folder and JSON files if they don't exist."""

    os.makedirs("data", exist_ok=True)

    files = {
        CUSTOMERS_FILE: [],
        TRANSACTIONS_FILE: [],
        LOANS_FILE: [],
        FD_FILE: [],
        ADMINS_FILE: [
            {
                "username": "admin",
                "password": "admin123"
            }
        ]
    }

    for file, default_data in files.items():
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump(default_data, f, indent=4)


# ===========================
# Read JSON File
# ===========================

def read_data(file_name):
    try:
        with open(file_name, "r") as f:
            return json.load(f)
    except:
        return []


# ===========================
# Write JSON File
# ===========================

def write_data(file_name, data):
    with open(file_name, "w") as f:
        json.dump(data, f, indent=4)


# ===========================
# Customer Functions
# ===========================

def get_customers():
    return read_data(CUSTOMERS_FILE)


def save_customers(customers):
    write_data(CUSTOMERS_FILE, customers)


# ===========================
# Transaction Functions
# ===========================

def get_transactions():
    return read_data(TRANSACTIONS_FILE)


def save_transactions(transactions):
    write_data(TRANSACTIONS_FILE, transactions)


# ===========================
# Loan Functions
# ===========================

def get_loans():
    return read_data(LOANS_FILE)


def save_loans(loans):
    write_data(LOANS_FILE, loans)


# ===========================
# Fixed Deposit Functions
# ===========================

def get_fixed_deposits():
    return read_data(FD_FILE)


def save_fixed_deposits(fd):
    write_data(FD_FILE, fd)


# ===========================
# Admin Functions
# ===========================

def get_admins():
    return read_data(ADMINS_FILE)


def save_admins(admins):
    write_data(ADMINS_FILE, admins)


# ===========================
# Main
# ===========================

if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")