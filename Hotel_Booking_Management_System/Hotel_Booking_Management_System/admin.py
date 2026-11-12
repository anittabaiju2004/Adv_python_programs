# Admin panel
# admin.py (Part 1)

from database import (
    get_rooms,
    get_bookings,
    get_customers,
    get_staff
)


# ==========================================
# Hotel Statistics
# ==========================================

def hotel_statistics():

    rooms = get_rooms()

    bookings = get_bookings()

    customers = get_customers()

    staff = get_staff()

    available = len([
        room
        for room in rooms
        if room["status"] == "Available"
    ])

    occupied = len([
        room
        for room in rooms
        if room["status"] == "Occupied"
    ])

    maintenance = len([
        room
        for room in rooms
        if room["status"] == "Maintenance"
    ])

    print("\n")
    print("=" * 60)
    print("          HOTEL STATISTICS")
    print("=" * 60)

    print("Total Rooms       :", len(rooms))
    print("Available Rooms   :", available)
    print("Occupied Rooms    :", occupied)
    print("Maintenance Rooms :", maintenance)

    print("Total Customers   :", len(customers))
    print("Total Bookings    :", len(bookings))
    print("Total Staff       :", len(staff))


# ==========================================
# Room Summary
# ==========================================

def room_summary():

    rooms = get_rooms()

    print("\n")
    print("=" * 60)
    print("            ROOM SUMMARY")
    print("=" * 60)

    if len(rooms) == 0:

        print("No Room Records Found.")

        return

    for room in rooms:

        print("-" * 50)

        print("Room Number :", room["room_number"])

        print("Category    :", room["category"])

        print("Price       : ₹", room["price"])

        print("Status      :", room["status"])


# ==========================================
# Booking Summary
# ==========================================

def booking_summary():

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("          BOOKING SUMMARY")
    print("=" * 60)

    if len(bookings) == 0:

        print("No Booking Records Found.")

        return

    for booking in bookings:

        print("-" * 50)

        print("Booking ID :", booking["booking_id"])

        print("Customer   :", booking["customer_name"])

        print("Room No    :", booking["room_number"])

        print("Check-In   :", booking["check_in"])

        print("Check-Out  :", booking["check_out"])

        print("Status     :", booking["status"])


# ==========================================
# Customer Summary
# ==========================================

def customer_summary():

    customers = get_customers()

    print("\n")
    print("=" * 60)
    print("         CUSTOMER SUMMARY")
    print("=" * 60)

    if len(customers) == 0:

        print("No Customer Records Found.")

        return

    for customer in customers:

        print("-" * 50)

        print("Customer ID :", customer["customer_id"])

        print("Name        :", customer["name"])

        print("Phone       :", customer["phone"])

        print("Email       :", customer["email"])


# ==========================================
# Admin Dashboard
# ==========================================

def admin_dashboard():

    while True:

        print("\n")
        print("=" * 60)
        print("          ADMIN DASHBOARD")
        print("=" * 60)

        print("1. Hotel Statistics")
        print("2. Room Summary")
        print("3. Booking Summary")
        print("4. Customer Summary")
        print("5. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            hotel_statistics()

        elif choice == "2":

            room_summary()

        elif choice == "3":

            booking_summary()

        elif choice == "4":

            customer_summary()

        elif choice == "5":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")
# ==========================================
# Staff Summary
# ==========================================

def staff_summary():

    staff = get_staff()

    print("\n")
    print("=" * 60)
    print("           STAFF SUMMARY")
    print("=" * 60)

    if len(staff) == 0:

        print("No Staff Records Found.")

        return

    for employee in staff:

        print("-" * 50)

        print("Staff ID :", employee["staff_id"])
        print("Name     :", employee["name"])
        print("Role     :", employee["role"])
        print("Phone    :", employee["phone"])
        print("Shift    :", employee["shift"])


# ==========================================
# Revenue Dashboard
# ==========================================

def revenue_dashboard():

    bookings = get_bookings()

    total_revenue = 0

    for booking in bookings:

        total_revenue += booking.get(
            "total_amount",
            0
        )

    print("\n")
    print("=" * 60)
    print("         REVENUE DASHBOARD")
    print("=" * 60)

    print("Total Bookings :", len(bookings))
    print("Total Revenue  : ₹", round(total_revenue, 2))

    if len(bookings):

        average = total_revenue / len(bookings)

        print("Average Booking Value : ₹", round(average, 2))


# ==========================================
# Occupancy Report
# ==========================================

def occupancy_report():

    rooms = get_rooms()

    total_rooms = len(rooms)

    occupied = len([

        room

        for room in rooms

        if room["status"] == "Occupied"

    ])

    available = len([

        room

        for room in rooms

        if room["status"] == "Available"

    ])

    maintenance = len([

        room

        for room in rooms

        if room["status"] == "Maintenance"

    ])

    occupancy = 0

    if total_rooms:

        occupancy = (

            occupied /

            total_rooms

        ) * 100

    print("\n")
    print("=" * 60)
    print("         OCCUPANCY REPORT")
    print("=" * 60)

    print("Total Rooms      :", total_rooms)
    print("Occupied Rooms   :", occupied)
    print("Available Rooms  :", available)
    print("Maintenance      :", maintenance)
    print("Occupancy Rate   : {:.2f}%".format(
        occupancy
    ))


# ==========================================
# Booking Statistics
# ==========================================

def booking_statistics():

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
    print("        BOOKING STATISTICS")
    print("=" * 60)

    print("Total Bookings :", len(bookings))
    print("Confirmed      :", confirmed)
    print("Checked-In     :", checked_in)
    print("Checked-Out    :", checked_out)
    print("Cancelled      :", cancelled)


# ==========================================
# Customer Statistics
# ==========================================

def customer_statistics():

    customers = get_customers()

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("       CUSTOMER STATISTICS")
    print("=" * 60)

    print("Total Customers :", len(customers))

    if len(customers):

        average = round(

            len(bookings) /

            len(customers),

            2

        )

        print("Average Bookings Per Customer :", average)

    if bookings:

        highest = max(

            bookings,

            key=lambda booking: booking.get(
                "total_amount",
                0
            )

        )

        print("\nHighest Booking")

        print("-------------------------")

        print("Customer :", highest["customer_name"])
        print("Amount   : ₹", highest["total_amount"])


# ==========================================
# Admin Analytics Menu
# ==========================================

def analytics_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("         ADMIN ANALYTICS")
        print("=" * 60)

        print("1. Staff Summary")
        print("2. Revenue Dashboard")
        print("3. Occupancy Report")
        print("4. Booking Statistics")
        print("5. Customer Statistics")
        print("6. Back")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            staff_summary()

        elif choice == "2":

            revenue_dashboard()

        elif choice == "3":

            occupancy_report()

        elif choice == "4":

            booking_statistics()

        elif choice == "5":

            customer_statistics()

        elif choice == "6":

            break

        else:

            print("\nInvalid Choice.")
# ==========================================
# Imports
# ==========================================

from backup import backup_menu

from auth import logout


# ==========================================
# System Information
# ==========================================

def system_information():

    print("\n")
    print("=" * 60)
    print("         SYSTEM INFORMATION")
    print("=" * 60)

    print("Project Name : Hotel Booking Management System")
    print("Language     : Python 3")
    print("Database     : JSON File")
    print("Architecture : Modular Programming")
    print("Version      : 1.0")

    print("\nTechnologies")

    print("--------------------------")

    print("• Python")
    print("• JSON")
    print("• CSV")
    print("• ReportLab")
    print("• hashlib")
    print("• shutil")
    print("• datetime")

    print("=" * 60)


# ==========================================
# Hotel Information
# ==========================================

def hotel_information():

    rooms = get_rooms()

    customers = get_customers()

    bookings = get_bookings()

    staff = get_staff()

    print("\n")
    print("=" * 60)
    print("         HOTEL INFORMATION")
    print("=" * 60)

    print("Hotel Name       : Grand Palace Hotel")
    print("Hotel Category   : 5 Star")
    print("Total Rooms      :", len(rooms))
    print("Registered Guests:", len(customers))
    print("Total Bookings   :", len(bookings))
    print("Staff Members    :", len(staff))

    print("=" * 60)


# ==========================================
# Backup Management
# ==========================================

def backup_management():

    print("\nOpening Backup Module...")

    backup_menu()


# ==========================================
# Refresh Dashboard
# ==========================================

def refresh_dashboard():

    print("\nDashboard Refreshed Successfully.")

    hotel_statistics()


# ==========================================
# Administrator Panel
# ==========================================

def administrator_panel():

    while True:

        print("\n")
        print("=" * 60)
        print("        ADMINISTRATOR PANEL")
        print("=" * 60)

        print("1. Hotel Statistics")
        print("2. Room Summary")
        print("3. Booking Summary")
        print("4. Customer Summary")
        print("5. Staff Summary")
        print("6. Revenue Dashboard")
        print("7. Occupancy Report")
        print("8. Booking Statistics")
        print("9. Customer Statistics")
        print("10. Hotel Information")
        print("11. System Information")
        print("12. Backup Management")
        print("13. Refresh Dashboard")
        print("14. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            hotel_statistics()

        elif choice == "2":

            room_summary()

        elif choice == "3":

            booking_summary()

        elif choice == "4":

            customer_summary()

        elif choice == "5":

            staff_summary()

        elif choice == "6":

            revenue_dashboard()

        elif choice == "7":

            occupancy_report()

        elif choice == "8":

            booking_statistics()

        elif choice == "9":

            customer_statistics()

        elif choice == "10":

            hotel_information()

        elif choice == "11":

            system_information()

        elif choice == "12":

            backup_management()

        elif choice == "13":

            refresh_dashboard()

        elif choice == "14":

            logout()

            print("\nLogged Out Successfully.")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    administrator_panel()