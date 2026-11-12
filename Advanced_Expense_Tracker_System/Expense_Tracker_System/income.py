# Income management
# income.py

from database import (
    get_income,
    save_income
)

from datetime import datetime


# ==========================================
# Generate Income ID
# ==========================================

def generate_income_id():

    income = get_income()

    if not income:
        return "INC1001"

    last_id = int(income[-1]["income_id"][3:])

    return f"INC{last_id + 1}"


# ==========================================
# Add Income
# ==========================================

def add_income():

    income = get_income()

    print("\n========== ADD INCOME ==========")

    source = input("Income Source : ")

    try:
        amount = float(input("Amount : ₹"))
    except ValueError:
        print("Invalid Amount.")
        return

    description = input("Description : ")

    income_data = {

        "income_id": generate_income_id(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": source,
        "amount": amount,
        "description": description

    }

    income.append(income_data)

    save_income(income)

    print("\nIncome Added Successfully.")


# ==========================================
# View Income
# ==========================================

def view_income():

    income = get_income()

    if not income:
        print("\nNo Income Records Found.")
        return

    print("\n========== INCOME LIST ==========")

    for item in income:

        print("-" * 50)

        print("Income ID   :", item["income_id"])
        print("Date        :", item["date"])
        print("Source      :", item["source"])
        print("Amount      : ₹", item["amount"])
        print("Description :", item["description"])


# ==========================================
# Search Income
# ==========================================

def search_income():

    income_id = input("\nEnter Income ID : ")

    income = get_income()

    for item in income:

        if item["income_id"] == income_id:

            print("\nIncome Found\n")

            print(item)

            return

    print("Income Not Found.")


# ==========================================
# Update Income
# ==========================================

def update_income():

    income = get_income()

    income_id = input("Enter Income ID : ")

    for item in income:

        if item["income_id"] == income_id:

            item["source"] = input("New Source : ")

            try:
                item["amount"] = float(
                    input("New Amount : ₹")
                )
            except ValueError:
                print("Invalid Amount.")
                return

            item["description"] = input(
                "New Description : "
            )

            save_income(income)

            print("\nIncome Updated Successfully.")

            return

    print("Income Not Found.")


# ==========================================
# Delete Income
# ==========================================

def delete_income():

    income = get_income()

    income_id = input("Enter Income ID : ")

    for item in income:

        if item["income_id"] == income_id:

            income.remove(item)

            save_income(income)

            print("\nIncome Deleted Successfully.")

            return

    print("Income Not Found.")


# ==========================================
# Total Income
# ==========================================

def total_income():

    income = get_income()

    total = sum(item["amount"] for item in income)

    print("\nTotal Income : ₹", total)


# ==========================================
# Monthly Income Summary
# ==========================================

def monthly_income_summary():

    income = get_income()

    report = {}

    for item in income:

        month = item["date"][:7]

        report[month] = report.get(month, 0)

        report[month] += item["amount"]

    print("\n====== MONTHLY INCOME SUMMARY ======")

    for month, amount in report.items():

        print(f"{month} : ₹{amount}")


# ==========================================
# Highest Income
# ==========================================

def highest_income():

    income = get_income()

    if not income:

        print("No Income Records.")

        return

    highest = max(
        income,
        key=lambda x: x["amount"]
    )

    print("\nHighest Income")

    print(highest)


# ==========================================
# Lowest Income
# ==========================================

def lowest_income():

    income = get_income()

    if not income:

        print("No Income Records.")

        return

    lowest = min(
        income,
        key=lambda x: x["amount"]
    )

    print("\nLowest Income")

    print(lowest)


# ==========================================
# Income by Source
# ==========================================

def source_report():

    income = get_income()

    report = {}

    for item in income:

        source = item["source"]

        report[source] = report.get(source, 0)

        report[source] += item["amount"]

    print("\n====== SOURCE REPORT ======")

    for source, amount in report.items():

        print(f"{source:<20} ₹{amount}")


# ==========================================
# Income Menu
# ==========================================

def income_menu():

    while True:

        print("\n================================")
        print("        INCOME MANAGEMENT")
        print("================================")

        print("1. Add Income")
        print("2. View Income")
        print("3. Search Income")
        print("4. Update Income")
        print("5. Delete Income")
        print("6. Total Income")
        print("7. Monthly Summary")
        print("8. Highest Income")
        print("9. Lowest Income")
        print("10. Source Report")
        print("11. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            add_income()

        elif choice == "2":
            view_income()

        elif choice == "3":
            search_income()

        elif choice == "4":
            update_income()

        elif choice == "5":
            delete_income()

        elif choice == "6":
            total_income()

        elif choice == "7":
            monthly_income_summary()

        elif choice == "8":
            highest_income()

        elif choice == "9":
            lowest_income()

        elif choice == "10":
            source_report()

        elif choice == "11":
            break

        else:
            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    income_menu()