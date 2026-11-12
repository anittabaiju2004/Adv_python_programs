# report.py (Part 1)

import csv
import os

from database import (
    get_customers,
    get_transactions,
    get_loans,
    get_fixed_deposits
)

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Generate Customer Report
# ==========================================

def generate_customer_report():

    customers = get_customers()

    if len(customers) == 0:

        print("\nNo Customer Records Found.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Customer_Report.csv"
    )

    with open(
        filename,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Account Number",
            "Customer Name",
            "Phone",
            "Email",
            "Balance",
            "Status",
            "Created Date"
        ])

        for customer in customers:

            writer.writerow([

                customer["account_number"],
                customer["name"],
                customer["phone"],
                customer["email"],
                customer["balance"],
                customer["status"],
                customer["created_date"]

            ])

    print("\nCustomer Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Generate Transaction Report
# ==========================================

def generate_transaction_report():

    transactions = get_transactions()

    if len(transactions) == 0:

        print("\nNo Transaction Records Found.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Transaction_Report.csv"
    )

    with open(
        filename,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Transaction ID",
            "Account Number",
            "Transaction Type",
            "Amount",
            "Balance",
            "Receiver Account",
            "Date"
        ])

        for transaction in transactions:

            writer.writerow([

                transaction["transaction_id"],
                transaction["account_number"],
                transaction["type"],
                transaction["amount"],
                transaction["balance"],
                transaction.get(
                    "receiver_account",
                    "-"
                ),
                transaction["date"]

            ])

    print("\nTransaction Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Report Summary
# ==========================================

def report_summary():

    customers = get_customers()
    transactions = get_transactions()
    loans = get_loans()
    fixed_deposits = get_fixed_deposits()

    total_balance = 0

    for customer in customers:

        total_balance += customer["balance"]

    print("\n")
    print("=" * 50)
    print("          REPORT SUMMARY")
    print("=" * 50)

    print(f"Total Customers        : {len(customers)}")
    print(f"Total Transactions     : {len(transactions)}")
    print(f"Total Loans            : {len(loans)}")
    print(f"Total Fixed Deposits   : {len(fixed_deposits)}")
    print(f"Total Bank Balance     : ₹{total_balance:.2f}")


# ==========================================
# View Reports Folder
# ==========================================

def view_reports():

    files = os.listdir(REPORT_FOLDER)

    if len(files) == 0:

        print("\nNo Reports Available.")

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
# Generate PDF Account Statement
# ==========================================

def generate_account_statement():

    customers = get_customers()
    transactions = get_transactions()

    account_number = input(
        "\nEnter Account Number : "
    ).strip()

    customer = None

    for c in customers:

        if c["account_number"] == account_number:

            customer = c
            break

    if customer is None:

        print("Customer Not Found.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        f"Statement_{account_number}.pdf"
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b>BANK ACCOUNT STATEMENT</b>",
            styles["Title"]
        )
    )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            f"Account Number : {customer['account_number']}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Customer Name : {customer['name']}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Phone : {customer['phone']}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Email : {customer['email']}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Current Balance : ₹{customer['balance']:.2f}",
            styles["BodyText"]
        )
    )

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "<b>Transaction History</b>",
            styles["Heading2"]
        )
    )

    for transaction in transactions:

        if transaction["account_number"] == account_number:

            line = (
                f"{transaction['date']} | "
                f"{transaction['type']} | "
                f"₹{transaction['amount']:.2f}"
            )

            story.append(
                Paragraph(
                    line,
                    styles["BodyText"]
                )
            )

    pdf = SimpleDocTemplate(filename)

    pdf.build(story)

    print("\nPDF Statement Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Generate Loan Report
# ==========================================

def generate_loan_report():

    loans = get_loans()

    if len(loans) == 0:

        print("\nNo Loan Records Found.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Loan_Report.csv"
    )

    with open(
        filename,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Loan ID",
            "Account Number",
            "Loan Type",
            "Loan Amount",
            "Interest Rate",
            "EMI",
            "Remaining Amount",
            "Status"
        ])

        for loan in loans:

            writer.writerow([

                loan["loan_id"],
                loan["account_number"],
                loan["loan_type"],
                loan["loan_amount"],
                loan["interest_rate"],
                loan["emi"],
                loan["remaining_amount"],
                loan["status"]

            ])

    print("\nLoan Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Generate Fixed Deposit Report
# ==========================================

def generate_fd_report():

    fds = get_fixed_deposits()

    if len(fds) == 0:

        print("\nNo Fixed Deposits Found.")

        return

    filename = os.path.join(
        REPORT_FOLDER,
        "Fixed_Deposit_Report.csv"
    )

    with open(
        filename,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "FD Number",
            "Account Number",
            "Amount",
            "Interest Rate",
            "Interest",
            "Maturity Amount",
            "Status"
        ])

        for fd in fds:

            writer.writerow([

                fd["fd_id"],
                fd["account_number"],
                fd["amount"],
                fd["interest_rate"],
                fd["interest"],
                fd["maturity_amount"],
                fd["status"]

            ])

    print("\nFixed Deposit Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Customer Account Summary
# ==========================================

def customer_account_summary():

    customers = get_customers()

    account_number = input(
        "\nEnter Account Number : "
    ).strip()

    for customer in customers:

        if customer["account_number"] == account_number:

            print("\n========== CUSTOMER SUMMARY ==========\n")

            print("Account Number :", customer["account_number"])
            print("Customer Name  :", customer["name"])
            print("Phone          :", customer["phone"])
            print("Email          :", customer["email"])
            print("Balance        : ₹", customer["balance"])
            print("Status         :", customer["status"])
            print("Created Date   :", customer["created_date"])

            return

    print("Customer Not Found.")
# ==========================================
# Daily Transaction Report
# ==========================================

def daily_transaction_report():

    transactions = get_transactions()

    date = input("\nEnter Date (YYYY-MM-DD): ").strip()

    found = False
    total = 0

    print("\n========== DAILY TRANSACTION REPORT ==========\n")

    for transaction in transactions:

        if transaction["date"].startswith(date):

            found = True

            print("-" * 60)
            print("Transaction ID :", transaction["transaction_id"])
            print("Account Number :", transaction["account_number"])
            print("Type           :", transaction["type"])
            print("Amount         : ₹", transaction["amount"])
            print("Date           :", transaction["date"])

            total += transaction["amount"]

    if not found:

        print("No Transactions Found.")

    else:

        print("\nTotal Transaction Amount : ₹", total)


# ==========================================
# Monthly Transaction Report
# ==========================================

def monthly_transaction_report():

    transactions = get_transactions()

    month = input("\nEnter Month (YYYY-MM): ").strip()

    found = False
    total = 0

    print("\n========== MONTHLY TRANSACTION REPORT ==========\n")

    for transaction in transactions:

        if transaction["date"].startswith(month):

            found = True

            print("-" * 60)
            print("Transaction ID :", transaction["transaction_id"])
            print("Account Number :", transaction["account_number"])
            print("Type           :", transaction["type"])
            print("Amount         : ₹", transaction["amount"])
            print("Date           :", transaction["date"])

            total += transaction["amount"]

    if not found:

        print("No Transactions Found.")

    else:

        print("\nTotal Monthly Transaction : ₹", total)


# ==========================================
# Deposit Report
# ==========================================

def deposit_report():

    transactions = get_transactions()

    total = 0

    print("\n========== DEPOSIT REPORT ==========\n")

    for transaction in transactions:

        if transaction["type"] == "Deposit":

            print("-" * 50)
            print("Transaction :", transaction["transaction_id"])
            print("Account     :", transaction["account_number"])
            print("Amount      : ₹", transaction["amount"])

            total += transaction["amount"]

    print("\nTotal Deposits : ₹", total)


# ==========================================
# Withdrawal Report
# ==========================================

def withdrawal_report():

    transactions = get_transactions()

    total = 0

    print("\n========== WITHDRAWAL REPORT ==========\n")

    for transaction in transactions:

        if transaction["type"] == "Withdraw":

            print("-" * 50)
            print("Transaction :", transaction["transaction_id"])
            print("Account     :", transaction["account_number"])
            print("Amount      : ₹", transaction["amount"])

            total += transaction["amount"]

    print("\nTotal Withdrawals : ₹", total)


# ==========================================
# Export All Reports
# ==========================================

def export_all_reports():

    generate_customer_report()
    generate_transaction_report()
    generate_loan_report()
    generate_fd_report()

    print("\n===================================")
    print("All Reports Generated Successfully")
    print("Reports Folder :", REPORT_FOLDER)
    print("===================================")


# ==========================================
# Report Menu
# ==========================================

def report_menu():

    while True:

        print("\n")
        print("=" * 50)
        print("            REPORT MENU")
        print("=" * 50)

        print("1. Customer Report")
        print("2. Transaction Report")
        print("3. Loan Report")
        print("4. Fixed Deposit Report")
        print("5. PDF Account Statement")
        print("6. Customer Summary")
        print("7. Daily Transaction Report")
        print("8. Monthly Transaction Report")
        print("9. Deposit Report")
        print("10. Withdrawal Report")
        print("11. Report Summary")
        print("12. View Reports Folder")
        print("13. Export All Reports")
        print("14. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            generate_customer_report()

        elif choice == "2":

            generate_transaction_report()

        elif choice == "3":

            generate_loan_report()

        elif choice == "4":

            generate_fd_report()

        elif choice == "5":

            generate_account_statement()

        elif choice == "6":

            customer_account_summary()

        elif choice == "7":

            daily_transaction_report()

        elif choice == "8":

            monthly_transaction_report()

        elif choice == "9":

            deposit_report()

        elif choice == "10":

            withdrawal_report()

        elif choice == "11":

            report_summary()

        elif choice == "12":

            view_reports()

        elif choice == "13":

            export_all_reports()

        elif choice == "14":

            print("\nReturning to Previous Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    report_menu()
