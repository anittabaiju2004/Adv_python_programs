# Main application
# main.py

from database import initialize_database

from auth import (
    register_user,
    login,
    change_password,
    forgot_password,
    logout
)

from expense import expense_menu
from income import income_menu
from budget import budget_menu
from admin import admin_login
from backup import backup_menu


# ==========================================
# User Dashboard
# ==========================================

def user_dashboard():

    while True:

        print("\n")
        print("=" * 50)
        print("      PERSONAL EXPENSE TRACKER SYSTEM")
        print("=" * 50)

        print("1. Expense Management")
        print("2. Income Management")
        print("3. Budget Management")
        print("4. Change Password")
        print("5. Backup Management")
        print("6. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            expense_menu()

        elif choice == "2":

            income_menu()

        elif choice == "3":

            budget_menu()

        elif choice == "4":

            change_password()

        elif choice == "5":

            backup_menu()

        elif choice == "6":

            logout()

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main Menu
# ==========================================

def main():

    initialize_database()

    while True:

        print("\n")
        print("=" * 60)
        print("      ADVANCED PERSONAL EXPENSE TRACKER")
        print("=" * 60)

        print("1. User Registration")
        print("2. User Login")
        print("3. Forgot Password")
        print("4. Admin Login")
        print("5. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            register_user()

        elif choice == "2":

            user = login()

            if user:

                user_dashboard()

        elif choice == "3":

            forgot_password()

        elif choice == "4":

            admin_login()

        elif choice == "5":

            print("\nThank You For Using Expense Tracker.")
            print("Have a Nice Day!")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    main()