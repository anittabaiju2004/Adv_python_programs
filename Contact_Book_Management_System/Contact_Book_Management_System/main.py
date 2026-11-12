# Main menu
# main.py

from database import initialize_database

from contact import (
    contact_menu
)

from auth import (
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
    print("=" * 65)
    print("       CONTACT BOOK MANAGEMENT SYSTEM")
    print("=" * 65)
    print(" Advanced Contact Book Using Python & JSON")
    print("=" * 65)


# ==========================================
# About Project
# ==========================================

def about():

    print("\n========== ABOUT ==========\n")

    print("Project Name : Contact Book Management System")
    print("Language     : Python 3")
    print("Database     : JSON File")
    print("Programming  : OOP + Modular Programming")
    print("Version      : 1.0")


# ==========================================
# Main Menu
# ==========================================

def main():

    initialize_database()

    while True:

        welcome()

        print("\nMAIN MENU\n")

        print("1. Contact Management")
        print("2. Administrator Login")
        print("3. About")
        print("4. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            contact_menu()

        elif choice == "2":

            if admin_login():

                admin_dashboard()

        elif choice == "3":

            about()

        elif choice == "4":

            print("\n")
            print("=" * 60)
            print("Thank You For Using")
            print("CONTACT BOOK MANAGEMENT SYSTEM")
            print("Visit Again!")
            print("=" * 60)

            break

        else:

            print("\nInvalid Choice. Please Try Again.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    main()