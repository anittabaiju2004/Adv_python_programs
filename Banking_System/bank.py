# bank.py

from database import initialize_database

from account import (
    register_account,
    customer_dashboard
)

from auth import (
    customer_login,
    admin_login
)

from admin import (
    admin_dashboard
)


# ==========================================
# Welcome Screen
# ==========================================

def welcome():

    print("\n")
    print("=" * 70)
    print("             BANK MANAGEMENT SYSTEM")
    print("=" * 70)
    print("      Advanced Banking Using Python & JSON")
    print("=" * 70)


# ==========================================
# About System
# ==========================================

def about():

    print("\n========== ABOUT ==========\n")

    print("Project Name : Bank Management System")
    print("Language     : Python")
    print("Database     : JSON File")
    print("Version      : 1.0")
    print("Type         : Console Application")


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

            if admin_login():

                admin_dashboard()

        elif choice == "4":

            about()

        elif choice == "5":

            print("\n===================================")
            print("Thank You For Using")
            print("BANK MANAGEMENT SYSTEM")
            print("Visit Again!")
            print("===================================")

            break

        else:

            print("\nInvalid Choice. Please Try Again.")


# ==========================================
# Start Program
# ==========================================

if __name__ == "__main__":

    main()