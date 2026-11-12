# Reports
# report.py (Part 1)

from database import (
    get_bookings,
    get_customers,
    get_rooms,
    get_staff
)


# ==========================================
# Booking Report
# ==========================================

def booking_report():

    bookings = get_bookings()

    print("\n")
    print("=" * 80)
    print("              BOOKING REPORT")
    print("=" * 80)

    if len(bookings) == 0:

        print("No Booking Records Found.")

        return

    for booking in bookings:

        print("-" * 60)

        print("Booking ID :", booking["booking_id"])

        print("Customer   :", booking["customer_name"])

        print("Room No    :", booking["room_number"])

        print("Check-In   :", booking["check_in"])

        print("Check-Out  :", booking["check_out"])

        print("Amount     : ₹", booking["total_amount"])

        print("Status     :", booking["status"])


# ==========================================
# Customer Report
# ==========================================

def customer_report():

    customers = get_customers()

    print("\n")
    print("=" * 80)
    print("             CUSTOMER REPORT")
    print("=" * 80)

    if len(customers) == 0:

        print("No Customer Records Found.")

        return

    for customer in customers:

        print("-" * 60)

        print("Customer ID :", customer["customer_id"])

        print("Name        :", customer["name"])

        print("Phone       :", customer["phone"])

        print("Email       :", customer["email"])

        print("Nationality :", customer["nationality"])


# ==========================================
# Room Report
# ==========================================

def room_report():

    rooms = get_rooms()

    print("\n")
    print("=" * 80)
    print("               ROOM REPORT")
    print("=" * 80)

    if len(rooms) == 0:

        print("No Room Records Found.")

        return

    for room in rooms:

        print("-" * 60)

        print("Room Number :", room["room_number"])

        print("Category    :", room["category"])

        print("Price       : ₹", room["price"])

        print("Status      :", room["status"])


# ==========================================
# Staff Report
# ==========================================

def staff_report():

    staff = get_staff()

    print("\n")
    print("=" * 80)
    print("              STAFF REPORT")
    print("=" * 80)

    if len(staff) == 0:

        print("No Staff Records Found.")

        return

    for employee in staff:

        print("-" * 60)

        print("Staff ID :", employee["staff_id"])

        print("Name     :", employee["name"])

        print("Role     :", employee["role"])

        print("Phone    :", employee["phone"])

        print("Shift    :", employee["shift"])
from datetime import datetime
from database import (
    get_payments,
    get_invoices
)

# ==========================================
# Revenue Report
# ==========================================

def revenue_report():

    payments = get_payments()

    total_revenue = sum(

        payment["amount"]

        for payment in payments

        if payment["status"] == "Success"

    )

    print("\n")
    print("=" * 70)
    print("           REVENUE REPORT")
    print("=" * 70)

    print("Total Successful Payments :", len([

        payment

        for payment in payments

        if payment["status"] == "Success"

    ]))

    print("Total Revenue             : ₹", round(total_revenue, 2))


# ==========================================
# Payment Report
# ==========================================

def payment_report():

    payments = get_payments()

    print("\n")
    print("=" * 80)
    print("            PAYMENT REPORT")
    print("=" * 80)

    if len(payments) == 0:

        print("No Payment Records Found.")

        return

    for payment in payments:

        print("-" * 60)

        print("Payment ID :", payment["payment_id"])

        print("Invoice ID :", payment["invoice_id"])

        print("Customer   :", payment["customer_name"])

        print("Method     :", payment["payment_method"])

        print("Amount     : ₹", payment["amount"])

        print("Status     :", payment["status"])


# ==========================================
# Invoice Report
# ==========================================

def invoice_report():

    invoices = get_invoices()

    print("\n")
    print("=" * 80)
    print("            INVOICE REPORT")
    print("=" * 80)

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
# Daily Revenue Report
# ==========================================

def daily_revenue_report():

    payments = get_payments()

    today = datetime.now().strftime("%Y-%m-%d")

    revenue = 0

    print("\n")
    print("=" * 70)
    print("        DAILY REVENUE REPORT")
    print("=" * 70)

    for payment in payments:

        if (

            payment["status"] == "Success"

            and

            payment["payment_date"].startswith(today)

        ):

            revenue += payment["amount"]

            print("-" * 50)

            print("Payment ID :", payment["payment_id"])

            print("Customer   :", payment["customer_name"])

            print("Amount     : ₹", payment["amount"])

    print("-" * 50)

    print("Today's Revenue : ₹", round(revenue, 2))


# ==========================================
# Monthly Revenue Report
# ==========================================

def monthly_revenue_report():

    payments = get_payments()

    month = datetime.now().strftime("%Y-%m")

    revenue = 0

    transactions = 0

    print("\n")
    print("=" * 70)
    print("      MONTHLY REVENUE REPORT")
    print("=" * 70)

    for payment in payments:

        if (

            payment["status"] == "Success"

            and

            payment["payment_date"].startswith(month)

        ):

            revenue += payment["amount"]

            transactions += 1

    print("Current Month :", month)

    print("Transactions  :", transactions)

    print("Revenue       : ₹", round(revenue, 2))
