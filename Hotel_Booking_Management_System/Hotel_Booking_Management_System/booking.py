# Booking management
# booking.py (Part 1)

from datetime import datetime

from database import (
    get_rooms,
    save_rooms,
    get_bookings,
    save_bookings,
    get_customers
)

from utils import (
    generate_booking_id
)


# ==========================================
# Book Room
# ==========================================

def book_room():

    rooms = get_rooms()
    bookings = get_bookings()
    customers = get_customers()

    print("\n")
    print("=" * 60)
    print("            ROOM BOOKING")
    print("=" * 60)

    customer_id = input("Customer ID : ").strip()

    customer = None

    for c in customers:

        if c["customer_id"] == customer_id:

            customer = c
            break

    if customer is None:

        print("Customer Not Found.")

        return

    room_number = input("Room Number : ").strip()

    room = None

    for r in rooms:

        if r["room_number"] == room_number:

            room = r
            break

    if room is None:

        print("Room Not Found.")

        return

    if room["status"] != "Available":

        print("Room Not Available.")

        return

    check_in = input(
        "Check-In Date (YYYY-MM-DD) : "
    ).strip()

    check_out = input(
        "Check-Out Date (YYYY-MM-DD) : "
    ).strip()

    try:

        in_date = datetime.strptime(
            check_in,
            "%Y-%m-%d"
        )

        out_date = datetime.strptime(
            check_out,
            "%Y-%m-%d"
        )

    except ValueError:

        print("Invalid Date Format.")

        return

    if out_date <= in_date:

        print("Check-Out Date Must Be After Check-In.")

        return

    days = (out_date - in_date).days

    total_amount = days * room["price"]

    booking = {

        "booking_id": generate_booking_id(),

        "customer_id": customer_id,

        "customer_name": customer["name"],

        "room_number": room_number,

        "room_category": room["category"],

        "check_in": check_in,

        "check_out": check_out,

        "days": days,

        "price_per_day": room["price"],

        "total_amount": total_amount,

        "booking_date": datetime.now().strftime(
            "%Y-%m-%d"
        ),

        "status": "Confirmed"

    }

    bookings.append(booking)

    room["status"] = "Occupied"

    save_bookings(bookings)

    save_rooms(rooms)

    print("\nRoom Booked Successfully.")

    print("Booking ID :", booking["booking_id"])

    print("Total Bill : ₹", total_amount)


# ==========================================
# View All Bookings
# ==========================================

def view_bookings():

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("          BOOKING LIST")
    print("=" * 60)

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
        print("Status     :", booking["status"])


# ==========================================
# Search Booking
# ==========================================

def search_booking():

    bookings = get_bookings()

    booking_id = input(
        "\nEnter Booking ID : "
    ).strip()

    for booking in bookings:

        if booking["booking_id"] == booking_id:

            print("\n")
            print("=" * 60)
            print("         BOOKING DETAILS")
            print("=" * 60)

            print("Booking ID     :", booking["booking_id"])
            print("Customer ID    :", booking["customer_id"])
            print("Customer Name  :", booking["customer_name"])
            print("Room Number    :", booking["room_number"])
            print("Room Category  :", booking["room_category"])
            print("Check-In       :", booking["check_in"])
            print("Check-Out      :", booking["check_out"])
            print("Days           :", booking["days"])
            print("Total Amount   : ₹", booking["total_amount"])
            print("Status         :", booking["status"])

            return

    print("Booking Not Found.")


# ==========================================
# Customer Booking History
# ==========================================

def booking_history():

    bookings = get_bookings()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    found = False

    print("\n")
    print("=" * 60)
    print("       CUSTOMER BOOKING HISTORY")
    print("=" * 60)

    for booking in bookings:

        if booking["customer_id"] == customer_id:

            found = True

            print("-" * 60)

            print("Booking ID :", booking["booking_id"])
            print("Room No    :", booking["room_number"])
            print("Check-In   :", booking["check_in"])
            print("Check-Out  :", booking["check_out"])
            print("Bill       : ₹", booking["total_amount"])
            print("Status     :", booking["status"])

    if not found:

        print("No Booking History Found.")
# ==========================================
# Update Booking
# ==========================================

def update_booking():

    bookings = get_bookings()

    booking_id = input("\nEnter Booking ID : ").strip()

    for booking in bookings:

        if booking["booking_id"] == booking_id:

            print("\nLeave blank to keep current value.\n")

            check_in = input(
                f"Check-In [{booking['check_in']}] : "
            ).strip()

            if check_in:

                booking["check_in"] = check_in

            check_out = input(
                f"Check-Out [{booking['check_out']}] : "
            ).strip()

            if check_out:

                booking["check_out"] = check_out

            try:

                in_date = datetime.strptime(
                    booking["check_in"],
                    "%Y-%m-%d"
                )

                out_date = datetime.strptime(
                    booking["check_out"],
                    "%Y-%m-%d"
                )

                booking["days"] = (
                    out_date - in_date
                ).days

                booking["total_amount"] = (

                    booking["days"]

                    * booking["price_per_day"]

                )

            except ValueError:

                print("Invalid Date Format.")

                return

            save_bookings(bookings)

            print("\nBooking Updated Successfully.")

            return

    print("Booking Not Found.")


# ==========================================
# Cancel Booking
# ==========================================

def cancel_booking():

    bookings = get_bookings()

    rooms = get_rooms()

    booking_id = input(
        "\nEnter Booking ID : "
    ).strip()

    for booking in bookings:

        if booking["booking_id"] == booking_id:

            if booking["status"] == "Cancelled":

                print("Booking Already Cancelled.")

                return

            booking["status"] = "Cancelled"

            for room in rooms:

                if room["room_number"] == booking["room_number"]:

                    room["status"] = "Available"

                    break

            save_bookings(bookings)

            save_rooms(rooms)

            print("\nBooking Cancelled Successfully.")

            return

    print("Booking Not Found.")


# ==========================================
# Check Room Availability
# ==========================================

def check_room_availability():

    rooms = get_rooms()

    available = [

        room

        for room in rooms

        if room["status"] == "Available"

    ]

    print("\n")
    print("=" * 60)
    print("        AVAILABLE ROOMS")
    print("=" * 60)

    if len(available) == 0:

        print("No Rooms Available.")

        return

    for room in available:

        print("-" * 50)

        print("Room Number :", room["room_number"])

        print("Category    :", room["category"])

        print("Price       : ₹", room["price"])


# ==========================================
# Search by Room Category
# ==========================================

def search_room_category():

    rooms = get_rooms()

    category = input(
        "\nEnter Room Category : "
    ).strip().lower()

    found = False

    print("\n")
    print("=" * 60)
    print("       ROOM CATEGORY SEARCH")
    print("=" * 60)

    for room in rooms:

        if room["category"].lower() == category:

            found = True

            print("-" * 50)

            print("Room Number :", room["room_number"])

            print("Price       : ₹", room["price"])

            print("Status      :", room["status"])

    if not found:

        print("No Rooms Found.")


# ==========================================
# Booking Status Report
# ==========================================

def booking_status_report():

    bookings = get_bookings()

    confirmed = len([

        booking

        for booking in bookings

        if booking["status"] == "Confirmed"

    ])

    checked_in = len([

        booking

        for booking in bookings

        if booking["status"] == "Checked-In"

    ])

    checked_out = len([

        booking

        for booking in bookings

        if booking["status"] == "Checked-Out"

    ])

    cancelled = len([

        booking

        for booking in bookings

        if booking["status"] == "Cancelled"

    ])

    print("\n")
    print("=" * 60)
    print("       BOOKING STATUS REPORT")
    print("=" * 60)

    print("Total Bookings :", len(bookings))
    print("Confirmed      :", confirmed)
    print("Checked-In     :", checked_in)
    print("Checked-Out    :", checked_out)
    print("Cancelled      :", cancelled)
# ==========================================
# Check-In Customer
# ==========================================

def check_in():

    bookings = get_bookings()

    booking_id = input("\nEnter Booking ID : ").strip()

    for booking in bookings:

        if booking["booking_id"] == booking_id:

            if booking["status"] == "Checked-In":

                print("Customer Already Checked-In.")

                return

            if booking["status"] == "Cancelled":

                print("Cancelled Booking.")

                return

            booking["status"] = "Checked-In"

            booking["check_in_time"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            save_bookings(bookings)

            print("\nCustomer Checked-In Successfully.")

            return

    print("Booking Not Found.")


# ==========================================
# Check-Out Customer
# ==========================================

def check_out():

    bookings = get_bookings()

    rooms = get_rooms()

    booking_id = input("\nEnter Booking ID : ").strip()

    for booking in bookings:

        if booking["booking_id"] == booking_id:

            if booking["status"] != "Checked-In":

                print("Customer Is Not Checked-In.")

                return

            booking["status"] = "Checked-Out"

            booking["check_out_time"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            for room in rooms:

                if room["room_number"] == booking["room_number"]:

                    room["status"] = "Available"

                    break

            save_bookings(bookings)

            save_rooms(rooms)

            print("\nCustomer Checked-Out Successfully.")

            print("Total Bill : ₹", booking["total_amount"])

            return

    print("Booking Not Found.")


# ==========================================
# Booking Statistics
# ==========================================

def booking_statistics():

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("        BOOKING STATISTICS")
    print("=" * 60)

    confirmed = 0
    checked_in = 0
    checked_out = 0
    cancelled = 0

    for booking in bookings:

        if booking["status"] == "Confirmed":

            confirmed += 1

        elif booking["status"] == "Checked-In":

            checked_in += 1

        elif booking["status"] == "Checked-Out":

            checked_out += 1

        elif booking["status"] == "Cancelled":

            cancelled += 1

    print("Total Bookings :", len(bookings))
    print("Confirmed      :", confirmed)
    print("Checked-In     :", checked_in)
    print("Checked-Out    :", checked_out)
    print("Cancelled      :", cancelled)


# ==========================================
# Occupancy Report
# ==========================================

def occupancy_report():

    rooms = get_rooms()

    total_rooms = len(rooms)

    occupied = 0
    available = 0
    maintenance = 0

    for room in rooms:

        if room["status"] == "Occupied":

            occupied += 1

        elif room["status"] == "Available":

            available += 1

        elif room["status"] == "Maintenance":

            maintenance += 1

    percentage = 0

    if total_rooms > 0:

        percentage = (occupied / total_rooms) * 100

    print("\n")
    print("=" * 60)
    print("         OCCUPANCY REPORT")
    print("=" * 60)

    print("Total Rooms      :", total_rooms)
    print("Occupied Rooms   :", occupied)
    print("Available Rooms  :", available)
    print("Maintenance      :", maintenance)
    print("Occupancy Rate   : {:.2f}%".format(percentage))


# ==========================================
# Revenue Summary
# ==========================================

def revenue_summary():

    bookings = get_bookings()

    total_revenue = 0
    completed = 0

    for booking in bookings:

        if booking["status"] == "Checked-Out":

            total_revenue += booking["total_amount"]

            completed += 1

    average = 0

    if completed > 0:

        average = total_revenue / completed

    print("\n")
    print("=" * 60)
    print("         REVENUE SUMMARY")
    print("=" * 60)

    print("Completed Bookings :", completed)

    print("Total Revenue      : ₹", round(total_revenue, 2))

    print("Average Revenue    : ₹", round(average, 2))
import csv
import os

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Export Booking Report
# ==========================================

def export_booking_report():

    bookings = get_bookings()

    if len(bookings) == 0:

        print("\nNo Booking Records Found.")

        return

    filename = os.path.join(

        REPORT_FOLDER,

        "Booking_Report.csv"

    )

    with open(

        filename,

        "w",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Booking ID",
            "Customer",
            "Room No",
            "Category",
            "Check-In",
            "Check-Out",
            "Days",
            "Amount",
            "Status"

        ])

        for booking in bookings:

            writer.writerow([

                booking["booking_id"],
                booking["customer_name"],
                booking["room_number"],
                booking["room_category"],
                booking["check_in"],
                booking["check_out"],
                booking["days"],
                booking["total_amount"],
                booking["status"]

            ])

    print("\nBooking Report Exported Successfully.")
    print("Saved To :", filename)


# ==========================================
# Booking Dashboard
# ==========================================

def booking_dashboard():

    bookings = get_bookings()

    rooms = get_rooms()

    total_revenue = sum(

        booking["total_amount"]

        for booking in bookings

        if booking["status"] == "Checked-Out"

    )

    print("\n")
    print("=" * 60)
    print("         BOOKING DASHBOARD")
    print("=" * 60)

    print("Total Rooms      :", len(rooms))
    print("Total Bookings   :", len(bookings))

    print(

        "Completed Stay  :",

        len([

            booking

            for booking in bookings

            if booking["status"] == "Checked-Out"

        ])

    )

    print(

        "Checked-In      :",

        len([

            booking

            for booking in bookings

            if booking["status"] == "Checked-In"

        ])

    )

    print("Revenue Earned  : ₹", round(total_revenue, 2))


# ==========================================
# Booking Summary
# ==========================================

def booking_summary():

    bookings = get_bookings()

    if len(bookings) == 0:

        print("\nNo Booking Records Found.")

        return

    print("\n")
    print("=" * 90)

    print(

        "{:<15}{:<20}{:<10}{:<15}{:<15}".format(

            "Booking ID",

            "Customer",

            "Room",

            "Amount",

            "Status"

        )

    )

    print("=" * 90)

    for booking in bookings:

        print(

            "{:<15}{:<20}{:<10}{:<15}{:<15}".format(

                booking["booking_id"],

                booking["customer_name"],

                booking["room_number"],

                booking["total_amount"],

                booking["status"]

            )

        )

    print("=" * 90)


# ==========================================
# Booking Menu
# ==========================================

def booking_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("        BOOKING MANAGEMENT")
        print("=" * 60)

        print("1. Book Room")
        print("2. View Bookings")
        print("3. Search Booking")
        print("4. Booking History")
        print("5. Update Booking")
        print("6. Cancel Booking")
        print("7. Room Availability")
        print("8. Search Room Category")
        print("9. Booking Status Report")
        print("10. Check-In")
        print("11. Check-Out")
        print("12. Booking Statistics")
        print("13. Occupancy Report")
        print("14. Revenue Summary")
        print("15. Export Booking Report")
        print("16. Booking Dashboard")
        print("17. Booking Summary")
        print("18. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            book_room()

        elif choice == "2":

            view_bookings()

        elif choice == "3":

            search_booking()

        elif choice == "4":

            booking_history()

        elif choice == "5":

            update_booking()

        elif choice == "6":

            cancel_booking()

        elif choice == "7":

            check_room_availability()

        elif choice == "8":

            search_room_category()

        elif choice == "9":

            booking_status_report()

        elif choice == "10":

            check_in()

        elif choice == "11":

            check_out()

        elif choice == "12":

            booking_statistics()

        elif choice == "13":

            occupancy_report()

        elif choice == "14":

            revenue_summary()

        elif choice == "15":

            export_booking_report()

        elif choice == "16":

            booking_dashboard()

        elif choice == "17":

            booking_summary()

        elif choice == "18":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    booking_menu()