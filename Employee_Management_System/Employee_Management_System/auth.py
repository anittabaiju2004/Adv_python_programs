# Authentication
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
# Verify Admin
# ==========================================

def verify_admin(username, password):

    admins = get_admins()

    for admin in admins:

        if (
            admin["username"] == username and
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
    print("=" * 50)
    print("          ADMIN LOGIN")
    print("=" * 50)

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

    print("\nAdmin Created Successfully.")


# ==========================================
# Change Password
# ==========================================

def change_password():

    admins = get_admins()

    print("\n========== CHANGE PASSWORD ==========\n")

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

    print("Admin Not Found.")


# ==========================================
# View Admin Accounts
# ==========================================

def view_admins():

    admins = get_admins()

    if len(admins) == 0:

        print("\nNo Admin Accounts Found.")

        return

    print("\n========== ADMIN ACCOUNTS ==========\n")

    for index, admin in enumerate(admins, start=1):

        print(f"{index}. {admin['username']}")


# ==========================================
# Delete Admin
# ==========================================

def delete_admin():

    admins = get_admins()

    username = input(
        "\nEnter Username : "
    ).strip()

    for admin in admins:

        if admin["username"] == username:

            if username == "admin":

                print(
                    "Default Admin Cannot Be Deleted."
                )

                return

            admins.remove(admin)

            save_admins(admins)

            print("\nAdmin Deleted Successfully.")

            return

    print("Admin Not Found.")


# ==========================================
# Logout
# ==========================================

def logout():

    print("\n")
    print("=" * 50)
    print("Logged Out Successfully")
    print("=" * 50)


# ==========================================
# Authentication Menu
# ==========================================

def authentication_menu():

    while True:

        print("\n")
        print("=" * 55)
        print("      AUTHENTICATION MENU")
        print("=" * 55)

        print("1. Admin Login")
        print("2. Create Admin")
        print("3. Change Password")
        print("4. Reset Password")
        print("5. View Admins")
        print("6. Delete Admin")
        print("7. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            admin_login()

        elif choice == "2":

            create_admin()

        elif choice == "3":

            change_password()

        elif choice == "4":

            reset_password()

        elif choice == "5":

            view_admins()

        elif choice == "6":

            delete_admin()

        elif choice == "7":

            logout()

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    authentication_menu()