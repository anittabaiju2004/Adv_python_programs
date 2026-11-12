# Authentication module
# auth.py

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
# Verify Admin Credentials
# ==========================================

def verify_admin(username, password):

    admins = get_admins()

    for admin in admins:

        if (
            admin["username"] == username and
            verify_password(password, admin["password"])
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
# Change Admin Password
# ==========================================

def change_admin_password():

    admins = get_admins()

    print("\n========== CHANGE PASSWORD ==========\n")

    username = input("Username : ").strip()

    old_password = input("Current Password : ").strip()

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

    print("Admin Account Not Found.")


# ==========================================
# Create Admin Account
# ==========================================

def create_admin():

    admins = get_admins()

    print("\n========== CREATE ADMIN ==========\n")

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

    admin = {

        "username": username,
        "password": hash_password(password)

    }

    admins.append(admin)

    save_admins(admins)

    print("\nAdmin Account Created Successfully.")


# ==========================================
# Forgot Password (Reset)
# ==========================================

def reset_password():

    admins = get_admins()

    print("\n========== RESET PASSWORD ==========\n")

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

    print("Admin Account Not Found.")


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

        print("1. Admin Login")
        print("2. Create Admin")
        print("3. Change Password")
        print("4. Reset Password")
        print("5. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            admin_login()

        elif choice == "2":

            create_admin()

        elif choice == "3":

            change_admin_password()

        elif choice == "4":

            reset_password()

        elif choice == "5":

            logout()

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    authentication_menu()