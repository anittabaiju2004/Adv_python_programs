# Invoice generation
# invoice.py (Part 1)

from datetime import datetime

from database import (
    get_bookings,
    get_invoices,
    save_invoices
)
from database import (
    get_payments,
    save_payments
)

from utils import (
    generate_payment_id
)
from utils import generate_invoice_id


# ==========================================
# Generate Invoice
# ==========================================

def generate_invoice():

    bookings = get_bookings()

    invoices = get_invoices()

    print("\n")
    print("=" * 60)
    print("          GENERATE INVOICE")
    print("=" * 60)

    booking_id = input("Booking ID : ").strip()

    for booking in bookings:

        if booking["booking_id"] == booking_id:

            for invoice in invoices:

                if invoice["booking_id"] == booking_id:

                    print("Invoice Already Exists.")

                    return

            invoice = {

                "invoice_id": generate_invoice_id(),

                "booking_id": booking["booking_id"],

                "customer_id": booking["customer_id"],

                "customer_name": booking["customer_name"],

                "room_number": booking["room_number"],

                "check_in": booking["check_in"],

                "check_out": booking["check_out"],

                "days": booking["days"],

                "amount": booking["total_amount"],

                "payment_status": "Pending",

                "generated_on": datetime.now().strftime(
                    "%Y-%m-%d"
                )

            }

            invoices.append(invoice)

            save_invoices(invoices)

            print("\nInvoice Generated Successfully.")

            print("Invoice ID :", invoice["invoice_id"])

            return

    print("Booking Not Found.")


# ==========================================
# View Invoices
# ==========================================

def view_invoices():

    invoices = get_invoices()

    print("\n")
    print("=" * 70)
    print("           INVOICE LIST")
    print("=" * 70)

    if len(invoices) == 0:

        print("No Invoice Records Found.")

        return

    for invoice in invoices:

        print("-" * 60)

        print("Invoice ID :", invoice["invoice_id"])

        print("Customer   :", invoice["customer_name"])

        print("Room No    :", invoice["room_number"])

        print("Amount     : ₹", invoice["amount"])

        print("Status     :", invoice["payment_status"])


# ==========================================
# Search Invoice
# ==========================================

def search_invoice():

    invoices = get_invoices()

    invoice_id = input(
        "\nEnter Invoice ID : "
    ).strip()

    for invoice in invoices:

        if invoice["invoice_id"] == invoice_id:

            print("\n")
            print("=" * 60)
            print("         INVOICE DETAILS")
            print("=" * 60)

            print("Invoice ID     :", invoice["invoice_id"])

            print("Booking ID     :", invoice["booking_id"])

            print("Customer       :", invoice["customer_name"])

            print("Room Number    :", invoice["room_number"])

            print("Check-In       :", invoice["check_in"])

            print("Check-Out      :", invoice["check_out"])

            print("Days           :", invoice["days"])

            print("Amount         : ₹", invoice["amount"])

            print("Payment Status :", invoice["payment_status"])

            print("Generated On   :", invoice["generated_on"])

            return

    print("Invoice Not Found.")


# ==========================================
# Customer Invoice History
# ==========================================

def invoice_history():

    invoices = get_invoices()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    found = False

    print("\n")
    print("=" * 70)
    print("       CUSTOMER INVOICE HISTORY")
    print("=" * 70)

    for invoice in invoices:

        if invoice["customer_id"] == customer_id:

            found = True

            print("-" * 60)

            print("Invoice ID :", invoice["invoice_id"])

            print("Booking ID :", invoice["booking_id"])

            print("Amount     : ₹", invoice["amount"])

            print("Status     :", invoice["payment_status"])

            print("Date       :", invoice["generated_on"])

    if not found:

        print("No Invoice History Found.")
# ==========================================
# Make Payment
# ==========================================

def make_payment():

    invoices = get_invoices()

    payments = get_payments()

    invoice_id = input(
        "\nEnter Invoice ID : "
    ).strip()

    for invoice in invoices:

        if invoice["invoice_id"] == invoice_id:

            if invoice["payment_status"] == "Paid":

                print("Invoice Already Paid.")

                return

            payment_method = input(
                "Payment Method (Cash/Card/UPI): "
            ).strip()

            payment = {

                "payment_id": generate_payment_id(),

                "invoice_id": invoice["invoice_id"],

                "customer_id": invoice["customer_id"],

                "customer_name": invoice["customer_name"],

                "amount": invoice["amount"],

                "payment_method": payment_method,

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

            return

    print("Invoice Not Found.")


# ==========================================
# Update Payment Status
# ==========================================

def update_payment_status():

    invoices = get_invoices()

    invoice_id = input(
        "\nEnter Invoice ID : "
    ).strip()

    for invoice in invoices:

        if invoice["invoice_id"] == invoice_id:

            print("\nCurrent Status :", invoice["payment_status"])

            status = input(
                "New Status (Pending/Paid): "
            ).strip().title()

            if status not in [

                "Pending",

                "Paid"

            ]:

                print("Invalid Status.")

                return

            invoice["payment_status"] = status

            save_invoices(invoices)

            print("\nPayment Status Updated.")

            return

    print("Invoice Not Found.")


# ==========================================
# Payment History
# ==========================================

def payment_history():

    payments = get_payments()

    print("\n")
    print("=" * 70)
    print("          PAYMENT HISTORY")
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

        print("Date       :", payment["payment_date"])

        print("Status     :", payment["status"])


# ==========================================
# Payment Summary
# ==========================================

def payment_summary():

    payments = get_payments()

    total_amount = sum(

        payment["amount"]

        for payment in payments

    )

    print("\n")
    print("=" * 60)
    print("          PAYMENT SUMMARY")
    print("=" * 60)

    print("Total Payments :", len(payments))

    print("Total Revenue  : ₹", round(total_amount, 2))

    if payments:

        average = total_amount / len(payments)

        print(

            "Average Payment : ₹",

            round(average, 2)

        )


# ==========================================
# Outstanding Payments
# ==========================================

def outstanding_payments():

    invoices = get_invoices()

    print("\n")
    print("=" * 70)
    print("       OUTSTANDING PAYMENTS")
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

        print("No Outstanding Payments.")
import csv
import os
from datetime import datetime

# ==========================================
# Report Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Export Invoice Report
# ==========================================

def export_invoice_report():

    invoices = get_invoices()

    filename = os.path.join(
        REPORT_FOLDER,
        "Invoice_Report.csv"
    )

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Invoice ID",
            "Booking ID",
            "Customer",
            "Room",
            "Amount",
            "Payment Status",
            "Generated Date"
        ])

        for invoice in invoices:

            writer.writerow([
                invoice["invoice_id"],
                invoice["booking_id"],
                invoice["customer_name"],
                invoice["room_number"],
                invoice["amount"],
                invoice["payment_status"],
                invoice["generated_on"]
            ])

    print("\nInvoice Report Exported Successfully.")
    print("Saved To :", filename)


# ==========================================
# Revenue Report
# ==========================================

def revenue_report():

    payments = get_payments()

    total = sum(

        payment["amount"]

        for payment in payments

    )

    print("\n")
    print("=" * 60)
    print("         REVENUE REPORT")
    print("=" * 60)

    print("Total Payments :", len(payments))

    print("Total Revenue  : ₹", round(total, 2))


# ==========================================
# Daily Revenue Report
# ==========================================

def daily_revenue_report():

    payments = get_payments()

    today = datetime.now().strftime("%Y-%m-%d")

    total = 0

    print("\n")
    print("=" * 60)
    print("      DAILY REVENUE REPORT")
    print("=" * 60)

    for payment in payments:

        if payment["payment_date"].startswith(today):

            total += payment["amount"]

            print("-" * 50)

            print("Payment ID :", payment["payment_id"])

            print("Customer   :", payment["customer_name"])

            print("Amount     : ₹", payment["amount"])

    print("-" * 50)

    print("Today's Revenue : ₹", total)


# ==========================================
# Monthly Revenue Report
# ==========================================

def monthly_revenue_report():

    payments = get_payments()

    month = datetime.now().strftime("%Y-%m")

    total = 0

    print("\n")
    print("=" * 60)
    print("     MONTHLY REVENUE REPORT")
    print("=" * 60)

    for payment in payments:

        if payment["payment_date"].startswith(month):

            total += payment["amount"]

    print("Current Month :", month)

    print("Revenue       : ₹", round(total, 2))


# ==========================================
# Invoice Statistics
# ==========================================

def invoice_statistics():

    invoices = get_invoices()

    paid = len([

        invoice

        for invoice in invoices

        if invoice["payment_status"] == "Paid"

    ])

    pending = len([

        invoice

        for invoice in invoices

        if invoice["payment_status"] == "Pending"

    ])

    total_amount = sum(

        invoice["amount"]

        for invoice in invoices

    )

    print("\n")
    print("=" * 60)
    print("       INVOICE STATISTICS")
    print("=" * 60)

    print("Total Invoices :", len(invoices))

    print("Paid           :", paid)

    print("Pending        :", pending)

    print("Invoice Value  : ₹", round(total_amount, 2))
# ==========================================
# Invoice Dashboard
# ==========================================

def invoice_dashboard():

    invoices = get_invoices()

    payments = get_payments()

    paid = len([

        invoice

        for invoice in invoices

        if invoice["payment_status"] == "Paid"

    ])

    pending = len([

        invoice

        for invoice in invoices

        if invoice["payment_status"] == "Pending"

    ])

    revenue = sum(

        payment["amount"]

        for payment in payments

    )

    print("\n")
    print("=" * 60)
    print("         INVOICE DASHBOARD")
    print("=" * 60)

    print("Total Invoices :", len(invoices))

    print("Paid Invoices  :", paid)

    print("Pending Bills  :", pending)

    print("Revenue Earned : ₹", round(revenue, 2))


# ==========================================
# Payment Analytics
# ==========================================

def payment_analytics():

    payments = get_payments()

    cash = 0
    card = 0
    upi = 0

    for payment in payments:

        method = payment["payment_method"].lower()

        if method == "cash":

            cash += 1

        elif method == "card":

            card += 1

        elif method == "upi":

            upi += 1

    print("\n")
    print("=" * 60)
    print("        PAYMENT ANALYTICS")
    print("=" * 60)

    print("Cash Payments :", cash)

    print("Card Payments :", card)

    print("UPI Payments  :", upi)

    print("Total Payments:", len(payments))


# ==========================================
# Invoice Summary
# ==========================================

def invoice_summary():

    invoices = get_invoices()

    print("\n")
    print("=" * 90)
    print("             INVOICE SUMMARY")
    print("=" * 90)

    if len(invoices) == 0:

        print("No Invoice Records Found.")

        return

    print(

        "{:<15}{:<20}{:<12}{:<15}{:<15}".format(

            "Invoice ID",

            "Customer",

            "Room",

            "Amount",

            "Status"

        )

    )

    print("=" * 90)

    for invoice in invoices:

        print(

            "{:<15}{:<20}{:<12}{:<15}{:<15}".format(

                invoice["invoice_id"],

                invoice["customer_name"],

                invoice["room_number"],

                invoice["amount"],

                invoice["payment_status"]

            )

        )

    print("=" * 90)


# ==========================================
# Invoice Management Menu
# ==========================================

def invoice_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("        INVOICE MANAGEMENT")
        print("=" * 60)

        print("1. Generate Invoice")
        print("2. View Invoices")
        print("3. Search Invoice")
        print("4. Customer Invoice History")
        print("5. Make Payment")
        print("6. Update Payment Status")
        print("7. Payment History")
        print("8. Payment Summary")
        print("9. Outstanding Payments")
        print("10. Export Invoice Report")
        print("11. Revenue Report")
        print("12. Daily Revenue Report")
        print("13. Monthly Revenue Report")
        print("14. Invoice Statistics")
        print("15. Invoice Dashboard")
        print("16. Payment Analytics")
        print("17. Invoice Summary")
        print("18. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            generate_invoice()

        elif choice == "2":

            view_invoices()

        elif choice == "3":

            search_invoice()

        elif choice == "4":

            invoice_history()

        elif choice == "5":

            make_payment()

        elif choice == "6":

            update_payment_status()

        elif choice == "7":

            payment_history()

        elif choice == "8":

            payment_summary()

        elif choice == "9":

            outstanding_payments()

        elif choice == "10":

            export_invoice_report()

        elif choice == "11":

            revenue_report()

        elif choice == "12":

            daily_revenue_report()

        elif choice == "13":

            monthly_revenue_report()

        elif choice == "14":

            invoice_statistics()

        elif choice == "15":

            invoice_dashboard()

        elif choice == "16":

            payment_analytics()

        elif choice == "17":

            invoice_summary()

        elif choice == "18":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    invoice_menu()
