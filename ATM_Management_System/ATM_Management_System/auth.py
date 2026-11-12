# Authentication
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
# Verify Customer
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

    account_number = input("Account Number : ")

    customer = find_customer(
        customers,
        account_number
    )

    if customer is None:

        print("Account Not Found.")

        return None

    if customer["status"] != "Active":

        print("Account is Frozen.")

        return None

    pin = input("PIN : ")

    if not verify_pin(pin, customer["pin"]):

        print("Incorrect PIN.")

        return None

    print("\nLogin Successful.")

    print(f"Welcome {customer['name']}")

    return customer


# ==========================================
# Verify Admin
# ==========================================

def verify_admin(username, password):

    admins = get_admins()

    for admin in admins:

        if (
            admin["username"] == username
            and admin["password"] == password
        ):

            return True

    return False


# ==========================================
# Admin Login
# ==========================================

def admin_login():

    print("\n========== ADMIN LOGIN ==========\n")

    username = input("Username : ")

    password = input("Password : ")

    if verify_admin(username, password):

        print("\nAdmin Login Successful.")

        return True

    print("Invalid Username or Password.")

    return False


# ==========================================
# Change Customer PIN
# ==========================================

def change_pin():

    customers = get_customers()

    account_number = input("Account Number : ")

    customer = find_customer(
        customers,
        account_number
    )

    if customer is None:

        print("Account Not Found.")

        return

    old_pin = input("Current PIN : ")

    if not verify_pin(old_pin, customer["pin"]):

        print("Incorrect PIN.")

        return

    new_pin = input("New PIN : ")

    if not is_valid_pin(new_pin):

        print("PIN must contain exactly 4 digits.")

        return

    confirm_pin = input("Confirm PIN : ")

    if new_pin != confirm_pin:

        print("PIN Mismatch.")

        return

    customer["pin"] = hash_pin(new_pin)

    save_customers(customers)

    print("\nPIN Changed Successfully.")


# ==========================================
# Verify PIN
# ==========================================

def authenticate_pin(customer):

    pin = input("Enter PIN : ")

    return verify_pin(pin, customer["pin"])


# ==========================================
# Logout
# ==========================================

def logout():

    print("\nLogged Out Successfully.")