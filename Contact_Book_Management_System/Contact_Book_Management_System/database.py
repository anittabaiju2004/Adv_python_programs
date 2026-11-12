# JSON database helpers
# database.py

import json
import os


# ==========================================
# Data Folder
# ==========================================

DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)


# ==========================================
# JSON Files
# ==========================================

CONTACT_FILE = os.path.join(
    DATA_FOLDER,
    "contacts.json"
)

ADMIN_FILE = os.path.join(
    DATA_FOLDER,
    "admins.json"
)


# ==========================================
# Initialize Database
# ==========================================

def initialize_database():

    if not os.path.exists(CONTACT_FILE):

        with open(
            CONTACT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                [],
                file,
                indent=4
            )

    if not os.path.exists(ADMIN_FILE):

        default_admin = [

            {

                "username": "admin",
                "password": "admin123"

            }

        ]

        with open(
            ADMIN_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                default_admin,
                file,
                indent=4
            )


# ==========================================
# Load Contacts
# ==========================================

def get_contacts():

    try:

        with open(
            CONTACT_FILE,
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
# Save Contacts
# ==========================================

def save_contacts(contacts):

    with open(

        CONTACT_FILE,
        "w",
        encoding="utf-8"

    ) as file:

        json.dump(

            contacts,
            file,
            indent=4

        )


# ==========================================
# Load Admins
# ==========================================

def get_admins():

    try:

        with open(

            ADMIN_FILE,
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
# Save Admins
# ==========================================

def save_admins(admins):

    with open(

        ADMIN_FILE,
        "w",
        encoding="utf-8"

    ) as file:

        json.dump(

            admins,
            file,
            indent=4

        )


# ==========================================
# Database Information
# ==========================================

def database_information():

    print("\n")
    print("=" * 50)
    print("      DATABASE INFORMATION")
    print("=" * 50)

    print("Contacts File :", CONTACT_FILE)
    print("Admins File   :", ADMIN_FILE)

    print(
        "Total Contacts :",
        len(get_contacts())
    )

    print(
        "Total Admins   :",
        len(get_admins())
    )


# ==========================================
# Clear Contacts
# ==========================================

def clear_contacts():

    save_contacts([])

    print("\nAll Contacts Deleted Successfully.")


# ==========================================
# Reset Database
# ==========================================

def reset_database():

    save_contacts([])

    save_admins([

        {

            "username": "admin",
            "password": "admin123"

        }

    ])

    print("\nDatabase Reset Successfully.")


# ==========================================
# Database Backup Copy
# ==========================================

def export_database():

    contacts = get_contacts()

    admins = get_admins()

    return {

        "contacts": contacts,

        "admins": admins

    }


# ==========================================
# Import Database
# ==========================================

def import_database(data):

    save_contacts(

        data.get(
            "contacts",
            []
        )

    )

    save_admins(

        data.get(
            "admins",
            []
        )

    )

    print("\nDatabase Imported Successfully.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    initialize_database()

    database_information()