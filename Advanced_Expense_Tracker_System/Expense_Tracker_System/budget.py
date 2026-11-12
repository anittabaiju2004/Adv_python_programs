# Budget management
# budget.py

from database import (
    get_budget,
    save_budget,
    get_expenses,
    get_income
)

from datetime import datetime


# ==========================================
# Set Monthly Budget
# ==========================================

def set_budget():

    budget_data = get_budget()

    print("\n========== SET MONTHLY BUDGET ==========")

    month = input("Enter Month (YYYY-MM): ").strip()

    try:
        amount = float(input("Enter Budget Amount : ₹"))
    except ValueError:
        print("Invalid Amount.")
        return

    for budget in budget_data:

        if budget["month"] == month:

            budget["budget"] = amount

            save_budget(budget_data)

            print("\nBudget Updated Successfully.")

            return

    budget_data.append({
        "month": month,
        "budget": amount
    })

    save_budget(budget_data)

    print("\nBudget Added Successfully.")


# ==========================================
# View Budget
# ==========================================

def view_budget():

    budget_data = get_budget()

    if not budget_data:
        print("\nNo Budget Found.")
        return

    print("\n========== MONTHLY BUDGET ==========")

    for budget in budget_data:

        print("-" * 40)
        print("Month  :", budget["month"])
        print("Budget : ₹", budget["budget"])


# ==========================================
# Budget Remaining
# ==========================================

def budget_remaining():

    budget_data = get_budget()

    month = input("\nEnter Month (YYYY-MM): ").strip()

    budget = None

    for item in budget_data:

        if item["month"] == month:
            budget = item
            break

    if budget is None:
        print("Budget Not Found.")
        return

    expenses = get_expenses()

    total = 0

    for expense in expenses:

        if expense["date"].startswith(month):

            total += float(expense["amount"])

    remaining = budget["budget"] - total

    print("\n========== BUDGET STATUS ==========")

    print("Budget        : ₹", budget["budget"])
    print("Expense       : ₹", total)
    print("Remaining     : ₹", remaining)


# ==========================================
# Budget Exceeded Alert
# ==========================================

def budget_alert():

    budget_data = get_budget()

    month = datetime.now().strftime("%Y-%m")

    budget = None

    for item in budget_data:

        if item["month"] == month:
            budget = item
            break

    if budget is None:
        print("\nNo Budget Set For Current Month.")
        return

    expenses = get_expenses()

    total = 0

    for expense in expenses:

        if expense["date"].startswith(month):

            total += float(expense["amount"])

    print("\n========== BUDGET ALERT ==========")

    print("Monthly Budget : ₹", budget["budget"])
    print("Current Expense: ₹", total)

    if total > budget["budget"]:

        print("\n⚠ Budget Exceeded!")

    elif total >= (budget["budget"] * 0.80):

        print("\n⚠ Warning : You have used 80% of your budget.")

    else:

        print("\nBudget is Under Control.")


# ==========================================
# Budget Summary
# ==========================================

def budget_summary():

    income = get_income()
    expenses = get_expenses()

    total_income = sum(float(i["amount"]) for i in income)
    total_expense = sum(float(e["amount"]) for e in expenses)

    balance = total_income - total_expense

    print("\n========== FINANCIAL SUMMARY ==========")

    print("Total Income  : ₹", total_income)
    print("Total Expense : ₹", total_expense)
    print("Balance       : ₹", balance)


# ==========================================
# Delete Budget
# ==========================================

def delete_budget():

    budget_data = get_budget()

    month = input("Enter Month (YYYY-MM): ")

    for budget in budget_data:

        if budget["month"] == month:

            budget_data.remove(budget)

            save_budget(budget_data)

            print("\nBudget Deleted Successfully.")

            return

    print("Budget Not Found.")


# ==========================================
# Budget Menu
# ==========================================

def budget_menu():

    while True:

        print("\n================================")
        print("       BUDGET MANAGEMENT")
        print("================================")

        print("1. Set Monthly Budget")
        print("2. View Budget")
        print("3. Budget Remaining")
        print("4. Budget Alert")
        print("5. Financial Summary")
        print("6. Delete Budget")
        print("7. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            set_budget()

        elif choice == "2":
            view_budget()

        elif choice == "3":
            budget_remaining()

        elif choice == "4":
            budget_alert()

        elif choice == "5":
            budget_summary()

        elif choice == "6":
            delete_budget()

        elif choice == "7":
            break

        else:
            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    budget_menu()