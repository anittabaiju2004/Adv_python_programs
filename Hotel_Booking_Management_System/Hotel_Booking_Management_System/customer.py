# Customer management
# customer.py (Part 1)

from datetime import datetime

from database import (
    get_bookings,
    get_customers,
    save_customers
)

from utils import (
    generate_customer_id,
    is_valid_phone,
    is_valid_email
)


# ==========================================
# Add Customer
# ==========================================

def add_customer():

    customers = get_customers()

    print("\n")
    print("=" * 60)
    print("         ADD CUSTOMER")
    print("=" * 60)

    name = input("Customer Name : ").strip()

    phone = input("Phone Number : ").strip()

    if not is_valid_phone(phone):

        print("Invalid Phone Number.")

        return

    for customer in customers:

        if customer["phone"] == phone:

            print("Phone Number Already Exists.")

            return

    email = input("Email : ").strip()

    if not is_valid_email(email):

        print("Invalid Email Address.")

        return

    address = input("Address : ").strip()

    gender = input("Gender : ").strip()

    nationality = input("Nationality : ").strip()

    id_proof = input(
        "ID Proof (Aadhar/Passport) : "
    ).strip()

    customer = {

        "customer_id": generate_customer_id(),

        "name": name,

        "phone": phone,

        "email": email,

        "address": address,

        "gender": gender,

        "nationality": nationality,

        "id_proof": id_proof,

        "registered_on": datetime.now().strftime(
            "%Y-%m-%d"
        )

    }

    customers.append(customer)

    save_customers(customers)

    print("\nCustomer Added Successfully.")

    print("Customer ID :", customer["customer_id"])


# ==========================================
# View Customers
# ==========================================

def view_customers():

    customers = get_customers()

    print("\n")
    print("=" * 80)
    print("            CUSTOMER LIST")
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
# Search Customer
# ==========================================

def search_customer():

    customers = get_customers()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    for customer in customers:

        if customer["customer_id"] == customer_id:

            print("\n")
            print("=" * 60)
            print("        CUSTOMER DETAILS")
            print("=" * 60)

            print("Customer ID  :", customer["customer_id"])
            print("Name         :", customer["name"])
            print("Phone        :", customer["phone"])
            print("Email        :", customer["email"])
            print("Address      :", customer["address"])
            print("Gender       :", customer["gender"])
            print("Nationality  :", customer["nationality"])
            print("ID Proof     :", customer["id_proof"])
            print("Registered   :", customer["registered_on"])

            return

    print("Customer Not Found.")


# ==========================================
# Customer Profile
# ==========================================

def customer_profile():

    customers = get_customers()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    for customer in customers:

        if customer["customer_id"] == customer_id:

            print("\n")
            print("=" * 60)
            print("        CUSTOMER PROFILE")
            print("=" * 60)

            print("Customer ID :", customer["customer_id"])
            print("Name        :", customer["name"])
            print("Phone       :", customer["phone"])
            print("Email       :", customer["email"])
            print("Address     :", customer["address"])
            print("Gender      :", customer["gender"])
            print("Nationality :", customer["nationality"])
            print("ID Proof    :", customer["id_proof"])
            print("Member Since:", customer["registered_on"])

            return

    print("Customer Not Found.")
# ==========================================
# Update Customer
# ==========================================

def update_customer():

    customers = get_customers()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    for customer in customers:

        if customer["customer_id"] == customer_id:

            print("\nLeave blank to keep current value.\n")

            name = input(
                f"Name [{customer['name']}] : "
            ).strip()

            if name:

                customer["name"] = name

            phone = input(
                f"Phone [{customer['phone']}] : "
            ).strip()

            if phone:

                if not is_valid_phone(phone):

                    print("Invalid Phone Number.")

                    return

                customer["phone"] = phone

            email = input(
                f"Email [{customer['email']}] : "
            ).strip()

            if email:

                if not is_valid_email(email):

                    print("Invalid Email Address.")

                    return

                customer["email"] = email

            address = input(
                f"Address [{customer['address']}] : "
            ).strip()

            if address:

                customer["address"] = address

            nationality = input(
                f"Nationality [{customer['nationality']}] : "
            ).strip()

            if nationality:

                customer["nationality"] = nationality

            save_customers(customers)

            print("\nCustomer Updated Successfully.")

            return

    print("Customer Not Found.")


# ==========================================
# Delete Customer
# ==========================================

def delete_customer():

    customers = get_customers()

    bookings = get_bookings()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    for customer in customers:

        if customer["customer_id"] == customer_id:

            active = False

            for booking in bookings:

                if (

                    booking["customer_id"] == customer_id

                    and

                    booking["status"] != "Checked-Out"

                    and

                    booking["status"] != "Cancelled"

                ):

                    active = True

                    break

            if active:

                print(
                    "Customer has active bookings."
                )

                return

            confirm = input(

                "Delete Customer? (Y/N): "

            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")

                return

            customers.remove(customer)

            save_customers(customers)

            print("\nCustomer Deleted Successfully.")

            return

    print("Customer Not Found.")


# ==========================================
# Customer Booking History
# ==========================================

def customer_booking_history():

    bookings = get_bookings()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    found = False

    print("\n")
    print("=" * 70)
    print("      CUSTOMER BOOKING HISTORY")
    print("=" * 70)

    for booking in bookings:

        if booking["customer_id"] == customer_id:

            found = True

            print("-" * 60)

            print("Booking ID :", booking["booking_id"])
            print("Room No    :", booking["room_number"])
            print("Category   :", booking["room_category"])
            print("Check-In   :", booking["check_in"])
            print("Check-Out  :", booking["check_out"])
            print("Amount     : ₹", booking["total_amount"])
            print("Status     :", booking["status"])

    if not found:

        print("No Booking History Found.")


# ==========================================
# Customer Stay History
# ==========================================

def customer_stay_history():

    bookings = get_bookings()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    completed = [

        booking

        for booking in bookings

        if (

            booking["customer_id"] == customer_id

            and

            booking["status"] == "Checked-Out"

        )

    ]

    print("\n")
    print("=" * 70)
    print("        CUSTOMER STAY HISTORY")
    print("=" * 70)

    if len(completed) == 0:

        print("No Completed Stays Found.")

        return

    total_days = 0

    total_spent = 0

    for booking in completed:

        total_days += booking["days"]

        total_spent += booking["total_amount"]

        print("-" * 60)

        print("Room Number :", booking["room_number"])
        print("Check-In    :", booking["check_in"])
        print("Check-Out   :", booking["check_out"])
        print("Days        :", booking["days"])
        print("Bill        : ₹", booking["total_amount"])

    print("-" * 60)

    print("Total Stays :", len(completed))
    print("Total Days  :", total_days)
    print("Total Spent : ₹", total_spent)


# ==========================================
# Customer Statistics
# ==========================================

def customer_statistics():

    customers = get_customers()

    bookings = get_bookings()

    total_revenue = sum(

        booking["total_amount"]

        for booking in bookings

        if booking["status"] == "Checked-Out"

    )

    print("\n")
    print("=" * 60)
    print("       CUSTOMER STATISTICS")
    print("=" * 60)

    print("Registered Customers :", len(customers))

    print("Total Bookings        :", len(bookings))

    print("Completed Stays       :", len([

        booking

        for booking in bookings

        if booking["status"] == "Checked-Out"

    ]))

    print("Total Revenue         : ₹", round(total_revenue, 2))

    if len(customers):

        average = len(bookings) / len(customers)

        print(

            "Average Bookings/Customer :",

            round(average, 2)

        )
import csv
import os

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# VIP Customer Report
# ==========================================

def vip_customers():

    customers = get_customers()

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("         VIP CUSTOMERS")
    print("=" * 60)

    found = False

    for customer in customers:

        total_spent = sum(

            booking["total_amount"]

            for booking in bookings

            if (

                booking["customer_id"] == customer["customer_id"]

                and

                booking["status"] == "Checked-Out"

            )

        )

        if total_spent >= 50000:

            found = True

            print("-" * 50)

            print("Customer :", customer["name"])

            print("Phone    :", customer["phone"])

            print("Spent    : ₹", total_spent)

    if not found:

        print("No VIP Customers Found.")


# ==========================================
# Frequent Customer Report
# ==========================================

def frequent_customers():

    customers = get_customers()

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("      FREQUENT CUSTOMERS")
    print("=" * 60)

    found = False

    for customer in customers:

        visits = len([

            booking

            for booking in bookings

            if (

                booking["customer_id"] == customer["customer_id"]

                and

                booking["status"] == "Checked-Out"

            )

        ])

        if visits >= 3:

            found = True

            print("-" * 50)

            print("Customer :", customer["name"])

            print("Visits   :", visits)

    if not found:

        print("No Frequent Customers Found.")


# ==========================================
# Export Customer Report
# ==========================================

def export_customer_report():

    customers = get_customers()

    filename = os.path.join(

        REPORT_FOLDER,

        "Customer_Report.csv"

    )

    with open(

        filename,

        "w",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Customer ID",

            "Name",

            "Phone",

            "Email",

            "Nationality",

            "Registered On"

        ])

        for customer in customers:

            writer.writerow([

                customer["customer_id"],

                customer["name"],

                customer["phone"],

                customer["email"],

                customer["nationality"],

                customer["registered_on"]

            ])

    print("\nCustomer Report Exported Successfully.")

    print("Saved To :", filename)


# ==========================================
# Customer Dashboard
# ==========================================

def customer_dashboard():

    customers = get_customers()

    bookings = get_bookings()

    total_revenue = sum(

        booking["total_amount"]

        for booking in bookings

        if booking["status"] == "Checked-Out"

    )

    print("\n")
    print("=" * 60)
    print("       CUSTOMER DASHBOARD")
    print("=" * 60)

    print("Registered Customers :", len(customers))

    print("Total Bookings       :", len(bookings))

    print("Revenue Generated    : ₹", round(total_revenue, 2))

    if customers:

        average = len(bookings) / len(customers)

        print(

            "Average Bookings/Customer :",

            round(average, 2)

        )


# ==========================================
# Customer Summary
# ==========================================

def customer_summary():

    customers = get_customers()

    bookings = get_bookings()

    print("\n")
    print("=" * 80)
    print("            CUSTOMER SUMMARY")
    print("=" * 80)

    if len(customers) == 0:

        print("No Customer Records Found.")

        return

    print(

        "{:<12}{:<20}{:<10}{:<15}".format(

            "Customer ID",

            "Name",

            "Bookings",

            "Total Spent"

        )

    )

    print("=" * 80)

    for customer in customers:

        customer_bookings = [

            booking

            for booking in bookings

            if booking["customer_id"] == customer["customer_id"]

        ]

        total_spent = sum(

            booking["total_amount"]

            for booking in customer_bookings

            if booking["status"] == "Checked-Out"

        )

        print(

            "{:<12}{:<20}{:<10}{:<15}".format(

                customer["customer_id"],

                customer["name"],

                len(customer_bookings),

                f"₹{total_spent}"

            )

        )

    print("=" * 80)
# ==========================================
# Customer Analytics
# ==========================================

def customer_analytics():

    customers = get_customers()

    bookings = get_bookings()

    print("\n")
    print("=" * 60)
    print("        CUSTOMER ANALYTICS")
    print("=" * 60)

    total_bookings = len(bookings)

    completed = len([

        booking

        for booking in bookings

        if booking["status"] == "Checked-Out"

    ])

    cancelled = len([

        booking

        for booking in bookings

        if booking["status"] == "Cancelled"

    ])

    revenue = sum(

        booking["total_amount"]

        for booking in bookings

        if booking["status"] == "Checked-Out"

    )

    print("Registered Customers :", len(customers))
    print("Total Bookings       :", total_bookings)
    print("Completed Bookings   :", completed)
    print("Cancelled Bookings   :", cancelled)
    print("Revenue Generated    : ₹", round(revenue, 2))


# ==========================================
# Validate Customer
# ==========================================

def validate_customer():

    customers = get_customers()

    customer_id = input(
        "\nEnter Customer ID : "
    ).strip()

    for customer in customers:

        if customer["customer_id"] == customer_id:

            print("\nCustomer Record Verified.")

            print("Name :", customer["name"])

            return True

    print("Customer Not Found.")

    return False


# ==========================================
# Customer Performance Report
# ==========================================

def customer_performance():

    customers = get_customers()

    bookings = get_bookings()

    print("\n")
    print("=" * 80)
    print("      CUSTOMER PERFORMANCE REPORT")
    print("=" * 80)

    if len(customers) == 0:

        print("No Customer Records Found.")

        return

    highest_customer = None

    highest_spent = 0

    for customer in customers:

        spent = sum(

            booking["total_amount"]

            for booking in bookings

            if (

                booking["customer_id"] == customer["customer_id"]

                and

                booking["status"] == "Checked-Out"

            )

        )

        if spent > highest_spent:

            highest_spent = spent

            highest_customer = customer

    if highest_customer:

        print("Best Customer")

        print("-" * 40)

        print("Customer ID :", highest_customer["customer_id"])

        print("Name        :", highest_customer["name"])

        print("Phone       :", highest_customer["phone"])

        print("Total Spent : ₹", highest_spent)


# ==========================================
# Customer Management Menu
# ==========================================

def customer_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("       CUSTOMER MANAGEMENT")
        print("=" * 60)

        print("1. Add Customer")
        print("2. View Customers")
        print("3. Search Customer")
        print("4. Customer Profile")
        print("5. Update Customer")
        print("6. Delete Customer")
        print("7. Booking History")
        print("8. Stay History")
        print("9. Customer Statistics")
        print("10. VIP Customers")
        print("11. Frequent Customers")
        print("12. Export Customer Report")
        print("13. Customer Dashboard")
        print("14. Customer Summary")
        print("15. Customer Analytics")
        print("16. Validate Customer")
        print("17. Customer Performance")
        print("18. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            add_customer()

        elif choice == "2":

            view_customers()

        elif choice == "3":

            search_customer()

        elif choice == "4":

            customer_profile()

        elif choice == "5":

            update_customer()

        elif choice == "6":

            delete_customer()

        elif choice == "7":

            customer_booking_history()

        elif choice == "8":

            customer_stay_history()

        elif choice == "9":

            customer_statistics()

        elif choice == "10":

            vip_customers()

        elif choice == "11":

            frequent_customers()

        elif choice == "12":

            export_customer_report()

        elif choice == "13":

            customer_dashboard()

        elif choice == "14":

            customer_summary()

        elif choice == "15":

            customer_analytics()

        elif choice == "16":

            validate_customer()

        elif choice == "17":

            customer_performance()

        elif choice == "18":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    customer_menu()