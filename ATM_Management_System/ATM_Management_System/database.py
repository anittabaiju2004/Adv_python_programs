# JSON database helpers
# database.py

import json
import os

# ==========================================
# Folder Configuration
# ==========================================

DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)


# ==========================================
# File Paths
# ==========================================

CUSTOMER_FILE = os.path.join(DATA_FOLDER, "customers.json")

TRANSACTION_FILE = os.path.join(DATA_FOLDER, "transactions.json")

LOAN_FILE = os.path.join(DATA_FOLDER, "loans.json")

FD_FILE = os.path.join(DATA_FOLDER, "fixed_deposits.json")

ADMIN_FILE = os.path.join(DATA_FOLDER, "admins.json")


# ==========================================
# Create JSON File
# ==========================================

def create_json_file(filename, default_data):

    if not os.path.exists(filename):

        with open(filename, "w") as file:

            json.dump(default_data, file, indent=4)


# ==========================================
# Initialize Database
# ==========================================

def initialize_database():

    create_json_file(CUSTOMER_FILE, [])

    create_json_file(TRANSACTION_FILE, [])

    create_json_file(LOAN_FILE, [])

    create_json_file(FD_FILE, [])

    create_json_file(
        ADMIN_FILE,
        [
            {
                "username": "admin",
                "password": "admin123"
            }
        ]
    )


# ==========================================
# Read JSON
# ==========================================

def read_json(filename):

    try:

        with open(filename, "r") as file:

            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):

        return []


# ==========================================
# Write JSON
# ==========================================

def write_json(filename, data):

    with open(filename, "w") as file:

        json.dump(data, file, indent=4)


# ==========================================
# Customers
# ==========================================

def get_customers():

    return read_json(CUSTOMER_FILE)


def save_customers(customers):

    write_json(CUSTOMER_FILE, customers)


# ==========================================
# Transactions
# ==========================================

def get_transactions():

    return read_json(TRANSACTION_FILE)


def save_transactions(transactions):

    write_json(TRANSACTION_FILE, transactions)


# ==========================================
# Loans
# ==========================================

def get_loans():

    return read_json(LOAN_FILE)


def save_loans(loans):

    write_json(LOAN_FILE, loans)


# ==========================================
# Fixed Deposits
# ==========================================

def get_fixed_deposits():

    return read_json(FD_FILE)


def save_fixed_deposits(fd_list):

    write_json(FD_FILE, fd_list)


# ==========================================
# Admins
# ==========================================

def get_admins():

    return read_json(ADMIN_FILE)


def save_admins(admins):

    write_json(ADMIN_FILE, admins)


# ==========================================
# Reset Database
# ==========================================

def reset_database():

    save_customers([])

    save_transactions([])

    save_loans([])

    save_fixed_deposits([])

    save_admins(
        [
            {
                "username": "admin",
                "password": "admin123"
            }
        ]
    )

    print("\nDatabase Reset Successfully.")


# ==========================================
# Database Statistics
# ==========================================

def database_statistics():

    customers = get_customers()

    transactions = get_transactions()

    loans = get_loans()

    fds = get_fixed_deposits()

    admins = get_admins()

    print("\n========== DATABASE STATISTICS ==========\n")

    print(f"Customers          : {len(customers)}")
    print(f"Transactions       : {len(transactions)}")
    print(f"Loans              : {len(loans)}")
    print(f"Fixed Deposits     : {len(fds)}")
    print(f"Administrators     : {len(admins)}")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    initialize_database()

    database_statistics()