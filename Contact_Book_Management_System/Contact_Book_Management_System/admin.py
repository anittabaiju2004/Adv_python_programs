# Admin module
# admin.py (Part 1)

from database import (
    get_admins,
    get_contacts,
    save_contacts
)

from report import report_menu
from backup import backup_menu


# ==========================================
# Admin Login
# ==========================================

def admin_login():

    admins = get_admins()

    print("\n========== ADMIN LOGIN ==========\n")

    username = input("Username : ").strip()
    password = input("Password : ").strip()

    for admin in admins:

        if (
            admin["username"] == username and
            admin["password"] == password
        ):

            print("\nLogin Successful.")

            admin_dashboard()

            return

    print("\nInvalid Username or Password.")


# ==========================================
# View All Contacts
# ==========================================

def view_contacts():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Found.")

        return

    print("\n========== CONTACT LIST ==========\n")

    print(
        "{:<5} {:<20} {:<15} {:<30}".format(
            "ID",
            "Name",
            "Phone",
            "Email"
        )
    )

    print("-" * 75)

    for contact in contacts:

        print(
            "{:<5} {:<20} {:<15} {:<30}".format(
                contact["contact_id"],
                contact["name"],
                contact["phone"],
                contact["email"]
            )
        )


# ==========================================
# Search Contact
# ==========================================

def search_contact():

    contacts = get_contacts()

    keyword = input(
        "\nEnter Contact Name : "
    ).strip().lower()

    found = False

    for contact in contacts:

        if keyword in contact["name"].lower():

            found = True

            print("\n========== CONTACT DETAILS ==========\n")

            print("Contact ID :", contact["contact_id"])
            print("Name       :", contact["name"])
            print("Phone      :", contact["phone"])
            print("Email      :", contact["email"])
            print("Category   :", contact["category"])
            print("Favorite   :", contact["favorite"])

    if not found:

        print("\nContact Not Found.")


# ==========================================
# Admin Dashboard
# ==========================================

def admin_dashboard():

    while True:

        print("\n")
        print("=" * 55)
        print("        ADMIN DASHBOARD")
        print("=" * 55)

        print("1. View Contacts")
        print("2. Search Contact")
        print("3. Delete Contact")
        print("4. Reports")
        print("5. Backup")
        print("6. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            view_contacts()

        elif choice == "2":

            search_contact()

        elif choice == "3":

            delete_contact()

        elif choice == "4":

            report_menu()

        elif choice == "5":

            backup_menu()

        elif choice == "6":

            print("\nAdmin Logged Out Successfully.")

            break

        else:

            print("\nInvalid Choice.")
# ==========================================
# Delete Contact
# ==========================================

def delete_contact():

    contacts = get_contacts()

    print("\n========== DELETE CONTACT ==========\n")

    contact_id = input("Enter Contact ID : ").strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            print("\nContact Found")
            print("----------------------------")
            print("Name     :", contact["name"])
            print("Phone    :", contact["phone"])
            print("Email    :", contact["email"])

            confirm = input(
                "\nDelete this contact? (Y/N): "
            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")
                return

            contacts.remove(contact)

            save_contacts(contacts)

            print("\nContact Deleted Successfully.")

            return

    print("Contact Not Found.")


# ==========================================
# View Favorite Contacts
# ==========================================

def view_favorite_contacts():

    contacts = get_contacts()

    print("\n========== FAVORITE CONTACTS ==========\n")

    found = False

    for contact in contacts:

        if contact["favorite"] == "Yes":

            found = True

            print("-" * 50)
            print("ID       :", contact["contact_id"])
            print("Name     :", contact["name"])
            print("Phone    :", contact["phone"])
            print("Email    :", contact["email"])
            print("Category :", contact["category"])

    if not found:

        print("No Favorite Contacts Found.")


# ==========================================
# View Contacts by Category
# ==========================================

def view_category_contacts():

    contacts = get_contacts()

    category = input(
        "\nEnter Category : "
    ).strip().lower()

    found = False

    print(f"\n========== {category.upper()} CONTACTS ==========\n")

    for contact in contacts:

        if contact["category"].lower() == category:

            found = True

            print("-" * 50)
            print("ID    :", contact["contact_id"])
            print("Name  :", contact["name"])
            print("Phone :", contact["phone"])
            print("Email :", contact["email"])

    if not found:

        print("No Contacts Found.")


# ==========================================
# Contact Statistics
# ==========================================

def contact_statistics():

    contacts = get_contacts()

    total_contacts = len(contacts)
    favorite_count = 0

    categories = {}

    for contact in contacts:

        if contact["favorite"] == "Yes":

            favorite_count += 1

        category = contact["category"]

        if category in categories:

            categories[category] += 1

        else:

            categories[category] = 1

    print("\n========== CONTACT STATISTICS ==========\n")

    print(f"Total Contacts   : {total_contacts}")
    print(f"Favorite Contacts: {favorite_count}")

    print("\nCategory Summary")

    print("-" * 30)

    for category, count in categories.items():

        print(f"{category:<15} : {count}")


# ==========================================
# Search by Phone Number
# ==========================================

def search_by_phone():

    contacts = get_contacts()

    phone = input(
        "\nEnter Phone Number : "
    ).strip()

    for contact in contacts:

        if contact["phone"] == phone:

            print("\n========== CONTACT FOUND ==========\n")

            print("ID       :", contact["contact_id"])
            print("Name     :", contact["name"])
            print("Phone    :", contact["phone"])
            print("Email    :", contact["email"])
            print("Category :", contact["category"])
            print("Favorite :", contact["favorite"])

            return

    print("Contact Not Found.")


# ==========================================
# Search by Email
# ==========================================

def search_by_email():

    contacts = get_contacts()

    email = input(
        "\nEnter Email Address : "
    ).strip().lower()

    for contact in contacts:

        if contact["email"].lower() == email:

            print("\n========== CONTACT FOUND ==========\n")

            print("ID       :", contact["contact_id"])
            print("Name     :", contact["name"])
            print("Phone    :", contact["phone"])
            print("Email    :", contact["email"])
            print("Category :", contact["category"])
            print("Favorite :", contact["favorite"])

            return

    print("Contact Not Found.")
# ==========================================
# Generate Reports
# ==========================================

def generate_reports():

    print("\n========== REPORTS ==========\n")

    report_menu()


# ==========================================
# Create Backup
# ==========================================

def create_backup():

    print("\nCreating Database Backup...\n")

    backup_menu()


# ==========================================
# Restore Backup
# ==========================================

def restore_backup():

    print("\nRestore Database\n")

    backup_menu()


# ==========================================
# Dashboard Summary
# ==========================================

def dashboard_summary():

    contacts = get_contacts()

    total_contacts = len(contacts)
    favorites = 0

    category_count = {}

    for contact in contacts:

        if contact["favorite"] == "Yes":

            favorites += 1

        category = contact["category"]

        if category in category_count:

            category_count[category] += 1

        else:

            category_count[category] = 1

    print("\n")
    print("=" * 55)
    print("         DASHBOARD SUMMARY")
    print("=" * 55)

    print("Total Contacts    :", total_contacts)
    print("Favorite Contacts :", favorites)

    print("\nCategory Summary")

    print("-" * 30)

    for category, count in category_count.items():

        print(f"{category:<15} : {count}")


# ==========================================
# Admin Information
# ==========================================

def admin_information():

    print("\n")
    print("=" * 55)
    print("         ADMIN INFORMATION")
    print("=" * 55)

    print("Application : Contact Book Management")
    print("Database    : JSON File")
    print("Language    : Python")
    print("Version     : 1.0")
    print("Access      : Administrator")


# ==========================================
# View Recent Contacts
# ==========================================

def recent_contacts():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    print("\n========== RECENT CONTACTS ==========\n")

    recent = contacts[-5:]

    for contact in recent:

        print("-" * 50)

        print("ID       :", contact["contact_id"])
        print("Name     :", contact["name"])
        print("Phone    :", contact["phone"])
        print("Email    :", contact["email"])
        print("Category :", contact["category"])


# ==========================================
# Admin Logout
# ==========================================

def admin_logout():

    print("\n===================================")
    print("Admin Logged Out Successfully")
    print("===================================")