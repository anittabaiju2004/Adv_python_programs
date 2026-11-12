# Admin module
# admin.py

from database import (
    get_users,
    save_users,
    get_expenses,
    get_income
)

from backup import backup_database, restore_database

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ==============================
# Admin Login
# ==============================

def admin_login():

    print("\n========== ADMIN LOGIN ==========")

    username = input("Username : ")
    password = input("Password : ")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        print("\nLogin Successful.")
        admin_menu()
    else:
        print("\nInvalid Username or Password.")


# ==============================
# View Users
# ==============================

def view_users():

    users = get_users()

    if not users:
        print("\nNo Users Found.")
        return

    print("\n=========== USERS ===========")

    for user in users:

        print("-" * 40)
        print("User ID :", user.get("user_id"))
        print("Name    :", user.get("name"))
        print("Email   :", user.get("email"))
        print("Phone   :", user.get("phone"))


# ==============================
# View Expenses
# ==============================

def view_all_expenses():

    expenses = get_expenses()

    if not expenses:
        print("\nNo Expense Records.")
        return

    print("\n========== ALL EXPENSES ==========")

    total = 0

    for expense in expenses:

        print("-" * 50)
        print("Expense ID :", expense.get("expense_id"))
        print("User ID    :", expense.get("user_id"))
        print("Date       :", expense.get("date"))
        print("Category   :", expense.get("category"))
        print("Amount     :", expense.get("amount"))
        print("Description:", expense.get("description"))

        total += float(expense.get("amount"))

    print("\nTotal Expenses : ₹", total)


# ==============================
# View Income
# ==============================

def view_all_income():

    income = get_income()

    if not income:
        print("\nNo Income Records.")
        return

    print("\n========== ALL INCOME ==========")

    total = 0

    for item in income:

        print("-" * 50)
        print("Income ID  :", item.get("income_id"))
        print("User ID    :", item.get("user_id"))
        print("Date       :", item.get("date"))
        print("Source     :", item.get("source"))
        print("Amount     :", item.get("amount"))

        total += float(item.get("amount"))

    print("\nTotal Income : ₹", total)


# ==============================
# Delete User
# ==============================

def delete_user():

    users = get_users()

    user_id = input("\nEnter User ID : ")

    for user in users:

        if user["user_id"] == user_id:

            users.remove(user)

            save_users(users)

            print("\nUser Deleted Successfully.")

            return

    print("\nUser Not Found.")


# ==============================
# Summary Report
# ==============================

def summary_report():

    users = get_users()
    expenses = get_expenses()
    income = get_income()

    total_income = sum(float(i["amount"]) for i in income)
    total_expense = sum(float(e["amount"]) for e in expenses)

    print("\n========== SUMMARY ==========")

    print("Total Users      :", len(users))
    print("Total Income     : ₹", total_income)
    print("Total Expense    : ₹", total_expense)
    print("Current Balance  : ₹", total_income - total_expense)


# ==============================
# Admin Menu
# ==============================

def admin_menu():

    while True:

        print("\n==============================")
        print("      ADMIN DASHBOARD")
        print("==============================")

        print("1. View Users")
        print("2. View Expenses")
        print("3. View Income")
        print("4. Delete User")
        print("5. Summary Report")
        print("6. Backup Database")
        print("7. Restore Database")
        print("8. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            view_users()

        elif choice == "2":
            view_all_expenses()

        elif choice == "3":
            view_all_income()

        elif choice == "4":
            delete_user()

        elif choice == "5":
            summary_report()

        elif choice == "6":
            backup_database()

        elif choice == "7":
            restore_database()

        elif choice == "8":
            print("\nLogged Out Successfully.")
            break

        else:
            print("\nInvalid Choice.")