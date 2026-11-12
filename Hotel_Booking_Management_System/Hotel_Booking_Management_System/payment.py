# Payment module
# payment.py (Part 1)

from datetime import datetime

from database import (
    get_payments,
    save_payments,
    get_invoices,
    save_invoices
)

from utils import (
    generate_payment_id
)


# ==========================================
# Make Payment
# ==========================================

def make_payment():

    invoices = get_invoices()

    payments = get_payments()

    invoice_id = input("\nEnter Invoice ID : ").strip()

    invoice = None

    for inv in invoices:

        if inv["invoice_id"] == invoice_id:

            invoice = inv

            break

    if invoice is None:

        print("Invoice Not Found.")

        return

    if invoice["payment_status"] == "Paid":

        print("Payment Already Completed.")

        return

    print("\nPayment Methods")
    print("1. Cash")
    print("2. Card")
    print("3. UPI")

    choice = input("Choose Method : ")

    methods = {

        "1": "Cash",

        "2": "Card",

        "3": "UPI"

    }

    if choice not in methods:

        print("Invalid Payment Method.")

        return

    payment = {

        "payment_id": generate_payment_id(),

        "invoice_id": invoice["invoice_id"],

        "customer_id": invoice["customer_id"],

        "customer_name": invoice["customer_name"],

        "amount": invoice["amount"],

        "payment_method": methods[choice],

        "payment_date": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "status": "Success"

    }

    payments.append(payment)

    invoice["payment_status"] = "Paid"

    save_payments(payments)

    save_invoices(invoices)

    print("\nPayment Successful.")

    print("Payment ID :", payment["payment_id"])


# ==========================================
# View Payments
# ==========================================

def view_payments():

    payments = get_payments()

    print("\n")
    print("=" * 70)
    print("          PAYMENT LIST")
    print("=" * 70)

    if len(payments) == 0:

        print("No Payment Records Found.")

        return

    for payment in payments:

        print("-" * 60)

        print("Payment ID :", payment["payment_id"])

        print("Invoice ID :", payment["invoice_id"])

        print("Customer   :", payment["customer_name"])

        print("Amount     : ₹", payment["amount"])

        print("Method     :", payment["payment_method"])

        print("Status     :", payment["status"])


# ==========================================
# Search Payment
# ==========================================

def search_payment():

    payments = get_payments()

    payment_id = input(
        "\nEnter Payment ID : "
    ).strip()

    for payment in payments:

        if payment["payment_id"] == payment_id:

            print("\n")
            print("=" * 60)
            print("        PAYMENT DETAILS")
            print("=" * 60)

            print("Payment ID     :", payment["payment_id"])

            print("Invoice ID     :", payment["invoice_id"])

            print("Customer       :", payment["customer_name"])

            print("Amount         : ₹", payment["amount"])

            print("Method         :", payment["payment_method"])

            print("Payment Date   :", payment["payment_date"])

            print("Status         :", payment["status"])

            return

    print("Payment Not Found.")


# ==========================================
# Payment Receipt
# ==========================================

def payment_receipt():

    payments = get_payments()

    payment_id = input(
        "\nEnter Payment ID : "
    ).strip()

    for payment in payments:

        if payment["payment_id"] == payment_id:

            print("\n")
            print("=" * 60)
            print("         PAYMENT RECEIPT")
            print("=" * 60)

            print("Receipt No   :", payment["payment_id"])

            print("Invoice ID   :", payment["invoice_id"])

            print("Customer     :", payment["customer_name"])

            print("Amount Paid  : ₹", payment["amount"])

            print("Method       :", payment["payment_method"])

            print("Date         :", payment["payment_date"])

            print("Status       :", payment["status"])

            print("=" * 60)

            print("Thank You For Your Payment!")

            return

    print("Payment Record Not Found.")
# ==========================================
# Update Payment
# ==========================================

def update_payment():

    payments = get_payments()

    payment_id = input(
        "\nEnter Payment ID : "
    ).strip()

    for payment in payments:

        if payment["payment_id"] == payment_id:

            print("\nCurrent Payment Method :", payment["payment_method"])

            print("\n1. Cash")
            print("2. Card")
            print("3. UPI")

            choice = input("\nSelect New Method : ")

            methods = {

                "1": "Cash",

                "2": "Card",

                "3": "UPI"

            }

            if choice not in methods:

                print("Invalid Choice.")

                return

            payment["payment_method"] = methods[choice]

            save_payments(payments)

            print("\nPayment Updated Successfully.")

            return

    print("Payment Not Found.")


# ==========================================
# Cancel Payment
# ==========================================

def cancel_payment():

    payments = get_payments()

    invoices = get_invoices()

    payment_id = input(
        "\nEnter Payment ID : "
    ).strip()

    for payment in payments:

        if payment["payment_id"] == payment_id:

            if payment["status"] == "Cancelled":

                print("Payment Already Cancelled.")

                return

            payment["status"] = "Cancelled"

            for invoice in invoices:

                if invoice["invoice_id"] == payment["invoice_id"]:

                    invoice["payment_status"] = "Pending"

                    break

            save_payments(payments)

            save_invoices(invoices)

            print("\nPayment Cancelled Successfully.")

            return

    print("Payment Not Found.")


# ==========================================
# Refund Payment
# ==========================================

def refund_payment():

    payments = get_payments()

    invoices = get_invoices()

    payment_id = input(
        "\nEnter Payment ID : "
    ).strip()

    for payment in payments:

        if payment["payment_id"] == payment_id:

            if payment["status"] != "Success":

                print("Only Successful Payments Can Be Refunded.")

                return

            payment["status"] = "Refunded"

            payment["refund_date"] = datetime.now().strftime(

                "%Y-%m-%d %H:%M:%S"

            )

            for invoice in invoices:

                if invoice["invoice_id"] == payment["invoice_id"]:

                    invoice["payment_status"] = "Pending"

                    break

            save_payments(payments)

            save_invoices(invoices)

            print("\nPayment Refunded Successfully.")

            return

    print("Payment Not Found.")


# ==========================================
# Payment History
# ==========================================

def payment_history():

    payments = get_payments()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    found = False

    print("\n")
    print("=" * 70)
    print("         PAYMENT HISTORY")
    print("=" * 70)

    for payment in payments:

        if payment["customer_id"] == customer_id:

            found = True

            print("-" * 60)

            print("Payment ID :", payment["payment_id"])

            print("Invoice ID :", payment["invoice_id"])

            print("Amount     : ₹", payment["amount"])

            print("Method     :", payment["payment_method"])

            print("Status     :", payment["status"])

            print("Date       :", payment["payment_date"])

    if not found:

        print("No Payment History Found.")


# ==========================================
# Pending Payments
# ==========================================

def pending_payments():

    invoices = get_invoices()

    print("\n")
    print("=" * 70)
    print("        PENDING PAYMENTS")
    print("=" * 70)

    found = False

    for invoice in invoices:

        if invoice["payment_status"] == "Pending":

            found = True

            print("-" * 60)

            print("Invoice ID :", invoice["invoice_id"])

            print("Customer   :", invoice["customer_name"])

            print("Amount     : ₹", invoice["amount"])

            print("Generated  :", invoice["generated_on"])

    if not found:

        print("No Pending Payments.")
import csv
import os
from datetime import datetime

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Daily Payment Report
# ==========================================

def daily_payment_report():

    payments = get_payments()

    today = datetime.now().strftime("%Y-%m-%d")

    total = 0

    print("\n")
    print("=" * 70)
    print("        DAILY PAYMENT REPORT")
    print("=" * 70)

    for payment in payments:

        if payment["payment_date"].startswith(today):

            total += payment["amount"]

            print("-" * 60)

            print("Payment ID :", payment["payment_id"])

            print("Customer   :", payment["customer_name"])

            print("Amount     : ₹", payment["amount"])

            print("Method     :", payment["payment_method"])

            print("Status     :", payment["status"])

    print("-" * 60)

    print("Today's Revenue : ₹", round(total, 2))


# ==========================================
# Monthly Payment Report
# ==========================================

def monthly_payment_report():

    payments = get_payments()

    month = datetime.now().strftime("%Y-%m")

    total = 0

    count = 0

    print("\n")
    print("=" * 70)
    print("       MONTHLY PAYMENT REPORT")
    print("=" * 70)

    for payment in payments:

        if payment["payment_date"].startswith(month):

            total += payment["amount"]

            count += 1

    print("Month          :", month)

    print("Transactions   :", count)

    print("Revenue        : ₹", round(total, 2))


# ==========================================
# Payment Statistics
# ==========================================

def payment_statistics():

    payments = get_payments()

    success = len([

        payment

        for payment in payments

        if payment["status"] == "Success"

    ])

    refunded = len([

        payment

        for payment in payments

        if payment["status"] == "Refunded"

    ])

    cancelled = len([

        payment

        for payment in payments

        if payment["status"] == "Cancelled"

    ])

    revenue = sum(

        payment["amount"]

        for payment in payments

        if payment["status"] == "Success"

    )

    print("\n")
    print("=" * 70)
    print("        PAYMENT STATISTICS")
    print("=" * 70)

    print("Total Payments :", len(payments))

    print("Successful     :", success)

    print("Refunded       :", refunded)

    print("Cancelled      :", cancelled)

    print("Revenue        : ₹", round(revenue, 2))


# ==========================================
# Payment Dashboard
# ==========================================

def payment_dashboard():

    payments = get_payments()

    print("\n")
    print("=" * 70)
    print("        PAYMENT DASHBOARD")
    print("=" * 70)

    print("Total Payments :", len(payments))

    print("Successful :", len([

        payment

        for payment in payments

        if payment["status"] == "Success"

    ]))

    print("Refunded :", len([

        payment

        for payment in payments

        if payment["status"] == "Refunded"

    ]))

    print("Cancelled :", len([

        payment

        for payment in payments

        if payment["status"] == "Cancelled"

    ]))

    print("Revenue : ₹", sum(

        payment["amount"]

        for payment in payments

        if payment["status"] == "Success"

    ))


# ==========================================
# Export Payment Report
# ==========================================

def export_payment_report():

    payments = get_payments()

    filename = os.path.join(

        REPORT_FOLDER,

        "Payment_Report.csv"

    )

    with open(

        filename,

        "w",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Payment ID",

            "Invoice ID",

            "Customer",

            "Amount",

            "Method",

            "Status",

            "Payment Date"

        ])

        for payment in payments:

            writer.writerow([

                payment["payment_id"],

                payment["invoice_id"],

                payment["customer_name"],

                payment["amount"],

                payment["payment_method"],

                payment["status"],

                payment["payment_date"]

            ])

    print("\nPayment Report Exported Successfully.")

    print("Saved To :", filename)
# ==========================================
# Payment Summary
# ==========================================

def payment_summary():

    payments = get_payments()

    print("\n")
    print("=" * 80)
    print("           PAYMENT SUMMARY")
    print("=" * 80)

    if len(payments) == 0:

        print("No Payment Records Found.")

        return

    print(

        "{:<15}{:<20}{:<12}{:<12}{:<15}".format(

            "Payment ID",

            "Customer",

            "Amount",

            "Method",

            "Status"

        )

    )

    print("=" * 80)

    for payment in payments:

        print(

            "{:<15}{:<20}{:<12}{:<12}{:<15}".format(

                payment["payment_id"],

                payment["customer_name"],

                payment["amount"],

                payment["payment_method"],

                payment["status"]

            )

        )

    print("=" * 80)


# ==========================================
# Payment Analytics
# ==========================================

def payment_analytics():

    payments = get_payments()

    total_amount = sum(

        payment["amount"]

        for payment in payments

        if payment["status"] == "Success"

    )

    successful = len([

        payment

        for payment in payments

        if payment["status"] == "Success"

    ])

    average = 0

    if successful > 0:

        average = total_amount / successful

    print("\n")
    print("=" * 60)
    print("         PAYMENT ANALYTICS")
    print("=" * 60)

    print("Total Successful Payments :", successful)

    print("Revenue Generated         : ₹", round(total_amount, 2))

    print("Average Payment           : ₹", round(average, 2))


# ==========================================
# Revenue by Payment Method
# ==========================================

def revenue_by_method():

    payments = get_payments()

    methods = {

        "Cash": 0,

        "Card": 0,

        "UPI": 0

    }

    for payment in payments:

        if payment["status"] == "Success":

            method = payment["payment_method"]

            if method in methods:

                methods[method] += payment["amount"]

    print("\n")
    print("=" * 60)
    print("      REVENUE BY PAYMENT METHOD")
    print("=" * 60)

    for method, amount in methods.items():

        print(f"{method:<10}: ₹ {round(amount, 2)}")


# ==========================================
# Payment Management Menu
# ==========================================

def payment_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("        PAYMENT MANAGEMENT")
        print("=" * 60)

        print("1. Make Payment")
        print("2. View Payments")
        print("3. Search Payment")
        print("4. Payment Receipt")
        print("5. Update Payment")
        print("6. Cancel Payment")
        print("7. Refund Payment")
        print("8. Payment History")
        print("9. Pending Payments")
        print("10. Daily Payment Report")
        print("11. Monthly Payment Report")
        print("12. Payment Statistics")
        print("13. Payment Dashboard")
        print("14. Export Payment Report")
        print("15. Payment Summary")
        print("16. Payment Analytics")
        print("17. Revenue by Payment Method")
        print("18. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            make_payment()

        elif choice == "2":

            view_payments()

        elif choice == "3":

            search_payment()

        elif choice == "4":

            payment_receipt()

        elif choice == "5":

            update_payment()

        elif choice == "6":

            cancel_payment()

        elif choice == "7":

            refund_payment()

        elif choice == "8":

            payment_history()

        elif choice == "9":

            pending_payments()

        elif choice == "10":

            daily_payment_report()

        elif choice == "11":

            monthly_payment_report()

        elif choice == "12":

            payment_statistics()

        elif choice == "13":

            payment_dashboard()

        elif choice == "14":

            export_payment_report()

        elif choice == "15":

            payment_summary()

        elif choice == "16":

            payment_analytics()

        elif choice == "17":

            revenue_by_method()

        elif choice == "18":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    payment_menu()