# Reports and charts
# report.py

import csv
import os

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph

from database import (
    get_expenses,
    get_income
)

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Expense Report
# ==========================================

def expense_report():

    expenses = get_expenses()

    if not expenses:
        print("\nNo Expense Records.")
        return

    total = 0

    print("\n========== EXPENSE REPORT ==========")

    for expense in expenses:

        print("-" * 50)
        print("Date       :", expense["date"])
        print("Category   :", expense["category"])
        print("Amount     : ₹", expense["amount"])
        print("Description:", expense["description"])

        total += expense["amount"]

    print("\nTotal Expense : ₹", total)


# ==========================================
# Income Report
# ==========================================

def income_report():

    income = get_income()

    if not income:
        print("\nNo Income Records.")
        return

    total = 0

    print("\n========== INCOME REPORT ==========")

    for item in income:

        print("-" * 50)
        print("Date       :", item["date"])
        print("Source     :", item["source"])
        print("Amount     : ₹", item["amount"])
        print("Description:", item["description"])

        total += item["amount"]

    print("\nTotal Income : ₹", total)


# ==========================================
# Financial Summary
# ==========================================

def financial_summary():

    expenses = get_expenses()
    income = get_income()

    total_income = sum(i["amount"] for i in income)
    total_expense = sum(e["amount"] for e in expenses)

    balance = total_income - total_expense

    print("\n========== FINANCIAL SUMMARY ==========")

    print("Total Income  : ₹", total_income)
    print("Total Expense : ₹", total_expense)
    print("Balance       : ₹", balance)


# ==========================================
# Monthly Report
# ==========================================

def monthly_report():

    expenses = get_expenses()

    report = {}

    for expense in expenses:

        month = expense["date"][:7]

        report[month] = report.get(month, 0)

        report[month] += expense["amount"]

    print("\n========== MONTHLY REPORT ==========")

    for month, amount in report.items():

        print(f"{month} : ₹{amount}")


# ==========================================
# Category Report
# ==========================================

def category_report():

    expenses = get_expenses()

    report = {}

    for expense in expenses:

        category = expense["category"]

        report[category] = report.get(category, 0)

        report[category] += expense["amount"]

    print("\n========== CATEGORY REPORT ==========")

    for category, amount in report.items():

        print(f"{category:<20} ₹{amount}")


# ==========================================
# Export Expense CSV
# ==========================================

def export_expense_csv():

    expenses = get_expenses()

    filename = os.path.join(
        REPORT_FOLDER,
        "expenses.csv"
    )

    with open(filename, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Expense ID",
            "Date",
            "Category",
            "Amount",
            "Description"
        ])

        for expense in expenses:

            writer.writerow([
                expense["expense_id"],
                expense["date"],
                expense["category"],
                expense["amount"],
                expense["description"]
            ])

    print("\nExpense CSV Generated Successfully.")
    print(filename)


# ==========================================
# Export Income CSV
# ==========================================

def export_income_csv():

    income = get_income()

    filename = os.path.join(
        REPORT_FOLDER,
        "income.csv"
    )

    with open(filename, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Income ID",
            "Date",
            "Source",
            "Amount",
            "Description"
        ])

        for item in income:

            writer.writerow([
                item["income_id"],
                item["date"],
                item["source"],
                item["amount"],
                item["description"]
            ])

    print("\nIncome CSV Generated Successfully.")
    print(filename)


# ==========================================
# PDF Expense Report
# ==========================================

def generate_pdf_report():

    expenses = get_expenses()

    filename = os.path.join(
        REPORT_FOLDER,
        "Expense_Report.pdf"
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b>Expense Report</b>",
            styles["Title"]
        )
    )

    total = 0

    for expense in expenses:

        line = (
            f"{expense['date']} | "
            f"{expense['category']} | "
            f"₹{expense['amount']} | "
            f"{expense['description']}"
        )

        story.append(
            Paragraph(
                line,
                styles["BodyText"]
            )
        )

        total += expense["amount"]

    story.append(
        Paragraph(
            f"<br/><b>Total Expense : ₹{total}</b>",
            styles["Heading2"]
        )
    )

    doc = SimpleDocTemplate(filename)

    doc.build(story)

    print("\nPDF Report Generated Successfully.")
    print(filename)


# ==========================================
# Report Menu
# ==========================================

def report_menu():

    while True:

        print("\n==============================")
        print("       REPORTS")
        print("==============================")

        print("1. Expense Report")
        print("2. Income Report")
        print("3. Financial Summary")
        print("4. Monthly Report")
        print("5. Category Report")
        print("6. Export Expense CSV")
        print("7. Export Income CSV")
        print("8. Generate PDF Report")
        print("9. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            expense_report()

        elif choice == "2":
            income_report()

        elif choice == "3":
            financial_summary()

        elif choice == "4":
            monthly_report()

        elif choice == "5":
            category_report()

        elif choice == "6":
            export_expense_csv()

        elif choice == "7":
            export_income_csv()

        elif choice == "8":
            generate_pdf_report()

        elif choice == "9":
            break

        else:
            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    report_menu()