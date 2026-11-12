# JSON database
# database.py (Part 1)

import json
import os

# ==========================================
# Database Folder
# ==========================================

DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)

# ==========================================
# Database Files
# ==========================================

ROOM_FILE = os.path.join(DATA_FOLDER, "rooms.json")

CUSTOMER_FILE = os.path.join(DATA_FOLDER, "customers.json")

BOOKING_FILE = os.path.join(DATA_FOLDER, "bookings.json")

STAFF_FILE = os.path.join(DATA_FOLDER, "staff.json")

ADMIN_FILE = os.path.join(DATA_FOLDER, "admins.json")

PAYMENT_FILE = os.path.join(DATA_FOLDER, "payments.json")

INVOICE_FILE = os.path.join(DATA_FOLDER, "invoices.json")


# ==========================================
# Create JSON File
# ==========================================

def create_file(filename):

    if not os.path.exists(filename):

        with open(

            filename,

            "w",

            encoding="utf-8"

        ) as file:

            json.dump([], file, indent=4)


# ==========================================
# Initialize Database
# ==========================================

def initialize_database():

    create_file(ROOM_FILE)

    create_file(CUSTOMER_FILE)

    create_file(BOOKING_FILE)

    create_file(STAFF_FILE)

    create_file(ADMIN_FILE)

    create_file(PAYMENT_FILE)

    create_file(INVOICE_FILE)

    print("\nDatabase Initialized Successfully.")


# ==========================================
# Read JSON File
# ==========================================

def read_json(filename):

    try:

        with open(

            filename,

            "r",

            encoding="utf-8"

        ) as file:

            return json.load(file)

    except (

        FileNotFoundError,

        json.JSONDecodeError

    ):

        return []


# ==========================================
# Write JSON File
# ==========================================

def write_json(

    filename,

    data

):

    with open(

        filename,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            data,

            file,

            indent=4

        )


# ==========================================
# Database Information
# ==========================================

def database_info():

    print("\n")
    print("=" * 60)
    print("         DATABASE INFORMATION")
    print("=" * 60)

    print("Database Type : JSON File")

    print("Storage Folder :", DATA_FOLDER)

    print("Files")

    print("---------------------------")

    print("rooms.json")

    print("customers.json")

    print("bookings.json")

    print("staff.json")

    print("admins.json")

    print("payments.json")

    print("invoices.json")

    print("=" * 60)
# ==========================================
# Rooms Database
# ==========================================

def get_rooms():

    return read_json(ROOM_FILE)


def save_rooms(data):

    write_json(ROOM_FILE, data)


# ==========================================
# Customers Database
# ==========================================

def get_customers():

    return read_json(CUSTOMER_FILE)


def save_customers(data):

    write_json(CUSTOMER_FILE, data)


# ==========================================
# Bookings Database
# ==========================================

def get_bookings():

    return read_json(BOOKING_FILE)


def save_bookings(data):

    write_json(BOOKING_FILE, data)


# ==========================================
# Staff Database
# ==========================================

def get_staff():

    return read_json(STAFF_FILE)


def save_staff(data):

    write_json(STAFF_FILE, data)


# ==========================================
# Admin Database
# ==========================================

def get_admins():

    return read_json(ADMIN_FILE)


def save_admins(data):

    write_json(ADMIN_FILE, data)


# ==========================================
# Payments Database
# ==========================================

def get_payments():

    return read_json(PAYMENT_FILE)


def save_payments(data):

    write_json(PAYMENT_FILE, data)


# ==========================================
# Invoice Database
# ==========================================

def get_invoices():

    return read_json(INVOICE_FILE)


def save_invoices(data):

    write_json(INVOICE_FILE, data)


# ==========================================
# Database Record Count
# ==========================================

def database_statistics():

    print("\n")
    print("=" * 60)
    print("       DATABASE STATISTICS")
    print("=" * 60)

    print("Rooms      :", len(get_rooms()))

    print("Customers  :", len(get_customers()))

    print("Bookings   :", len(get_bookings()))

    print("Staff      :", len(get_staff()))

    print("Admins     :", len(get_admins()))

    print("Payments   :", len(get_payments()))

    print("Invoices   :", len(get_invoices()))

    print("=" * 60)
# ==========================================
# Verify Database Files
# ==========================================

def verify_database():

    print("\n")
    print("=" * 60)
    print("      DATABASE VERIFICATION")
    print("=" * 60)

    files = [

        ROOM_FILE,

        CUSTOMER_FILE,

        BOOKING_FILE,

        STAFF_FILE,

        ADMIN_FILE,

        PAYMENT_FILE,

        INVOICE_FILE

    ]

    for file in files:

        if os.path.exists(file):

            print(os.path.basename(file), " : OK")

        else:

            print(os.path.basename(file), " : Missing")


# ==========================================
# Database Health Check
# ==========================================

def database_health():

    print("\n")
    print("=" * 60)
    print("        DATABASE HEALTH")
    print("=" * 60)

    verify_database()

    print("\nDatabase Status : Healthy")


# ==========================================
# Reset Database
# ==========================================

def reset_database():

    confirm = input(

        "\nReset Entire Database? (Y/N): "

    ).strip().upper()

    if confirm != "Y":

        print("Reset Cancelled.")

        return

    write_json(ROOM_FILE, [])

    write_json(CUSTOMER_FILE, [])

    write_json(BOOKING_FILE, [])

    write_json(STAFF_FILE, [])

    write_json(ADMIN_FILE, [])

    write_json(PAYMENT_FILE, [])

    write_json(INVOICE_FILE, [])

    print("\nDatabase Reset Successfully.")


# ==========================================
# Clear Specific Database
# ==========================================

def clear_database():

    print("\n")
    print("=" * 60)
    print("        CLEAR DATABASE")
    print("=" * 60)

    print("1. Rooms")

    print("2. Customers")

    print("3. Bookings")

    print("4. Staff")

    print("5. Admins")

    print("6. Payments")

    print("7. Invoices")

    choice = input("\nEnter Choice : ")

    mapping = {

        "1": ROOM_FILE,

        "2": CUSTOMER_FILE,

        "3": BOOKING_FILE,

        "4": STAFF_FILE,

        "5": ADMIN_FILE,

        "6": PAYMENT_FILE,

        "7": INVOICE_FILE

    }

    if choice not in mapping:

        print("Invalid Choice.")

        return

    confirm = input(

        "Clear Selected Database? (Y/N): "

    ).strip().upper()

    if confirm != "Y":

        print("Cancelled.")

        return

    write_json(mapping[choice], [])

    print("\nDatabase Cleared Successfully.")


# ==========================================
# Database Backup Verification
# ==========================================

def backup_verification():

    backup_folder = "backups"

    print("\n")
    print("=" * 60)
    print("      BACKUP VERIFICATION")
    print("=" * 60)

    if os.path.exists(backup_folder):

        backups = [

            folder

            for folder in os.listdir(backup_folder)

            if os.path.isdir(

                os.path.join(

                    backup_folder,

                    folder

                )

            )

        ]

        print("Available Backups :", len(backups))

    else:

        print("Backup Folder Not Found.")


# ==========================================
# Database Management Menu
# ==========================================

def database_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("      DATABASE MANAGEMENT")
        print("=" * 60)

        print("1. Initialize Database")

        print("2. Database Information")

        print("3. Database Statistics")

        print("4. Verify Database")

        print("5. Database Health")

        print("6. Reset Database")

        print("7. Clear Database")

        print("8. Backup Verification")

        print("9. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            initialize_database()

        elif choice == "2":

            database_info()

        elif choice == "3":

            database_statistics()

        elif choice == "4":

            verify_database()

        elif choice == "5":

            database_health()

        elif choice == "6":

            reset_database()

        elif choice == "7":

            clear_database()

        elif choice == "8":

            backup_verification()

        elif choice == "9":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    database_menu()