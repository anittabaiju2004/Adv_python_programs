# Authentication
# auth.py

import hashlib

from database import (
    get_users,
    save_users
)


# ==========================================
# Hash Password
# ==========================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ==========================================
# Register User
# ==========================================

def register_user():

    users = get_users()

    print("\n========== USER REGISTRATION ==========")

    user_id = input("Enter User ID : ").strip()

    for user in users:
        if user["user_id"] == user_id:
            print("User ID already exists.")
            return

    name = input("Enter Name : ").strip()
    email = input("Enter Email : ").strip()
    phone = input("Enter Phone : ").strip()
    password = input("Create Password : ").strip()

    users.append({
        "user_id": user_id,
        "name": name,
        "email": email,
        "phone": phone,
        "password": hash_password(password)
    })

    save_users(users)

    print("\nRegistration Successful.")


# ==========================================
# Login
# ==========================================

def login():

    users = get_users()

    print("\n========== USER LOGIN ==========")

    user_id = input("Enter User ID : ").strip()
    password = input("Enter Password : ").strip()

    password = hash_password(password)

    for user in users:

        if user["user_id"] == user_id and user["password"] == password:

            print(f"\nWelcome {user['name']}")

            return user

    print("Invalid User ID or Password.")

    return None


# ==========================================
# Change Password
# ==========================================

def change_password():

    users = get_users()

    user_id = input("Enter User ID : ")

    old_password = hash_password(
        input("Enter Current Password : ")
    )

    for user in users:

        if user["user_id"] == user_id:

            if user["password"] != old_password:
                print("Incorrect Password.")
                return

            new_password = input("Enter New Password : ")

            confirm = input("Confirm Password : ")

            if new_password != confirm:
                print("Passwords do not match.")
                return

            user["password"] = hash_password(new_password)

            save_users(users)

            print("\nPassword Changed Successfully.")

            return

    print("User Not Found.")


# ==========================================
# Forgot Password
# ==========================================

def forgot_password():

    users = get_users()

    email = input("Enter Registered Email : ")

    for user in users:

        if user["email"] == email:

            new_password = input("Enter New Password : ")

            user["password"] = hash_password(new_password)

            save_users(users)

            print("\nPassword Reset Successfully.")

            return

    print("Email Not Found.")


# ==========================================
# Logout
# ==========================================

def logout():

    print("\nLogged Out Successfully.")


# ==========================================
# Authentication Menu
# ==========================================

def auth_menu():

    while True:

        print("\n==============================")
        print("      AUTHENTICATION")
        print("==============================")

        print("1. Register")
        print("2. Login")
        print("3. Change Password")
        print("4. Forgot Password")
        print("5. Exit")

        choice = input("Enter Choice : ")

        if choice == "1":
            register_user()

        elif choice == "2":
            user = login()

            if user:
                return user

        elif choice == "3":
            change_password()

        elif choice == "4":
            forgot_password()

        elif choice == "5":
            break

        else:
            print("Invalid Choice.")