# Main application
# main.py (Part 1)

import os
import sys
from datetime import datetime

from database import (
    initialize_database
)

from auth import (
    admin_login,
    initialize_default_admin
)


# ==========================================
# Clear Screen
# ==========================================

def clear_screen():

    os.system(

        "cls"

        if os.name == "nt"

        else "clear"

    )


# ==========================================
# Welcome Screen
# ==========================================

def welcome_screen():

    clear_screen()

    print("\n")

    print("=" * 70)

    print("        HOTEL BOOKING MANAGEMENT SYSTEM")

    print("=" * 70)

    print("Version      : 1.0")

    print("Database     : JSON File")

    print("Language     : Python")

    print(

        "Started At   :",

        datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        )

    )

    print("=" * 70)


# ==========================================
# Initialize Application
# ==========================================

def initialize_application():

    print("\nInitializing Application...")

    initialize_database()

    initialize_default_admin()

    print("Application Ready.")


# ==========================================
# Administrator Login
# ==========================================

def login():

    print("\n")

    print("=" * 70)

    print("           ADMIN LOGIN")

    print("=" * 70)

    attempts = 3

    while attempts > 0:

        if admin_login():

            print("\nAccess Granted.")

            return True

        attempts -= 1

        print(

            f"Remaining Attempts : {attempts}"

        )

    print("\nToo Many Failed Login Attempts.")

    return False


# ==========================================
# Main Dashboard
# ==========================================

def dashboard():

    print("\n")

    print("=" * 70)

    print("            MAIN DASHBOARD")

    print("=" * 70)

    print("1. Customer Management")

    print("2. Room Management")

    print("3. Booking Management")

    print("4. Invoice Management")

    print("5. Staff Management")

    print("6. Reports")

    print("7. Administration")

    print("8. Backup")

    print("9. Database")

    print("10. Exit")

    print("=" * 70)


# ==========================================
# Start Application
# ==========================================

def start():

    welcome_screen()

    initialize_application()

    if not login():

        sys.exit()

    print("\nLogin Successful.")

    dashboard()


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    start()
# ==========================================
# Module Imports
# ==========================================

from customer import customer_menu

from room import room_menu

from booking import booking_menu

from invoice import invoice_menu

from staff import staff_menu

from report import report_menu


# ==========================================
# Main Menu
# ==========================================

def main_menu():

    while True:

        print("\n")
        print("=" * 70)
        print("       HOTEL MANAGEMENT SYSTEM")
        print("=" * 70)

        print("1. Customer Management")

        print("2. Room Management")

        print("3. Booking Management")

        print("4. Invoice Management")

        print("5. Staff Management")

        print("6. Reports")

        print("7. Next Menu")

        print("8. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            customer_menu()

        elif choice == "2":

            room_menu()

        elif choice == "3":

            booking_menu()

        elif choice == "4":

            invoice_menu()

        elif choice == "5":

            staff_menu()

        elif choice == "6":

            report_menu()

        elif choice == "7":

            return

        elif choice == "8":

            print("\nThank You For Using")

            print("Hotel Booking Management System")

            exit()

        else:

            print("\nInvalid Choice.")


# ==========================================
# Run Main Menu
# ==========================================

def run_application():

    welcome_screen()

    initialize_application()

    if login():

        main_menu()

    else:

        print("\nAccess Denied.")
# ==========================================
# Additional Module Imports
# ==========================================

from admin import administrator_panel

from backup import backup_menu

from database import database_menu

from auth import logout


# ==========================================
# System Information
# ==========================================

def system_information():

    print("\n")
    print("=" * 70)
    print("      HOTEL BOOKING MANAGEMENT SYSTEM")
    print("=" * 70)

    print("Project   : Hotel Booking Management System")
    print("Version   : 1.0")
    print("Language  : Python")
    print("Database  : JSON")
    print("Developer : Student Project")

    print("\nModules")

    print("-" * 70)

    print("✓ Authentication")
    print("✓ Customer Management")
    print("✓ Room Management")
    print("✓ Booking Management")
    print("✓ Invoice Management")
    print("✓ Staff Management")
    print("✓ Reports")
    print("✓ Backup")
    print("✓ Database Management")

    print("=" * 70)


# ==========================================
# Administration Menu
# ==========================================

def administration_menu():

    while True:

        print("\n")
        print("=" * 70)
        print("          ADMINISTRATION")
        print("=" * 70)

        print("1. Admin Panel")

        print("2. Backup Management")

        print("3. Database Management")

        print("4. System Information")

        print("5. Logout")

        print("6. Back")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            administrator_panel()

        elif choice == "2":

            backup_menu()

        elif choice == "3":

            database_menu()

        elif choice == "4":

            system_information()

        elif choice == "5":

            logout()

            print("\nLogged Out Successfully.")

            if login():

                continue

            else:

                break

        elif choice == "6":

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Complete Application
# ==========================================

def application():

    welcome_screen()

    initialize_application()

    if not login():

        print("\nAccess Denied.")

        return

    while True:

        print("\n")
        print("=" * 70)
        print("      HOTEL BOOKING MANAGEMENT SYSTEM")
        print("=" * 70)

        print("1. Customer Management")

        print("2. Room Management")

        print("3. Booking Management")

        print("4. Invoice Management")

        print("5. Staff Management")

        print("6. Reports")

        print("7. Administration")

        print("8. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            customer_menu()

        elif choice == "2":

            room_menu()

        elif choice == "3":

            booking_menu()

        elif choice == "4":

            invoice_menu()

        elif choice == "5":

            staff_menu()

        elif choice == "6":

            report_menu()

        elif choice == "7":

            administration_menu()

        elif choice == "8":

            print("\nThank You For Using")

            print("Hotel Booking Management System")

            print("Have a Nice Day!")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    application()