# Expense management
# expense.py

from database import (
    get_expenses,
    save_expenses
)

from datetime import datetime


# ==========================================
# Generate Expense ID
# ==========================================

def generate_expense_id():

    expenses = get_expenses()

    if not expenses:
        return "EXP1001"

    last_id = int(expenses[-1]["expense_id"][3:])

    return f"EXP{last_id+1}"


# ==========================================
# Add Expense
# ==========================================

def add_expense():

    expenses = get_expenses()

    print("\n========== ADD EXPENSE ==========")

    category = input("Category : ")

    try:
        amount = float(input("Amount : ₹"))
    except ValueError:
        print("Invalid Amount.")
        return

    description = input("Description : ")

    expense = {

        "expense_id": generate_expense_id(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "category": category,
        "amount": amount,
        "description": description

    }

    expenses.append(expense)

    save_expenses(expenses)

    print("\nExpense Added Successfully.")


# ==========================================
# View Expenses
# ==========================================

def view_expenses():

    expenses = get_expenses()

    if not expenses:

        print("\nNo Expenses Found.")

        return

    print("\n========== EXPENSE LIST ==========")

    for expense in expenses:

        print("-" * 45)

        print("Expense ID :", expense["expense_id"])
        print("Date       :", expense["date"])
        print("Category   :", expense["category"])
        print("Amount     : ₹", expense["amount"])
        print("Description:", expense["description"])


# ==========================================
# Search Expense
# ==========================================

def search_expense():

    expense_id = input("\nEnter Expense ID : ")

    expenses = get_expenses()

    for expense in expenses:

        if expense["expense_id"] == expense_id:

            print("\nExpense Found\n")

            print(expense)

            return

    print("Expense Not Found.")


# ==========================================
# Update Expense
# ==========================================

def update_expense():

    expenses = get_expenses()

    expense_id = input("Expense ID : ")

    for expense in expenses:

        if expense["expense_id"] == expense_id:

            expense["category"] = input("New Category : ")

            try:
                expense["amount"] = float(
                    input("New Amount : ₹")
                )

            except:

                print("Invalid Amount.")

                return

            expense["description"] = input(
                "New Description : "
            )

            save_expenses(expenses)

            print("\nExpense Updated Successfully.")

            return

    print("Expense Not Found.")


# ==========================================
# Delete Expense
# ==========================================

def delete_expense():

    expenses = get_expenses()

    expense_id = input("Expense ID : ")

    for expense in expenses:

        if expense["expense_id"] == expense_id:

            expenses.remove(expense)

            save_expenses(expenses)

            print("\nExpense Deleted Successfully.")

            return

    print("Expense Not Found.")


# ==========================================
# Total Expense
# ==========================================

def total_expense():

    expenses = get_expenses()

    total = sum(
        expense["amount"]
        for expense in expenses
    )

    print("\nTotal Expense : ₹", total)


# ==========================================
# Category Wise Expense
# ==========================================

def category_report():

    expenses = get_expenses()

    report = {}

    for expense in expenses:

        category = expense["category"]

        report[category] = report.get(category, 0)

        report[category] += expense["amount"]

    print("\n====== CATEGORY REPORT ======")

    for category, amount in report.items():

        print(f"{category:<20} ₹{amount}")


# ==========================================
# Monthly Expense
# ==========================================

def monthly_summary():

    expenses = get_expenses()

    report = {}

    for expense in expenses:

        month = expense["date"][:7]

        report[month] = report.get(month, 0)

        report[month] += expense["amount"]

    print("\n====== MONTHLY SUMMARY ======")

    for month, amount in report.items():

        print(f"{month} : ₹{amount}")


# ==========================================
# Highest Expense
# ==========================================

def highest_expense():

    expenses = get_expenses()

    if not expenses:

        print("No Expense Found.")

        return

    highest = max(
        expenses,
        key=lambda x: x["amount"]
    )

    print("\nHighest Expense")

    print(highest)


# ==========================================
# Lowest Expense
# ==========================================

def lowest_expense():

    expenses = get_expenses()

    if not expenses:

        print("No Expense Found.")

        return

    lowest = min(
        expenses,
        key=lambda x: x["amount"]
    )

    print("\nLowest Expense")

    print(lowest)


# ==========================================
# Expense Menu
# ==========================================

def expense_menu():

    while True:

        print("\n==============================")
        print("      EXPENSE MANAGEMENT")
        print("==============================")

        print("1. Add Expense")
        print("2. View Expenses")
        print("3. Search Expense")
        print("4. Update Expense")
        print("5. Delete Expense")
        print("6. Total Expense")
        print("7. Category Report")
        print("8. Monthly Summary")
        print("9. Highest Expense")
        print("10. Lowest Expense")
        print("11. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            add_expense()

        elif choice == "2":
            view_expenses()

        elif choice == "3":
            search_expense()

        elif choice == "4":
            update_expense()

        elif choice == "5":
            delete_expense()

        elif choice == "6":
            total_expense()

        elif choice == "7":
            category_report()

        elif choice == "8":
            monthly_summary()

        elif choice == "9":
            highest_expense()

        elif choice == "10":
            lowest_expense()

        elif choice == "11":
            break

        else:
            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    expense_menu()