# Bill reminders
# reminder.py

from database import (
    get_reminders,
    save_reminders
)

from datetime import datetime


# ==========================================
# Generate Reminder ID
# ==========================================

def generate_reminder_id():

    reminders = get_reminders()

    if not reminders:
        return "REM1001"

    last_id = int(reminders[-1]["reminder_id"][3:])

    return f"REM{last_id + 1}"


# ==========================================
# Add Reminder
# ==========================================

def add_reminder():

    reminders = get_reminders()

    print("\n========== ADD BILL REMINDER ==========")

    title = input("Reminder Title : ")
    due_date = input("Due Date (YYYY-MM-DD) : ")

    try:
        amount = float(input("Amount : ₹"))
    except ValueError:
        print("Invalid Amount.")
        return

    status = "Pending"

    reminder = {

        "reminder_id": generate_reminder_id(),
        "title": title,
        "due_date": due_date,
        "amount": amount,
        "status": status,
        "created_date": datetime.now().strftime("%Y-%m-%d")

    }

    reminders.append(reminder)

    save_reminders(reminders)

    print("\nReminder Added Successfully.")


# ==========================================
# View All Reminders
# ==========================================

def view_reminders():

    reminders = get_reminders()

    if not reminders:

        print("\nNo Reminders Found.")

        return

    print("\n========== REMINDER LIST ==========")

    for reminder in reminders:

        print("-" * 50)

        print("Reminder ID :", reminder["reminder_id"])
        print("Title       :", reminder["title"])
        print("Due Date    :", reminder["due_date"])
        print("Amount      : ₹", reminder["amount"])
        print("Status      :", reminder["status"])


# ==========================================
# Upcoming Bills
# ==========================================

def upcoming_bills():

    reminders = get_reminders()

    today = datetime.now().strftime("%Y-%m-%d")

    print("\n========== UPCOMING BILLS ==========")

    found = False

    for reminder in reminders:

        if reminder["status"] == "Pending" and reminder["due_date"] >= today:

            found = True

            print("-" * 40)
            print("Reminder :", reminder["title"])
            print("Due Date :", reminder["due_date"])
            print("Amount   : ₹", reminder["amount"])

    if not found:
        print("No Upcoming Bills.")


# ==========================================
# Mark as Paid
# ==========================================

def mark_paid():

    reminders = get_reminders()

    reminder_id = input("Enter Reminder ID : ")

    for reminder in reminders:

        if reminder["reminder_id"] == reminder_id:

            reminder["status"] = "Paid"

            save_reminders(reminders)

            print("\nBill Marked as Paid.")

            return

    print("Reminder Not Found.")


# ==========================================
# Overdue Bills
# ==========================================

def overdue_bills():

    reminders = get_reminders()

    today = datetime.now().strftime("%Y-%m-%d")

    print("\n========== OVERDUE BILLS ==========")

    found = False

    for reminder in reminders:

        if reminder["status"] == "Pending" and reminder["due_date"] < today:

            found = True

            print("-" * 40)
            print("Reminder :", reminder["title"])
            print("Due Date :", reminder["due_date"])
            print("Amount   : ₹", reminder["amount"])

    if not found:
        print("No Overdue Bills.")


# ==========================================
# Delete Reminder
# ==========================================

def delete_reminder():

    reminders = get_reminders()

    reminder_id = input("Enter Reminder ID : ")

    for reminder in reminders:

        if reminder["reminder_id"] == reminder_id:

            reminders.remove(reminder)

            save_reminders(reminders)

            print("\nReminder Deleted Successfully.")

            return

    print("Reminder Not Found.")


# ==========================================
# Reminder Summary
# ==========================================

def reminder_summary():

    reminders = get_reminders()

    total = len(reminders)

    paid = sum(1 for r in reminders if r["status"] == "Paid")

    pending = sum(1 for r in reminders if r["status"] == "Pending")

    print("\n========== REMINDER SUMMARY ==========")

    print("Total Bills   :", total)
    print("Paid Bills    :", paid)
    print("Pending Bills :", pending)


# ==========================================
# Reminder Menu
# ==========================================

def reminder_menu():

    while True:

        print("\n================================")
        print("      BILL REMINDER SYSTEM")
        print("================================")

        print("1. Add Reminder")
        print("2. View Reminders")
        print("3. Upcoming Bills")
        print("4. Mark Bill as Paid")
        print("5. Overdue Bills")
        print("6. Delete Reminder")
        print("7. Reminder Summary")
        print("8. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            add_reminder()

        elif choice == "2":
            view_reminders()

        elif choice == "3":
            upcoming_bills()

        elif choice == "4":
            mark_paid()

        elif choice == "5":
            overdue_bills()

        elif choice == "6":
            delete_reminder()

        elif choice == "7":
            reminder_summary()

        elif choice == "8":
            break

        else:
            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    reminder_menu()