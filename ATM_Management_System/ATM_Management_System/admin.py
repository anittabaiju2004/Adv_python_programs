# Admin operations
# admin.py

from database import (
    get_admins,
    get_customers,
    get_transactions,
    save_customers
)

from utils import (
    current_datetime
)

from report import (
    generate_customer_report,
    generate_transaction_report,
    report_menu
)

from backup import (
    backup_database,
    restore_database
)


# ==========================================
# Admin Login
# ==========================================

def admin_login():

    admins = get_admins()

    print("\n========== ADMIN LOGIN ==========\n")

    username = input("Username : ").strip()
    password = input("Password : ").strip()

    for admin in admins:

        if (
            admin["username"] == username
            and admin["password"] == password
        ):

            print("\nLogin Successful.")

            admin_dashboard()

            return

    print("\nInvalid Username or Password.")


# ==========================================
# View All Customers
# ==========================================

def view_customers():

    customers = get_customers()

    if len(customers) == 0:

        print("\nNo Customer Records Found.")

        return

    print("\n========== CUSTOMER LIST ==========\n")

    print(
        "{:<12} {:<20} {:<12} {:>12} {:<10}".format(
            "Account",
            "Name",
            "Phone",
            "Balance",
            "Status"
        )
    )

    print("-" * 75)

    for customer in customers:

        print(
            "{:<12} {:<20} {:<12} ₹{:>10.2f} {:<10}".format(
                customer["account_number"],
                customer["name"],
                customer["phone"],
                customer["balance"],
                customer["status"]
            )
        )


# ==========================================
# Search Customer
# ==========================================

def search_customer():

    customers = get_customers()

    account_number = input(
        "\nEnter Account Number : "
    ).strip()

    for customer in customers:

        if customer["account_number"] == account_number:

            print("\n========== CUSTOMER DETAILS ==========\n")

            print("Account Number :", customer["account_number"])
            print("Name           :", customer["name"])
            print("Age            :", customer["age"])
            print("Gender         :", customer["gender"])
            print("Phone          :", customer["phone"])
            print("Email          :", customer["email"])
            print("Address        :", customer["address"])
            print("Balance        : ₹", customer["balance"])
            print("Status         :", customer["status"])
            print("Created Date   :", customer["created_date"])

            return

    print("\nCustomer Not Found.")


# ==========================================
# Admin Dashboard
# ==========================================

def admin_dashboard():

    while True:

        print("\n")
        print("=" * 50)
        print("           ADMIN DASHBOARD")
        print("=" * 50)

        print("1. View Customers")
        print("2. Search Customer")
        print("3. Freeze Account")
        print("4. Unfreeze Account")
        print("5. Delete Account")
        print("6. View Transactions")
        print("7. Generate Reports")
        print("8. Backup Database")
        print("9. Restore Database")
        print("10. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            view_customers()

        elif choice == "2":

            search_customer()

        elif choice == "3":

            freeze_account()

        elif choice == "4":

            unfreeze_account()

        elif choice == "5":

            delete_account()

        elif choice == "6":

            view_transactions()

        elif choice == "7":

            report_menu()

        elif choice == "8":

            backup_database()

        elif choice == "9":

            restore_database()

        elif choice == "10":

            print("\nAdmin Logged Out Successfully.")

            break

        else:

            print("\nInvalid Choice.")
# ==========================================
# Freeze Customer Account
# ==========================================

def freeze_account():

    customers = get_customers()

    print("\n========== FREEZE ACCOUNT ==========\n")

    account_number = input("Enter Account Number : ").strip()

    for customer in customers:

        if customer["account_number"] == account_number:

            if customer["status"] == "Frozen":

                print("Account Already Frozen.")

                return

            customer["status"] = "Frozen"

            save_customers(customers)

            print("\nAccount Frozen Successfully.")

            return

    print("Customer Not Found.")


# ==========================================
# Unfreeze Customer Account
# ==========================================

def unfreeze_account():

    customers = get_customers()

    print("\n========== UNFREEZE ACCOUNT ==========\n")

    account_number = input("Enter Account Number : ").strip()

    for customer in customers:

        if customer["account_number"] == account_number:

            if customer["status"] == "Active":

                print("Account Already Active.")

                return

            customer["status"] = "Active"

            save_customers(customers)

            print("\nAccount Activated Successfully.")

            return

    print("Customer Not Found.")


# ==========================================
# Delete Customer Account
# ==========================================

def delete_account():

    customers = get_customers()

    print("\n========== DELETE ACCOUNT ==========\n")

    account_number = input("Enter Account Number : ").strip()

    for customer in customers:

        if customer["account_number"] == account_number:

            confirm = input(
                f"Delete account of {customer['name']} (Y/N): "
            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")

                return

            customers.remove(customer)

            save_customers(customers)

            print("\nAccount Deleted Successfully.")

            return

    print("Customer Not Found.")


# ==========================================
# View Transactions
# ==========================================

def view_transactions():

    transactions = get_transactions()

    if len(transactions) == 0:

        print("\nNo Transactions Available.")

        return

    print("\n========== TRANSACTION HISTORY ==========\n")

    print(
        "{:<12} {:<12} {:<15} {:>12} {:<20}".format(
            "Trans ID",
            "Account",
            "Type",
            "Amount",
            "Date"
        )
    )

    print("-" * 80)

    for transaction in transactions:

        print(
            "{:<12} {:<12} {:<15} ₹{:>10.2f} {:<20}".format(
                transaction["transaction_id"],
                transaction["account_number"],
                transaction["type"],
                transaction["amount"],
                transaction["date"]
            )
        )

        # Display receiver account for transfer
        if (
            transaction["type"] == "Transfer"
            and "receiver_account" in transaction
        ):

            print(
                " " * 14 +
                f"Transferred To : {transaction['receiver_account']}"
            )
# ==========================================
# Generate Customer Report
# ==========================================

def generate_reports():

    while True:

        print("\n========== REPORT MENU ==========\n")

        print("1. Customer Report")
        print("2. Transaction Report")
        print("3. System Statistics")
        print("4. Back")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            generate_customer_report()

        elif choice == "2":

            generate_transaction_report()

        elif choice == "3":

            system_statistics()

        elif choice == "4":

            break

        else:

            print("Invalid Choice.")


# ==========================================
# System Statistics
# ==========================================

def system_statistics():

    customers = get_customers()
    transactions = get_transactions()

    total_accounts = len(customers)

    active_accounts = 0
    frozen_accounts = 0
    total_balance = 0

    for customer in customers:

        total_balance += customer["balance"]

        if customer["status"] == "Active":

            active_accounts += 1

        elif customer["status"] == "Frozen":

            frozen_accounts += 1

    print("\n========== SYSTEM STATISTICS ==========\n")

    print(f"Total Customers      : {total_accounts}")
    print(f"Active Accounts      : {active_accounts}")
    print(f"Frozen Accounts      : {frozen_accounts}")
    print(f"Total Transactions   : {len(transactions)}")
    print(f"Total Bank Balance   : ₹{total_balance:.2f}")


# ==========================================
# Customer Report
# ==========================================

def customer_report():

    generate_customer_report()

    print("\nCustomer Report Generated Successfully.")


# ==========================================
# Transaction Report
# ==========================================

def transaction_report():

    generate_transaction_report()

    print("\nTransaction Report Generated Successfully.")


# ==========================================
# Backup System
# ==========================================

def database_backup():

    backup_database()

    print("\nDatabase Backup Completed.")


# ==========================================
# Restore System
# ==========================================

def database_restore():

    restore_database()

    print("\nDatabase Restored Successfully.")


# ==========================================
# Logout
# ==========================================

def admin_logout():

    print("\nAdmin Logged Out Successfully.")