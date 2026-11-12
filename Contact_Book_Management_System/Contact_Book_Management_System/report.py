# CSV/PDF export
# report.py (Part 1)

import csv
import os

from database import get_contacts


# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Generate Contact Report (CSV)
# ==========================================

def generate_contact_report():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Contact_Report.csv"
    )

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

    print("\nContact Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Favorite Contacts Report (CSV)
# ==========================================

def generate_favorite_report():

    contacts = get_contacts()

    favorites = [
        contact
        for contact in contacts
        if contact["favorite"] == "Yes"
    ]

    if len(favorites) == 0:

        print("\nNo Favorite Contacts Available.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Favorite_Contacts.csv"
    )

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
            "Category"
        ])

        for contact in favorites:

            writer.writerow([

                contact["contact_id"],
                contact["name"],
                contact["phone"],
                contact["email"],
                contact["category"]

            ])

    print("\nFavorite Contacts Report Generated.")
    print("Saved To :", filename)


# ==========================================
# Report Summary
# ==========================================

def report_summary():

    contacts = get_contacts()

    total_contacts = len(contacts)

    favorite_contacts = len([
        contact
        for contact in contacts
        if contact["favorite"] == "Yes"
    ])

    categories = {}

    for contact in contacts:

        category = contact["category"]

        categories[category] = categories.get(
            category,
            0
        ) + 1

    print("\n")
    print("=" * 50)
    print("          REPORT SUMMARY")
    print("=" * 50)

    print("Total Contacts    :", total_contacts)
    print("Favorite Contacts :", favorite_contacts)

    print("\nCategory Summary")

    print("-" * 30)

    for category, count in categories.items():

        print(f"{category:<15} : {count}")


# ==========================================
# View Reports
# ==========================================

def view_reports():

    files = os.listdir(REPORT_FOLDER)

    if len(files) == 0:

        print("\nNo Reports Generated Yet.")

        return

    print("\n========== GENERATED REPORTS ==========\n")

    for index, file in enumerate(files, start=1):

        print(f"{index}. {file}")
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)


# ==========================================
# Generate Contact Report (PDF)
# ==========================================

def generate_contact_pdf():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Contact_Report.pdf"
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b>CONTACT BOOK REPORT</b>",
            styles["Title"]
        )
    )

    story.append(Spacer(1, 15))

    for contact in contacts:

        story.append(

            Paragraph(

                f"<b>{contact['name']}</b>",

                styles["Heading2"]

            )

        )

        story.append(

            Paragraph(
                f"Contact ID : {contact['contact_id']}",
                styles["BodyText"]
            )

        )

        story.append(

            Paragraph(
                f"Phone : {contact['phone']}",
                styles["BodyText"]
            )

        )

        story.append(

            Paragraph(
                f"Email : {contact['email']}",
                styles["BodyText"]
            )

        )

        story.append(

            Paragraph(
                f"Category : {contact['category']}",
                styles["BodyText"]
            )

        )

        story.append(

            Paragraph(
                f"Favorite : {contact['favorite']}",
                styles["BodyText"]
            )

        )

        story.append(Spacer(1, 12))

    pdf = SimpleDocTemplate(filename)

    pdf.build(story)

    print("\nPDF Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Generate Category Report
# ==========================================

def generate_category_report():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Category_Report.csv"
    )

    with open(

        filename,
        "w",
        newline="",
        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Category",
            "Total Contacts"

        ])

        category_count = {}

        for contact in contacts:

            category = contact["category"]

            category_count[category] = category_count.get(
                category,
                0
            ) + 1

        for category, count in category_count.items():

            writer.writerow([

                category,
                count

            ])

    print("\nCategory Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Contact Summary
# ==========================================

def contact_summary():

    contacts = get_contacts()

    contact_id = input(
        "\nEnter Contact ID : "
    ).strip()

    for contact in contacts:

        if contact["contact_id"] == contact_id:

            print("\n")
            print("=" * 50)
            print("         CONTACT SUMMARY")
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
# Recent Contacts Report
# ==========================================

def recent_contacts_report():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    print("\n========== RECENT CONTACTS ==========\n")

    recent = contacts[-5:]

    for contact in recent:

        print("-" * 50)

        print("Contact ID :", contact["contact_id"])
        print("Name       :", contact["name"])
        print("Phone      :", contact["phone"])
        print("Email      :", contact["email"])
        print("Category   :", contact["category"])
        print("Favorite   :", contact["favorite"])
# ==========================================
# Contact Statistics Report
# ==========================================

def contact_statistics_report():

    contacts = get_contacts()

    if len(contacts) == 0:

        print("\nNo Contacts Available.")

        return

    total_contacts = len(contacts)

    favorite_contacts = 0

    category_count = {}

    for contact in contacts:

        if contact["favorite"] == "Yes":

            favorite_contacts += 1

        category = contact["category"]

        category_count[category] = category_count.get(
            category,
            0
        ) + 1

    print("\n")
    print("=" * 50)
    print("      CONTACT STATISTICS REPORT")
    print("=" * 50)

    print("Total Contacts      :", total_contacts)
    print("Favorite Contacts   :", favorite_contacts)
    print("Normal Contacts     :", total_contacts - favorite_contacts)

    print("\nCategory Statistics")

    print("-" * 30)

    for category, count in category_count.items():

        print(f"{category:<15} : {count}")


# ==========================================
# Favorite Contacts Summary
# ==========================================

def favorite_summary():

    contacts = get_contacts()

    favorites = [

        contact

        for contact in contacts

        if contact["favorite"] == "Yes"

    ]

    print("\n")
    print("=" * 50)
    print("      FAVORITE CONTACT SUMMARY")
    print("=" * 50)

    if len(favorites) == 0:

        print("No Favorite Contacts Found.")

        return

    for contact in favorites:

        print("-" * 40)

        print("Name     :", contact["name"])
        print("Phone    :", contact["phone"])
        print("Category :", contact["category"])


# ==========================================
# Export All Reports
# ==========================================

def export_all_reports():

    generate_contact_report()

    generate_favorite_report()

    generate_category_report()

    generate_contact_pdf()

    print("\n")
    print("=" * 50)
    print("ALL REPORTS GENERATED SUCCESSFULLY")
    print("=" * 50)

    print("Location :", REPORT_FOLDER)


# ==========================================
# Report Dashboard
# ==========================================

def report_dashboard():

    print("\n")
    print("=" * 50)
    print("       REPORT DASHBOARD")
    print("=" * 50)

    files = os.listdir(REPORT_FOLDER)

    print("Total Reports :", len(files))

    if len(files):

        print("\nAvailable Reports")

        print("-" * 25)

        for file in files:

            print(file)


# ==========================================
# Report Menu
# ==========================================

def report_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("          REPORT MANAGEMENT")
        print("=" * 60)

        print("1. Contact Report (CSV)")
        print("2. Favorite Contacts Report")
        print("3. Category Report")
        print("4. Contact Report (PDF)")
        print("5. Contact Summary")
        print("6. Recent Contacts")
        print("7. Contact Statistics")
        print("8. Favorite Summary")
        print("9. View Reports")
        print("10. Report Dashboard")
        print("11. Export All Reports")
        print("12. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            generate_contact_report()

        elif choice == "2":

            generate_favorite_report()

        elif choice == "3":

            generate_category_report()

        elif choice == "4":

            generate_contact_pdf()

        elif choice == "5":

            contact_summary()

        elif choice == "6":

            recent_contacts_report()

        elif choice == "7":

            contact_statistics_report()

        elif choice == "8":

            favorite_summary()

        elif choice == "9":

            view_reports()

        elif choice == "10":

            report_dashboard()

        elif choice == "11":

            export_all_reports()

        elif choice == "12":

            print("\nReturning to Previous Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    report_menu()