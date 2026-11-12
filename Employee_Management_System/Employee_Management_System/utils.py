# Utility functions
# utils.py (Part 1)

import hashlib
from datetime import datetime


# ==========================================
# Generate Employee ID
# ==========================================

def generate_employee_id(employees):

    if len(employees) == 0:

        return "EMP001"

    numbers = []

    for employee in employees:

        try:

            numbers.append(

                int(

                    employee["employee_id"].replace(

                        "EMP",

                        ""

                    )

                )

            )

        except:

            continue

    if len(numbers) == 0:

        return "EMP001"

    return f"EMP{max(numbers)+1:03d}"


# ==========================================
# Generate Payroll ID
# ==========================================

def generate_payroll_id():

    return "PAY" + datetime.now().strftime(

        "%Y%m%d%H%M%S"

    )


# ==========================================
# Generate Report ID
# ==========================================

def generate_report_id():

    return "RPT" + datetime.now().strftime(

        "%Y%m%d%H%M%S"

    )


# ==========================================
# Generate Backup Name
# ==========================================

def generate_backup_name():

    return "Backup_" + datetime.now().strftime(

        "%Y%m%d_%H%M%S"

    )


# ==========================================
# Current Date
# ==========================================

def current_date():

    return datetime.now().strftime(

        "%Y-%m-%d"

    )


# ==========================================
# Current Date & Time
# ==========================================

def current_datetime():

    return datetime.now().strftime(

        "%Y-%m-%d %H:%M:%S"

    )


# ==========================================
# Hash Password
# ==========================================

def hash_password(password):

    return hashlib.sha256(

        password.encode()

    ).hexdigest()


# ==========================================
# Verify Password
# ==========================================

def verify_password(

    password,

    hashed_password

):

    return (

        hash_password(password)

        == hashed_password

    )


# ==========================================
# Application Information
# ==========================================

def application_info():

    print("\n")

    print("=" * 60)

    print("     EMPLOYEE MANAGEMENT SYSTEM")

    print("=" * 60)

    print("Language : Python")

    print("Database : JSON File")

    print("Version  : 1.0")

    print("=" * 60)
# ==========================================
# Validate Phone Number
# ==========================================

def is_valid_phone(phone):

    if len(phone) != 10:

        return False

    if not phone.isdigit():

        return False

    return True


# ==========================================
# Validate Email
# ==========================================

def is_valid_email(email):

    if "@" not in email:

        return False

    if "." not in email:

        return False

    return True


# ==========================================
# Validate Password
# ==========================================

def is_valid_password(password):

    return len(password) >= 6


# ==========================================
# Find Employee by ID
# ==========================================

def find_employee(

    employees,

    employee_id

):

    for employee in employees:

        if employee["employee_id"] == employee_id:

            return employee

    return None


# ==========================================
# Employee Exists
# ==========================================

def employee_exists(

    employees,

    employee_id

):

    for employee in employees:

        if employee["employee_id"] == employee_id:

            return True

    return False


# ==========================================
# Display Employee Details
# ==========================================

def display_employee(employee):

    print("\n")

    print("=" * 60)
    print("         EMPLOYEE DETAILS")
    print("=" * 60)

    print("Employee ID :", employee["employee_id"])
    print("Name        :", employee["name"])
    print("Department  :", employee["department"])
    print("Designation :", employee["designation"])
    print("Phone       :", employee["phone"])
    print("Email       :", employee["email"])
    print("Salary      : ₹", employee["salary"])
    print("Present     :", employee["present_days"])
    print("Absent      :", employee["absent_days"])
    print("Leave Days  :", employee["leave_days"])

    print("=" * 60)


# ==========================================
# Print Header
# ==========================================

def print_header(title):

    print("\n")

    print("=" * 60)

    print(title.center(60))

    print("=" * 60)


# ==========================================
# Print Divider
# ==========================================

def print_divider():

    print("-" * 60)


# ==========================================
# Total Employees
# ==========================================

def total_employees(employees):

    return len(employees)


# ==========================================
# Employee Summary
# ==========================================

def employee_summary(employees):

    print("\n")

    print("=" * 60)
    print("        EMPLOYEE SUMMARY")
    print("=" * 60)

    print("Total Employees :", len(employees))

    if len(employees):

        total_salary = sum(

            employee["salary"]

            for employee in employees

        )

        print("Total Salary    : ₹", total_salary)

        print(

            "Average Salary : ₹",

            round(

                total_salary /

                len(employees),

                2

            )

        )

    print("=" * 60)


# ==========================================
# Employee List
# ==========================================

def employee_list(employees):

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    print("\n")

    print("=" * 80)

    print(

        "{:<8} {:<20} {:<15} {:<15}".format(

            "ID",

            "Name",

            "Department",

            "Designation"

        )

    )

    print("=" * 80)

    for employee in employees:

        print(

            "{:<8} {:<20} {:<15} {:<15}".format(

                employee["employee_id"],

                employee["name"],

                employee["department"],

                employee["designation"]

            )

        )

    print("=" * 80)
# ==========================================
# Imports
# ==========================================

import os
from datetime import datetime


# ==========================================
# Employee Statistics
# ==========================================

def employee_statistics(employees):

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    total_salary = sum(

        employee["salary"]

        for employee in employees

    )

    highest = max(

        employees,

        key=lambda employee: employee["salary"]

    )

    lowest = min(

        employees,

        key=lambda employee: employee["salary"]

    )

    print("\n")
    print("=" * 60)
    print("        EMPLOYEE STATISTICS")
    print("=" * 60)

    print("Total Employees :", len(employees))

    print("Total Salary    : ₹", total_salary)

    print(

        "Average Salary : ₹",

        round(

            total_salary /

            len(employees),

            2

        )

    )

    print("Highest Salary  : ₹", highest["salary"])
    print("Highest Paid    :", highest["name"])

    print("Lowest Salary   : ₹", lowest["salary"])
    print("Lowest Paid     :", lowest["name"])


# ==========================================
# Greeting Message
# ==========================================

def greeting():

    hour = datetime.now().hour

    if hour < 12:

        return "Good Morning"

    elif hour < 17:

        return "Good Afternoon"

    else:

        return "Good Evening"


# ==========================================
# Welcome Banner
# ==========================================

def welcome_message():

    print("\n")

    print("=" * 60)

    print(greeting())

    print("WELCOME TO EMPLOYEE MANAGEMENT SYSTEM")

    print("=" * 60)


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
# Pause Program
# ==========================================

def pause():

    input(

        "\nPress Enter To Continue..."

    )


# ==========================================
# Success Message
# ==========================================

def success(message):

    print(f"\nSUCCESS : {message}")


# ==========================================
# Error Message
# ==========================================

def error(message):

    print(f"\nERROR : {message}")


# ==========================================
# Warning Message
# ==========================================

def warning(message):

    print(f"\nWARNING : {message}")


# ==========================================
# Confirmation Prompt
# ==========================================

def confirm_action(message):

    choice = input(

        f"{message} (Y/N): "

    ).strip().upper()

    return choice == "Y"


# ==========================================
# Footer
# ==========================================

def footer():

    print("\n")

    print("=" * 60)

    print("Thank You For Using")

    print("EMPLOYEE MANAGEMENT SYSTEM")

    print("=" * 60)


# ==========================================
# Version Information
# ==========================================

def version():

    print("\n")

    print("=" * 60)

    print("EMPLOYEE MANAGEMENT SYSTEM")

    print("=" * 60)

    print("Version  : 1.0")

    print("Language : Python")

    print("Database : JSON File")

    print("=" * 60)


# ==========================================
# Developer Information
# ==========================================

def developer_info():

    print("\n")

    print("=" * 60)

    print("      DEVELOPER INFORMATION")

    print("=" * 60)

    print("Project  : Employee Management System")

    print("Language : Python")

    print("Database : JSON File")

    print("Concepts :")

    print(" - Object-Oriented Programming")

    print(" - Modular Programming")

    print(" - JSON File Handling")

    print(" - Exception Handling")

    print("=" * 60)


# ==========================================
# Show Current Date & Time
# ==========================================

def show_datetime():

    print(

        "Current Date & Time :",

        current_datetime()

    )