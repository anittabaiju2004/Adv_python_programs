# auth.py

from database import (
    get_customers,
    get_admins,
    save_customers
)

from utils import (
    verify_pin,
    hash_pin,
    is_valid_pin,
    find_customer
)


# ==========================================
# Verify Customer Account
# ==========================================

def verify_customer(account_number):

    customers = get_customers()

    customer = find_customer(
        customers,
        account_number
    )

    return customer


# ==========================================
# Customer Login
# ==========================================

def customer_login():

    customers = get_customers()

    print("\n========== CUSTOMER LOGIN ==========\n")

    account_number = input("Account Number : ").strip()

    customer = find_customer(customers, account_number)

    if customer is None:

        print("Account Not Found.")

        return None

    if customer["status"] != "Active":

        print("Account is Frozen.")

        return None

    pin = input("PIN : ").strip()

    if not verify_pin(pin, customer["pin"]):

        print("Incorrect PIN.")

        return None

    print("\n===================================")
    print("Login Successful")
    print("===================================")
    print(f"Welcome {customer['name']}")

    return customer


# ==========================================
# Verify Admin
# ==========================================

def verify_admin(username, password):

    admins = get_admins()

    for admin in admins:

        if (
            admin["username"] == username and
            admin["password"] == password
        ):

            return True

    return False


# ==========================================
# Admin Login
# ==========================================

def admin_login():

    print("\n========== ADMIN LOGIN ==========\n")

    username = input("Username : ").strip()

    password = input("Password : ").strip()

    if verify_admin(username, password):

        print("\n===================================")
        print("Admin Login Successful")
        print("===================================")

        return True

    print("\nInvalid Username or Password.")

    return False


# ==========================================
# Change PIN
# ==========================================

def change_customer_pin():

    customers = get_customers()

    account_number = input("Account Number : ").strip()

    customer = find_customer(customers, account_number)

    if customer is None:

        print("Account Not Found.")

        return

    old_pin = input("Current PIN : ").strip()

    if not verify_pin(old_pin, customer["pin"]):

        print("Incorrect Current PIN.")

        return

    new_pin = input("New PIN : ").strip()

    if not is_valid_pin(new_pin):

        print("PIN must contain exactly 4 digits.")

        return

    confirm_pin = input("Confirm PIN : ").strip()

    if new_pin != confirm_pin:

        print("PIN Mismatch.")

        return

    customer["pin"] = hash_pin(new_pin)

    save_customers(customers)

    print("\nPIN Changed Successfully.")


# ==========================================
# Authenticate PIN
# ==========================================

def authenticate_pin(customer):

    pin = input("Enter PIN : ").strip()

    return verify_pin(pin, customer["pin"])


# ==========================================
# Verify Account Status
# ==========================================

def verify_account_status(customer):

    if customer["status"] != "Active":

        print("Account is Frozen.")

        return False

    return True


# ==========================================
# Logout
# ==========================================

def logout():

    print("\n===================================")
    print("Logged Out Successfully")
    print("===================================")


# ==========================================
# Authentication Menu
# ==========================================

def authentication_menu():

    while True:

        print("\n")
        print("=" * 50)
        print("      AUTHENTICATION MENU")
        print("=" * 50)

        print("1. Customer Login")
        print("2. Admin Login")
        print("3. Change Customer PIN")
        print("4. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            customer_login()

        elif choice == "2":

            admin_login()

        elif choice == "3":

            change_customer_pin()

        elif choice == "4":

            print("\nReturning...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    authentication_menu()