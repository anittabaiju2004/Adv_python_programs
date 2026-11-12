# Savings module
# savings.py

from database import (
    get_savings,
    save_savings
)

from datetime import datetime


# ==========================================
# Generate Savings ID
# ==========================================

def generate_savings_id():

    savings = get_savings()

    if not savings:
        return "SAV1001"

    last_id = int(savings[-1]["savings_id"][3:])

    return f"SAV{last_id+1}"


# ==========================================
# Set Savings Goal
# ==========================================

def set_savings_goal():

    savings = get_savings()

    print("\n========== SET SAVINGS GOAL ==========")

    goal_name = input("Goal Name : ")

    try:
        target = float(input("Target Amount : ₹"))
    except ValueError:
        print("Invalid Amount.")
        return

    goal = {

        "savings_id": generate_savings_id(),
        "goal_name": goal_name,
        "target_amount": target,
        "saved_amount": 0,
        "created_date": datetime.now().strftime("%Y-%m-%d")

    }

    savings.append(goal)

    save_savings(savings)

    print("\nSavings Goal Created Successfully.")


# ==========================================
# Add Savings
# ==========================================

def add_savings():

    savings = get_savings()

    savings_id = input("Savings ID : ")

    for goal in savings:

        if goal["savings_id"] == savings_id:

            try:
                amount = float(input("Amount to Save : ₹"))
            except ValueError:
                print("Invalid Amount.")
                return

            goal["saved_amount"] += amount

            save_savings(savings)

            print("\nSavings Updated Successfully.")

            return

    print("Savings Goal Not Found.")


# ==========================================
# Withdraw Savings
# ==========================================

def withdraw_savings():

    savings = get_savings()

    savings_id = input("Savings ID : ")

    for goal in savings:

        if goal["savings_id"] == savings_id:

            try:
                amount = float(input("Withdraw Amount : ₹"))
            except ValueError:
                print("Invalid Amount.")
                return

            if amount > goal["saved_amount"]:

                print("Insufficient Savings.")

                return

            goal["saved_amount"] -= amount

            save_savings(savings)

            print("\nWithdrawal Successful.")

            return

    print("Savings Goal Not Found.")


# ==========================================
# View Savings
# ==========================================

def view_savings():

    savings = get_savings()

    if not savings:

        print("\nNo Savings Goals Found.")

        return

    print("\n========== SAVINGS ==========")

    for goal in savings:

        print("-"*50)

        print("Savings ID   :", goal["savings_id"])
        print("Goal         :", goal["goal_name"])
        print("Target       : ₹", goal["target_amount"])
        print("Saved        : ₹", goal["saved_amount"])
        print("Created Date :", goal["created_date"])


# ==========================================
# Savings Progress
# ==========================================

def savings_progress():

    savings = get_savings()

    savings_id = input("Savings ID : ")

    for goal in savings:

        if goal["savings_id"] == savings_id:

            percentage = (
                goal["saved_amount"] /
                goal["target_amount"]
            ) * 100

            print("\n========== PROGRESS ==========")

            print("Goal       :", goal["goal_name"])
            print("Target     : ₹", goal["target_amount"])
            print("Saved      : ₹", goal["saved_amount"])
            print(f"Progress   : {percentage:.2f}%")

            return

    print("Savings Goal Not Found.")


# ==========================================
# Savings Summary
# ==========================================

def savings_summary():

    savings = get_savings()

    total_target = sum(
        goal["target_amount"]
        for goal in savings
    )

    total_saved = sum(
        goal["saved_amount"]
        for goal in savings
    )

    print("\n========== SUMMARY ==========")

    print("Goals         :", len(savings))
    print("Target Amount : ₹", total_target)
    print("Saved Amount  : ₹", total_saved)


# ==========================================
# Delete Savings Goal
# ==========================================

def delete_goal():

    savings = get_savings()

    savings_id = input("Savings ID : ")

    for goal in savings:

        if goal["savings_id"] == savings_id:

            savings.remove(goal)

            save_savings(savings)

            print("\nSavings Goal Deleted.")

            return

    print("Goal Not Found.")


# ==========================================
# Savings Menu
# ==========================================

def savings_menu():

    while True:

        print("\n==============================")
        print("      SAVINGS MANAGEMENT")
        print("==============================")

        print("1. Set Savings Goal")
        print("2. Add Savings")
        print("3. Withdraw Savings")
        print("4. View Savings")
        print("5. Savings Progress")
        print("6. Savings Summary")
        print("7. Delete Savings Goal")
        print("8. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            set_savings_goal()

        elif choice == "2":
            add_savings()

        elif choice == "3":
            withdraw_savings()

        elif choice == "4":
            view_savings()

        elif choice == "5":
            savings_progress()

        elif choice == "6":
            savings_summary()

        elif choice == "7":
            delete_goal()

        elif choice == "8":
            break

        else:
            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    savings_menu()