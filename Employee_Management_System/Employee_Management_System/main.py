# Main application
# main.py

from database import initialize_database

from auth import admin_login

from admin import admin_dashboard

from employee import employee_menu

from attendance import attendance_menu

from leave import leave_menu

from payroll import payroll_menu

from report import report_menu

from backup import backup_menu


# ==========================================
# Welcome Screen
# ==========================================

def welcome():

    print("\n")
    print("=" * 70)
    print("        EMPLOYEE MANAGEMENT SYSTEM")
    print("=" * 70)
    print(" Advanced Employee Record Management")
    print(" Using Python & JSON File Handling")
    print("=" * 70)


# ==========================================
# About Project
# ==========================================

def about():

    print("\n")
    print("=" * 60)
    print("            ABOUT PROJECT")
    print("=" * 60)

    print("Project   : Employee Management System")
    print("Language  : Python 3")
    print("Database  : JSON File")
    print("Concepts  :")
    print("  - Object-Oriented Programming")
    print("  - Modular Programming")
    print("  - JSON File Handling")
    print("  - Exception Handling")
    print("Version   : 1.0")

    print("=" * 60)


# ==========================================
# Main Menu
# ==========================================

def main():

    initialize_database()

    while True:

        welcome()

        print("\nMAIN MENU\n")

        print("1. Employee Management")
        print("2. Attendance Management")
        print("3. Leave Management")
        print("4. Payroll Management")
        print("5. Reports")
        print("6. Backup & Restore")
        print("7. Administrator Login")
        print("8. About")
        print("9. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            employee_menu()

        elif choice == "2":

            attendance_menu()

        elif choice == "3":

            leave_menu()

        elif choice == "4":

            payroll_menu()

        elif choice == "5":

            report_menu()

        elif choice == "6":

            backup_menu()

        elif choice == "7":

            if admin_login():

                admin_dashboard()

        elif choice == "8":

            about()

        elif choice == "9":

            print("\n")
            print("=" * 60)
            print("Thank You For Using")
            print("EMPLOYEE MANAGEMENT SYSTEM")
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