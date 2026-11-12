# Contact management module
# contact.py (Part 1)

from database import (
    get_contacts,
    save_contacts
)

from utils import (
    generate_contact_id,
    is_valid_phone,
    is_valid_email
)


# ==========================================
# Add New Contact
# ==========================================

def add_contact():

    contacts = get_contacts()

    print("\n========== ADD NEW CONTACT ==========\n")

    name = input("Enter Name : ").strip()

    phone = input("Enter Phone Number : ").strip()

    if not is_valid_phone(phone):

        print("Invalid Phone Number.")

        return

    for contact in contacts:

        if contact["phone"] == phone:

            print("Phone Number Already Exists.")

            return

    email = input("Enter Email Address : ").strip()

    if not is_valid_email(email):

        print("Invalid Email Address.")

        return

    for contact in contacts:

        if contact["email"].lower() == email.lower():

            print("Email Already Exists.")

            return

    category = input(
        "Category (Family/Friend/Office/Others) : "
    ).strip()

    favorite = input(
        "Favorite (Yes/No) : "
    ).strip().capitalize()

    if favorite not in ["Yes", "No"]:

        favorite = "No"

    contact = {

        "contact_id": generate_contact_id(contacts),
        "name": name,
        "phone": phone,
        "email": email,
        "category": category,
        "favorite": favorite

    }

    contacts.append(contact)

    save_contacts(contacts)

    print("\nContact Added Successfully.")
    print("Contact ID :", contact["contact_id"])


# ==========================================
# View All Contacts
# ==========================================

def view_contacts():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    print("\n========== CONTACT LIST ==========\n")

    print(
        "{:<8} {:<20} {:<15} {:<30}".format(
            "ID",
            "Name",
            "Phone",
            "Email"
        )
    )

    print("-" * 80)

    for contact in contacts:

        print(
            "{:<8} {:<20} {:<15} {:<30}".format(
                contact["contact_id"],
                contact["name"],
                contact["phone"],
                contact["email"]
            )
        )


# ==========================================
# Search Contact by Name
# ==========================================

def search_contact():

    contacts = get_contacts()

    keyword = input(
        "\nEnter Contact Name : "
    ).strip().lower()

    found = False

    print("\n========== SEARCH RESULT ==========\n")

    for contact in contacts:

        if keyword in contact["name"].lower():

            found = True

            print("-" * 50)
            print("Contact ID :", contact["contact_id"])
            print("Name       :", contact["name"])
            print("Phone      :", contact["phone"])
            print("Email      :", contact["email"])
            print("Category   :", contact["category"])
            print("Favorite   :", contact["favorite"])

    if not found:

        print("Contact Not Found.")


# ==========================================
# Search Contact by Phone
# ==========================================

def search_phone():

    contacts = get_contacts()

    phone = input(
        "\nEnter Phone Number : "
    ).strip()

    for contact in contacts:

        if contact["phone"] == phone:

            print("\n========== CONTACT FOUND ==========\n")

            print("Contact ID :", contact["contact_id"])
            print("Name       :", contact["name"])
            print("Phone      :", contact["phone"])
            print("Email      :", contact["email"])
            print("Category   :", contact["category"])
            print("Favorite   :", contact["favorite"])

            return

    print("Contact Not Found.")
# ==========================================
# Update Contact
# ==========================================

def update_contact():

    contacts = get_contacts()

    print("\n========== UPDATE CONTACT ==========\n")

    contact_id = input("Enter Contact ID : ").strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            print("\nLeave blank to keep existing value.\n")

            name = input(
                f"Name [{contact['name']}] : "
            ).strip()

            if name:

                contact["name"] = name

            phone = input(
                f"Phone [{contact['phone']}] : "
            ).strip()

            if phone:

                if not is_valid_phone(phone):

                    print("Invalid Phone Number.")

                    return

                for c in contacts:

                    if (
                        c["phone"] == phone and
                        c["contact_id"] != contact_id
                    ):

                        print("Phone Number Already Exists.")

                        return

                contact["phone"] = phone

            email = input(
                f"Email [{contact['email']}] : "
            ).strip()

            if email:

                if not is_valid_email(email):

                    print("Invalid Email Address.")

                    return

                for c in contacts:

                    if (
                        c["email"].lower() == email.lower() and
                        c["contact_id"] != contact_id
                    ):

                        print("Email Already Exists.")

                        return

                contact["email"] = email

            category = input(
                f"Category [{contact['category']}] : "
            ).strip()

            if category:

                contact["category"] = category

            favorite = input(
                f"Favorite [{contact['favorite']}] (Yes/No): "
            ).strip().capitalize()

            if favorite in ["Yes", "No"]:

                contact["favorite"] = favorite

            save_contacts(contacts)

            print("\nContact Updated Successfully.")

            return

    print("Contact Not Found.")


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
            print("-" * 30)
            print("Name  :", contact["name"])
            print("Phone :", contact["phone"])

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
# Search Contact by Email
# ==========================================

def search_email():

    contacts = get_contacts()

    email = input(
        "\nEnter Email Address : "
    ).strip().lower()

    for contact in contacts:

        if contact["email"].lower() == email:

            print("\n========== CONTACT FOUND ==========\n")

            print("Contact ID :", contact["contact_id"])
            print("Name       :", contact["name"])
            print("Phone      :", contact["phone"])
            print("Email      :", contact["email"])
            print("Category   :", contact["category"])
            print("Favorite   :", contact["favorite"])

            return

    print("Contact Not Found.")


# ==========================================
# View Contact Details
# ==========================================

def contact_details():

    contacts = get_contacts()

    contact_id = input(
        "\nEnter Contact ID : "
    ).strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

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

            return

    print("Contact Not Found.")


# ==========================================
# Total Contacts
# ==========================================

def total_contacts():

    contacts = get_contacts()

    print("\nTotal Contacts :", len(contacts))
# ==========================================
# Mark Contact as Favorite
# ==========================================

def add_favorite():

    contacts = get_contacts()

    print("\n========== ADD TO FAVORITES ==========\n")

    contact_id = input("Enter Contact ID : ").strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            if contact["favorite"] == "Yes":

                print("Contact Already in Favorites.")

                return

            contact["favorite"] = "Yes"

            save_contacts(contacts)

            print("\nContact Added to Favorites Successfully.")

            return

    print("Contact Not Found.")


# ==========================================
# Remove Favorite Contact
# ==========================================

def remove_favorite():

    contacts = get_contacts()

    print("\n========== REMOVE FAVORITE ==========\n")

    contact_id = input("Enter Contact ID : ").strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            if contact["favorite"] == "No":

                print("Contact is Not in Favorites.")

                return

            contact["favorite"] = "No"

            save_contacts(contacts)

            print("\nFavorite Removed Successfully.")

            return

    print("Contact Not Found.")


# ==========================================
# View Favorite Contacts
# ==========================================

def view_favorites():

    contacts = get_contacts()

    favorites = [
        contact
        for contact in contacts
        if contact["favorite"] == "Yes"
    ]

    if len(favorites) == 0:

        print("\nNo Favorite Contacts Found.")

        return

    print("\n========== FAVORITE CONTACTS ==========\n")

    print("{:<8} {:<20} {:<15}".format(
        "ID",
        "Name",
        "Phone"
    ))

    print("-" * 50)

    for contact in favorites:

        print("{:<8} {:<20} {:<15}".format(
            contact["contact_id"],
            contact["name"],
            contact["phone"]
        ))


# ==========================================
# View Contacts by Category
# ==========================================

def view_category():

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

            print("ID       :", contact["contact_id"])
            print("Name     :", contact["name"])
            print("Phone    :", contact["phone"])
            print("Email    :", contact["email"])

    if not found:

        print("No Contacts Found.")


# ==========================================
# Change Contact Category
# ==========================================

def change_category():

    contacts = get_contacts()

    print("\n========== CHANGE CATEGORY ==========\n")

    contact_id = input("Enter Contact ID : ").strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            print(
                f"Current Category : {contact['category']}"
            )

            new_category = input(
                "New Category : "
            ).strip()

            if new_category == "":

                print("Category Cannot Be Empty.")

                return

            contact["category"] = new_category

            save_contacts(contacts)

            print("\nCategory Updated Successfully.")

            return

    print("Contact Not Found.")


# ==========================================
# Category Statistics
# ==========================================

def category_statistics():

    contacts = get_contacts()

    statistics = {}

    for contact in contacts:

        category = contact["category"]

        if category in statistics:

            statistics[category] += 1

        else:

            statistics[category] = 1

    print("\n========== CATEGORY STATISTICS ==========\n")

    if len(statistics) == 0:

        print("No Contacts Available.")

        return

    for category, count in statistics.items():

        print(f"{category:<15} : {count}")


# ==========================================
# Favorite Statistics
# ==========================================

def favorite_statistics():

    contacts = get_contacts()

    total = len(contacts)

    favorites = len([
        c
        for c in contacts
        if c["favorite"] == "Yes"
    ])

    print("\n========== FAVORITE STATISTICS ==========\n")

    print("Total Contacts     :", total)
    print("Favorite Contacts  :", favorites)
    print("Normal Contacts    :", total - favorites)
import csv

from report import (
    generate_contact_pdf
)


# ==========================================
# Export Contacts to CSV
# ==========================================

def export_contacts_csv():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    filename = "contacts_export.csv"

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Contact ID",
            "Name",
            "Phone",
            "Email",
            "Category",
            "Favorite"
        ])

        for contact in contacts:

            writer.writerow([

                contact["contact_id"],
                contact["name"],
                contact["phone"],
                contact["email"],
                contact["category"],
                contact["favorite"]

            ])

    print("\nContacts Exported Successfully.")
    print("File :", filename)


# ==========================================
# Import Contacts from CSV
# ==========================================

def import_contacts_csv():

    contacts = get_contacts()

    filename = input(
        "\nEnter CSV File Name : "
    ).strip()

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            count = 0

            for row in reader:

                duplicate = False

                for contact in contacts:

                    if contact["phone"] == row["Phone"]:

                        duplicate = True
                        break

                if duplicate:

                    continue

                contacts.append({

                    "contact_id": generate_contact_id(contacts),
                    "name": row["Name"],
                    "phone": row["Phone"],
                    "email": row["Email"],
                    "category": row["Category"],
                    "favorite": row["Favorite"]

                })

                count += 1

        save_contacts(contacts)

        print(f"\n{count} Contacts Imported Successfully.")

    except FileNotFoundError:

        print("CSV File Not Found.")


# ==========================================
# Export Contacts to PDF
# ==========================================

def export_contacts_pdf():

    generate_contact_pdf()


# ==========================================
# Contact Statistics
# ==========================================

def contact_statistics():

    contacts = get_contacts()

    favorites = len([
        c for c in contacts
        if c["favorite"] == "Yes"
    ])

    print("\n========== CONTACT STATISTICS ==========\n")

    print("Total Contacts    :", len(contacts))
    print("Favorite Contacts :", favorites)
    print("Normal Contacts   :", len(contacts)-favorites)


# ==========================================
# Contact Dashboard
# ==========================================

def contact_dashboard():

    contacts = get_contacts()

    print("\n")
    print("=" * 55)
    print("       CONTACT DASHBOARD")
    print("=" * 55)

    print("Total Contacts     :", len(contacts))

    favorite = len([
        c for c in contacts
        if c["favorite"] == "Yes"
    ])

    print("Favorite Contacts :", favorite)

    categories = {}

    for contact in contacts:

        category = contact["category"]

        categories[category] = categories.get(
            category,
            0
        ) + 1

    print("\nCategory Summary")

    print("-" * 30)

    for category, count in categories.items():

        print(f"{category:<15} : {count}")


# ==========================================
# Contact Menu
# ==========================================

def contact_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("      CONTACT MANAGEMENT SYSTEM")
        print("=" * 60)

        print("1. Add Contact")
        print("2. View Contacts")
        print("3. Search by Name")
        print("4. Search by Phone")
        print("5. Search by Email")
        print("6. Update Contact")
        print("7. Delete Contact")
        print("8. Add Favorite")
        print("9. Remove Favorite")
        print("10. View Favorites")
        print("11. View Category")
        print("12. Change Category")
        print("13. Import CSV")
        print("14. Export CSV")
        print("15. Export PDF")
        print("16. Contact Statistics")
        print("17. Dashboard")
        print("18. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            add_contact()

        elif choice == "2":

            view_contacts()

        elif choice == "3":

            search_contact()

        elif choice == "4":

            search_phone()

        elif choice == "5":

            search_email()

        elif choice == "6":

            update_contact()

        elif choice == "7":

            delete_contact()

        elif choice == "8":

            add_favorite()

        elif choice == "9":

            remove_favorite()

        elif choice == "10":

            view_favorites()

        elif choice == "11":

            view_category()

        elif choice == "12":

            change_category()

        elif choice == "13":

            import_contacts_csv()

        elif choice == "14":

            export_contacts_csv()

        elif choice == "15":

            export_contacts_pdf()

        elif choice == "16":

            contact_statistics()

        elif choice == "17":

            contact_dashboard()

        elif choice == "18":

            print("\nThank You For Using Contact Book.")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    contact_menu()