# admin.py (Part 1)

from database import (
    get_admins,
    get_customers,
    save_customers,
    get_transactions
)

from report import (
    report_menu
)

from backup import (
    backup_menu
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
# View Customers
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
            "Customer",
            "Phone",
            "Balance",
            "Status"
        )
    )

    print("-" * 80)

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
            print("Customer Name  :", customer["name"])
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
        print("=" * 60)
        print("           ADMIN DASHBOARD")
        print("=" * 60)

        print("1. View Customers")
        print("2. Search Customer")
        print("3. Freeze Account")
        print("4. Unfreeze Account")
        print("5. Delete Account")
        print("6. View Transactions")
        print("7. Reports")
        print("8. Backup")
        print("9. Logout")

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

            backup_menu()

        elif choice == "9":

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

            print("\nCustomer Found")
            print("---------------------------")
            print("Name    :", customer["name"])
            print("Balance : ₹", customer["balance"])
            print("Status  :", customer["status"])

            confirm = input(
                "\nAre you sure? (Y/N): "
            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")

                return

            customers.remove(customer)

            save_customers(customers)

            print("\nCustomer Account Deleted Successfully.")

            return

    print("Customer Not Found.")


# ==========================================
# View All Transactions
# ==========================================

def view_transactions():

    transactions = get_transactions()

    if len(transactions) == 0:

        print("\nNo Transactions Found.")

        return

    print("\n========== ALL TRANSACTIONS ==========\n")

    print(
        "{:<18} {:<12} {:<12} {:>12}".format(
            "Transaction ID",
            "Account",
            "Type",
            "Amount"
        )
    )

    print("-" * 70)

    for transaction in transactions:

        print(
            "{:<18} {:<12} {:<12} ₹{:>10.2f}".format(
                transaction["transaction_id"],
                transaction["account_number"],
                transaction["type"],
                transaction["amount"]
            )
        )

        if (
            transaction["type"] == "Transfer"
            and "receiver_account" in transaction
        ):

            print(
                " " * 20 +
                f"Transferred To : {transaction['receiver_account']}"
            )

        print(
            " " * 20 +
            f"Date : {transaction['date']}"
        )

        print("-" * 70)


# ==========================================
# View Active Accounts
# ==========================================

def view_active_accounts():

    customers = get_customers()

    print("\n========== ACTIVE ACCOUNTS ==========\n")

    found = False

    for customer in customers:

        if customer["status"] == "Active":

            found = True

            print(
                customer["account_number"],
                "-",
                customer["name"]
            )

    if not found:

        print("No Active Accounts Found.")


# ==========================================
# View Frozen Accounts
# ==========================================

def view_frozen_accounts():

    customers = get_customers()

    print("\n========== FROZEN ACCOUNTS ==========\n")

    found = False

    for customer in customers:

        if customer["status"] == "Frozen":

            found = True

            print(
                customer["account_number"],
                "-",
                customer["name"]
            )

    if not found:

        print("No Frozen Accounts Found.")
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

        else:

            frozen_accounts += 1

    print("\n========== SYSTEM STATISTICS ==========\n")

    print(f"Total Customers      : {total_accounts}")
    print(f"Active Accounts      : {active_accounts}")
    print(f"Frozen Accounts      : {frozen_accounts}")
    print(f"Total Transactions   : {len(transactions)}")
    print(f"Total Bank Balance   : ₹{total_balance:.2f}")


# ==========================================
# Generate Reports
# ==========================================

def generate_reports():

    while True:

        print("\n")
        print("=" * 50)
        print("          REPORT MENU")
        print("=" * 50)

        print("1. Customer Report")
        print("2. Transaction Report")
        print("3. Loan Report")
        print("4. Fixed Deposit Report")
        print("5. Report Summary")
        print("6. Back")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            report_menu()

        elif choice == "2":

            report_menu()

        elif choice == "3":

            report_menu()

        elif choice == "4":

            report_menu()

        elif choice == "5":

            system_statistics()

        elif choice == "6":

            break

        else:

            print("Invalid Choice.")


# ==========================================
# Backup Database
# ==========================================

def create_backup():

    print("\nCreating Backup...")

    backup_menu()


# ==========================================
# Restore Database
# ==========================================

def restore_backup():

    print("\nRestore Database")

    backup_menu()


# ==========================================
# Admin Information
# ==========================================

def admin_information():

    print("\n========== ADMIN INFORMATION ==========\n")

    print("Role          : Administrator")
    print("System        : Bank Management System")
    print("Database      : JSON")
    print("Access Level  : Full Access")


# ==========================================
# Dashboard Summary
# ==========================================

def dashboard_summary():

    customers = get_customers()

    active = 0
    frozen = 0

    for customer in customers:

        if customer["status"] == "Active":

            active += 1

        else:

            frozen += 1

    print("\n========== DASHBOARD ==========\n")

    print(f"Customers       : {len(customers)}")
    print(f"Active Accounts : {active}")
    print(f"Frozen Accounts : {frozen}")


# ==========================================
# Admin Logout
# ==========================================

def admin_logout():

    print("\n================================")
    print("Admin Logged Out Successfully.")
    print("================================")