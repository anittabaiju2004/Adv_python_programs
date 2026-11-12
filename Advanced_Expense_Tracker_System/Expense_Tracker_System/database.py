# JSON database
# database.py

import json
import os

# ==========================================
# Data Folder
# ==========================================

DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)


# ==========================================
# File Paths
# ==========================================

USERS_FILE = os.path.join(DATA_FOLDER, "users.json")
EXPENSE_FILE = os.path.join(DATA_FOLDER, "expenses.json")
INCOME_FILE = os.path.join(DATA_FOLDER, "income.json")
BUDGET_FILE = os.path.join(DATA_FOLDER, "budget.json")
REMINDER_FILE = os.path.join(DATA_FOLDER, "reminders.json")
SAVINGS_FILE = os.path.join(DATA_FOLDER, "savings.json")
ADMINS_FILE = os.path.join(DATA_FOLDER, "admins.json")


# ==========================================
# Create File
# ==========================================

def create_file(filename, default_data):

    if not os.path.exists(filename):

        with open(filename, "w") as file:

            json.dump(default_data, file, indent=4)


# ==========================================
# Initialize Database
# ==========================================

def initialize_database():

    create_file(USERS_FILE, [])

    create_file(EXPENSE_FILE, [])

    create_file(INCOME_FILE, [])

    create_file(BUDGET_FILE, [])

    create_file(REMINDER_FILE, [])

    create_file(SAVINGS_FILE, [])

    create_file(
        ADMINS_FILE,
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

    except:

        return []


# ==========================================
# Write JSON
# ==========================================

def write_json(filename, data):

    with open(filename, "w") as file:

        json.dump(data, file, indent=4)


# ==========================================
# Users
# ==========================================

def get_users():

    return read_json(USERS_FILE)


def save_users(users):

    write_json(USERS_FILE, users)


# ==========================================
# Expenses
# ==========================================

def get_expenses():

    return read_json(EXPENSE_FILE)


def save_expenses(expenses):

    write_json(EXPENSE_FILE, expenses)


# ==========================================
# Income
# ==========================================

def get_income():

    return read_json(INCOME_FILE)


def save_income(income):

    write_json(INCOME_FILE, income)


# ==========================================
# Budget
# ==========================================

def get_budget():

    return read_json(BUDGET_FILE)


def save_budget(budget):

    write_json(BUDGET_FILE, budget)


# ==========================================
# Reminders
# ==========================================

def get_reminders():

    return read_json(REMINDER_FILE)


def save_reminders(reminders):

    write_json(REMINDER_FILE, reminders)


# ==========================================
# Savings
# ==========================================

def get_savings():

    return read_json(SAVINGS_FILE)


def save_savings(savings):

    write_json(SAVINGS_FILE, savings)


# ==========================================
# Admins
# ==========================================

def get_admins():

    return read_json(ADMINS_FILE)


def save_admins(admins):

    write_json(ADMINS_FILE, admins)


# ==========================================
# Reset Database
# ==========================================

def reset_database():

    save_users([])

    save_expenses([])

    save_income([])

    save_budget([])

    save_reminders([])

    save_savings([])

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
# Main
# ==========================================

if __name__ == "__main__":

    initialize_database()

    print("Database Initialized Successfully.")