# Authentication
# auth.py (Part 1)

from database import (
    get_admins,
    save_admins
)

from utils import (
    hash_password,
    verify_password,
    is_valid_password
)


# ==========================================
# Verify Admin
# ==========================================

def verify_admin(username, password):

    admins = get_admins()

    for admin in admins:

        if (

            admin["username"] == username

            and

            verify_password(

                password,

                admin["password"]

            )

        ):

            return True

    return False


# ==========================================
# Admin Login
# ==========================================

def admin_login():

    print("\n")
    print("=" * 60)
    print("            ADMIN LOGIN")
    print("=" * 60)

    username = input("Username : ").strip()

    password = input("Password : ").strip()

    if verify_admin(username, password):

        print("\nLogin Successful.")

        return True

    print("\nInvalid Username or Password.")

    return False


# ==========================================
# Create Admin
# ==========================================

def create_admin():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("          CREATE ADMIN")
    print("=" * 60)

    username = input("Username : ").strip()

    for admin in admins:

        if admin["username"] == username:

            print("Username Already Exists.")

            return

    password = input("Password : ").strip()

    if not is_valid_password(password):

        print(

            "Password must contain at least "

            "6 characters."

        )

        return

    admins.append({

        "username": username,

        "password": hash_password(password)

    })

    save_admins(admins)

    print("\nAdmin Account Created Successfully.")


# ==========================================
# Admin Exists
# ==========================================

def admin_exists(username):

    admins = get_admins()

    for admin in admins:

        if admin["username"] == username:

            return True

    return False


# ==========================================
# Display Admin Accounts
# ==========================================

def display_admins():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("         ADMIN ACCOUNTS")
    print("=" * 60)

    if len(admins) == 0:

        print("No Admin Accounts Found.")

        return

    for index, admin in enumerate(admins, start=1):

        print(

            f"{index}. {admin['username']}"

        )
# ==========================================
# Change Password
# ==========================================

def change_password():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("          CHANGE PASSWORD")
    print("=" * 60)

    username = input("Username : ").strip()

    old_password = input(
        "Current Password : "
    ).strip()

    for admin in admins:

        if admin["username"] == username:

            if not verify_password(

                old_password,

                admin["password"]

            ):

                print("Incorrect Current Password.")

                return

            new_password = input(
                "New Password : "
            ).strip()

            if not is_valid_password(new_password):

                print(
                    "Password must contain at least "
                    "6 characters."
                )

                return

            confirm = input(
                "Confirm Password : "
            ).strip()

            if new_password != confirm:

                print("Password Mismatch.")

                return

            admin["password"] = hash_password(
                new_password
            )

            save_admins(admins)

            print("\nPassword Changed Successfully.")

            return

    print("Admin Not Found.")


# ==========================================
# Reset Password
# ==========================================

def reset_password():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("           RESET PASSWORD")
    print("=" * 60)

    username = input("Username : ").strip()

    for admin in admins:

        if admin["username"] == username:

            new_password = input(
                "New Password : "
            ).strip()

            if not is_valid_password(new_password):

                print(
                    "Password must contain at least "
                    "6 characters."
                )

                return

            admin["password"] = hash_password(
                new_password
            )

            save_admins(admins)

            print("\nPassword Reset Successfully.")

            return

    print("Admin Not Found.")


# ==========================================
# Delete Admin Account
# ==========================================

def delete_admin():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("          DELETE ADMIN")
    print("=" * 60)

    username = input("Username : ").strip()

    for admin in admins:

        if admin["username"] == username:

            if username.lower() == "admin":

                print(
                    "Default Admin Account "
                    "Cannot Be Deleted."
                )

                return

            confirm = input(
                "Delete this Admin? (Y/N): "
            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")

                return

            admins.remove(admin)

            save_admins(admins)

            print("\nAdmin Deleted Successfully.")

            return

    print("Admin Not Found.")


# ==========================================
# View Admin Details
# ==========================================

def view_admin_details():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("         ADMIN DETAILS")
    print("=" * 60)

    if len(admins) == 0:

        print("No Admin Accounts Found.")

        return

    for index, admin in enumerate(admins, start=1):

        print("-" * 40)

        print(f"Admin {index}")

        print("Username :", admin["username"])

        print(
            "Password : ********"
        )


# ==========================================
# Total Admin Accounts
# ==========================================

def total_admins():

    admins = get_admins()

    print("\nTotal Admin Accounts :", len(admins))


# ==========================================
# Authentication Statistics
# ==========================================

def authentication_statistics():

    admins = get_admins()

    print("\n")
    print("=" * 60)
    print("     AUTHENTICATION STATISTICS")
    print("=" * 60)

    print("Total Admin Accounts :", len(admins))

    if admins:

        print(
            "Default Admin Available : Yes"
        )

    else:

        print(
            "Default Admin Available : No"
        )
# ==========================================
# Imports
# ==========================================

import json
import os
from datetime import datetime


# ==========================================
# Login History File
# ==========================================

LOGIN_HISTORY_FILE = "data/login_history.json"

os.makedirs("data", exist_ok=True)


# ==========================================
# Initialize Login History
# ==========================================

def initialize_login_history():

    if not os.path.exists(LOGIN_HISTORY_FILE):

        with open(

            LOGIN_HISTORY_FILE,

            "w",

            encoding="utf-8"

        ) as file:

            json.dump([], file, indent=4)


# ==========================================
# Save Login History
# ==========================================

def save_login_history(username):

    initialize_login_history()

    with open(

        LOGIN_HISTORY_FILE,

        "r",

        encoding="utf-8"

    ) as file:

        history = json.load(file)

    history.append({

        "username": username,

        "login_time": datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        )

    })

    with open(

        LOGIN_HISTORY_FILE,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(history, file, indent=4)


# ==========================================
# View Login History
# ==========================================

def view_login_history():

    initialize_login_history()

    with open(

        LOGIN_HISTORY_FILE,

        "r",

        encoding="utf-8"

    ) as file:

        history = json.load(file)

    print("\n")
    print("=" * 60)
    print("           LOGIN HISTORY")
    print("=" * 60)

    if len(history) == 0:

        print("No Login History Available.")

        return

    for record in history:

        print("-" * 50)

        print("Username :", record["username"])

        print("Login At :", record["login_time"])


# ==========================================
# Default Admin Initialization
# ==========================================

def initialize_default_admin():

    admins = get_admins()

    if len(admins) == 0:

        admins.append({

            "username": "admin",

            "password": hash_password("admin123")

        })

        save_admins(admins)


# ==========================================
# Logout
# ==========================================

def logout():

    print("\n")
    print("=" * 60)
    print("     LOGGED OUT SUCCESSFULLY")
    print("=" * 60)


# ==========================================
# Authentication Dashboard
# ==========================================

def authentication_dashboard():

    initialize_default_admin()

    while True:

        print("\n")
        print("=" * 60)
        print("      AUTHENTICATION PANEL")
        print("=" * 60)

        print("1. Admin Login")
        print("2. Create Admin")
        print("3. Change Password")
        print("4. Reset Password")
        print("5. View Admin Accounts")
        print("6. View Admin Details")
        print("7. Delete Admin")
        print("8. Login History")
        print("9. Authentication Statistics")
        print("10. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            print("\nLogin")

            username = input("Username : ")

            password = input("Password : ")

            if verify_admin(username, password):

                save_login_history(username)

                print("\nLogin Successful.")

            else:

                print("\nInvalid Credentials.")

        elif choice == "2":

            create_admin()

        elif choice == "3":

            change_password()

        elif choice == "4":

            reset_password()

        elif choice == "5":

            display_admins()

        elif choice == "6":

            view_admin_details()

        elif choice == "7":

            delete_admin()

        elif choice == "8":

            view_login_history()

        elif choice == "9":

            authentication_statistics()

        elif choice == "10":

            logout()

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    authentication_dashboard()