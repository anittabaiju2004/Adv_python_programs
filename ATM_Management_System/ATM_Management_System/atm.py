# Main entry point
# atm.py

from database import initialize_database

from account import (
    register_account,
    customer_login,
    customer_dashboard
)

from admin import admin_login


# ==========================================
# Welcome Screen
# ==========================================

def welcome():

    print("\n")
    print("=" * 70)
    print("          ADVANCED ATM MANAGEMENT SYSTEM")
    print("=" * 70)
    print("      Advanced ATM Using Python & JSON")
    print("=" * 70)


# ==========================================
# About System
# ==========================================

def about():

    print("\n========== ABOUT ==========")

    print("Project : ATM Management System")
    print("Version : 1.0")
    print("Language: Python")
    print("Database: JSON")
    print("Developer: Student Project")


# ==========================================
# Main Menu
# ==========================================

def main():

    initialize_database()

    while True:

        welcome()

        print("\nMAIN MENU\n")

        print("1. Register New Account")
        print("2. Customer Login")
        print("3. Admin Login")
        print("4. About")
        print("5. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            register_account()

        elif choice == "2":

            customer = customer_login()

            if customer:

                customer_dashboard()

        elif choice == "3":

            admin_login()

        elif choice == "4":

            about()

        elif choice == "5":

            print("\nThank You For Using ATM Management System.")
            print("Visit Again!")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    main()