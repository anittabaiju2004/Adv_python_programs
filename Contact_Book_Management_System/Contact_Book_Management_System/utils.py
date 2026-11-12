# Utility functions
# utils.py (Part 1)

import hashlib
from datetime import datetime


# ==========================================
# Generate Contact ID
# ==========================================

def generate_contact_id(contacts):

    if len(contacts) == 0:

        return "CNT001"

    numbers = []

    for contact in contacts:

        try:

            numbers.append(

                int(
                    contact["contact_id"].replace(
                        "CNT",
                        ""
                    )
                )

            )

        except:

            continue

    if len(numbers) == 0:

        return "CNT001"

    return f"CNT{max(numbers)+1:03d}"


# ==========================================
# Current Date
# ==========================================

def current_date():

    return datetime.now().strftime("%Y-%m-%d")


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
# Generate Reference Number
# ==========================================

def generate_reference_number():

    return "REF" + datetime.now().strftime(

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
# Generate Report ID
# ==========================================

def generate_report_id():

    return "RPT" + datetime.now().strftime(

        "%Y%m%d%H%M%S"

    )


# ==========================================
# Generate Export ID
# ==========================================

def generate_export_id():

    return "EXP" + datetime.now().strftime(

        "%Y%m%d%H%M%S"

    )


# ==========================================
# Application Information
# ==========================================

def application_info():

    print("\n")
    print("=" * 55)
    print(" CONTACT BOOK MANAGEMENT SYSTEM ")
    print("=" * 55)
    print("Language : Python")
    print("Database : JSON")
    print("Version  : 1.0")
    print("=" * 55)
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
# Validate Email Address
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
# Validate Category
# ==========================================

def is_valid_category(category):

    categories = [

        "Family",
        "Friend",
        "Office",
        "Business",
        "Emergency",
        "Others"

    ]

    return category.capitalize() in categories


# ==========================================
# Validate Favorite
# ==========================================

def is_valid_favorite(value):

    return value.capitalize() in [

        "Yes",
        "No"

    ]


# ==========================================
# Find Contact
# ==========================================

def find_contact(

    contacts,
    contact_id

):

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            return contact

    return None


# ==========================================
# Contact Exists
# ==========================================

def contact_exists(

    contacts,
    phone

):

    for contact in contacts:

        if contact["phone"] == phone:

            return True

    return False


# ==========================================
# Display Contact
# ==========================================

def display_contact(contact):

    print("\n")

    print("=" * 50)
    print("         CONTACT DETAILS")
    print("=" * 50)

    print("Contact ID :", contact["contact_id"])
    print("Name       :", contact["name"])
    print("Phone      :", contact["phone"])
    print("Email      :", contact["email"])
    print("Category   :", contact["category"])
    print("Favorite   :", contact["favorite"])

    print("=" * 50)


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
# Contact Count
# ==========================================

def total_contacts(contacts):

    return len(contacts)


# ==========================================
# Favorite Count
# ==========================================

def total_favorites(contacts):

    return len([

        contact

        for contact in contacts

        if contact["favorite"] == "Yes"

    ])


# ==========================================
# Display Summary
# ==========================================

def display_summary(contacts):

    print("\n")

    print("=" * 50)
    print("         CONTACT SUMMARY")
    print("=" * 50)

    print("Total Contacts    :", total_contacts(contacts))
    print("Favorite Contacts :", total_favorites(contacts))

    print("=" * 50)
# ==========================================
# Imports
# ==========================================

import os
from datetime import datetime


# ==========================================
# Contact Statistics
# ==========================================

def contact_statistics(contacts):

    total = len(contacts)

    favorites = 0

    categories = {}

    for contact in contacts:

        if contact["favorite"] == "Yes":

            favorites += 1

        category = contact["category"]

        categories[category] = categories.get(
            category,
            0
        ) + 1

    print("\n")
    print("=" * 60)
    print("         CONTACT STATISTICS")
    print("=" * 60)

    print("Total Contacts     :", total)
    print("Favorite Contacts  :", favorites)
    print("Normal Contacts    :", total - favorites)

    print("\nCategory Statistics")
    print("-" * 30)

    for category, count in categories.items():

        print(f"{category:<15} : {count}")


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
    print("WELCOME TO CONTACT BOOK MANAGEMENT SYSTEM")
    print("=" * 60)


# ==========================================
# Clear Screen
# ==========================================

def clear_screen():

    os.system("cls" if os.name == "nt" else "clear")


# ==========================================
# Pause Program
# ==========================================

def pause():

    input("\nPress Enter To Continue...")


# ==========================================
# Footer
# ==========================================

def footer():

    print("\n")
    print("=" * 60)
    print("Thank You For Using")
    print("CONTACT BOOK MANAGEMENT SYSTEM")
    print("=" * 60)


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
# Show Current Date & Time
# ==========================================

def show_datetime():

    print(
        "Current Date & Time :",
        current_datetime()
    )


# ==========================================
# Display Application Version
# ==========================================

def version():

    print("\n")
    print("=" * 50)
    print("CONTACT BOOK MANAGEMENT SYSTEM")
    print("=" * 50)
    print("Version : 1.0")
    print("Language: Python")
    print("Database: JSON File")
    print("=" * 50)


# ==========================================
# Display Developer Information
# ==========================================

def developer_info():

    print("\n")
    print("=" * 50)
    print("      DEVELOPER INFORMATION")
    print("=" * 50)

    print("Project  : Contact Book Management System")
    print("Language : Python")
    print("Database : JSON File")
    print("Concepts :")
    print(" - Object-Oriented Programming")
    print(" - Modular Programming")
    print(" - JSON File Handling")
    print(" - Exception Handling")

    print("=" * 50)