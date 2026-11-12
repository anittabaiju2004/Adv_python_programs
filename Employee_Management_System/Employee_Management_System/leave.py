# Leave management
# leave.py (Part 1)

from datetime import datetime

from database import (
    get_employees,
    save_employees
)


# ==========================================
# Apply Leave
# ==========================================

def apply_leave():

    employees = get_employees()

    print("\n========== APPLY LEAVE ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            try:

                days = int(
                    input("Number of Leave Days : ")
                )

            except ValueError:

                print("Invalid Number.")

                return

            if days <= 0:

                print("Leave Days Must Be Greater Than Zero.")

                return

            if days > employee["remaining_leave"]:

                print("Insufficient Leave Balance.")

                return

            reason = input("Reason : ").strip()

            leave = {

                "date": datetime.now().strftime("%Y-%m-%d"),

                "days": days,

                "reason": reason,

                "status": "Pending"

            }

            leaves = employee.get("leave_history", [])

            leaves.append(leave)

            employee["leave_history"] = leaves

            save_employees(employees)

            print("\nLeave Request Submitted Successfully.")

            return

    print("Employee Not Found.")


# ==========================================
# View Leave Requests
# ==========================================

def view_leave_requests():

    employees = get_employees()

    print("\n========== LEAVE REQUESTS ==========\n")

    found = False

    for employee in employees:

        for leave in employee.get("leave_history", []):

            found = True

            print("-" * 50)

            print("Employee ID :", employee["employee_id"])
            print("Name        :", employee["name"])
            print("Date        :", leave["date"])
            print("Days        :", leave["days"])
            print("Reason      :", leave["reason"])
            print("Status      :", leave["status"])

    if not found:

        print("No Leave Requests Found.")


# ==========================================
# Search Leave
# ==========================================

def search_leave():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            leaves = employee.get("leave_history", [])

            if len(leaves) == 0:

                print("\nNo Leave Records Found.")

                return

            print("\n========== LEAVE DETAILS ==========\n")

            for leave in leaves:

                print("-" * 50)

                print("Date   :", leave["date"])
                print("Days   :", leave["days"])
                print("Reason :", leave["reason"])
                print("Status :", leave["status"])

            return

    print("Employee Not Found.")


# ==========================================
# Leave History
# ==========================================

def leave_history():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n")
            print("=" * 60)
            print("           LEAVE HISTORY")
            print("=" * 60)

            history = employee.get(
                "leave_history",
                []
            )

            if len(history) == 0:

                print("No Leave History Available.")

                return

            for leave in history:

                print(
                    f"{leave['date']} | "
                    f"{leave['days']} Day(s) | "
                    f"{leave['status']}"
                )

            return

    print("Employee Not Found.")
# ==========================================
# Approve Leave
# ==========================================

def approve_leave():

    employees = get_employees()

    print("\n========== APPROVE LEAVE ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            leaves = employee.get("leave_history", [])

            pending = [

                leave

                for leave in leaves

                if leave["status"] == "Pending"

            ]

            if len(pending) == 0:

                print("No Pending Leave Requests.")

                return

            for index, leave in enumerate(pending, start=1):

                print(f"\nRequest {index}")

                print("Date   :", leave["date"])
                print("Days   :", leave["days"])
                print("Reason :", leave["reason"])

            try:

                choice = int(
                    input("\nSelect Request : ")
                )

                leave = pending[choice - 1]

            except (ValueError, IndexError):

                print("Invalid Selection.")

                return

            leave["status"] = "Approved"

            employee["leave_days"] += leave["days"]

            employee["remaining_leave"] -= leave["days"]

            save_employees(employees)

            print("\nLeave Approved Successfully.")

            return

    print("Employee Not Found.")


# ==========================================
# Reject Leave
# ==========================================

def reject_leave():

    employees = get_employees()

    print("\n========== REJECT LEAVE ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            leaves = employee.get("leave_history", [])

            pending = [

                leave

                for leave in leaves

                if leave["status"] == "Pending"

            ]

            if len(pending) == 0:

                print("No Pending Leave Requests.")

                return

            for index, leave in enumerate(pending, start=1):

                print(f"\nRequest {index}")

                print("Date   :", leave["date"])
                print("Days   :", leave["days"])
                print("Reason :", leave["reason"])

            try:

                choice = int(
                    input("\nSelect Request : ")
                )

                leave = pending[choice - 1]

            except (ValueError, IndexError):

                print("Invalid Selection.")

                return

            leave["status"] = "Rejected"

            save_employees(employees)

            print("\nLeave Rejected Successfully.")

            return

    print("Employee Not Found.")


# ==========================================
# Leave Balance
# ==========================================

def leave_balance():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n========== LEAVE BALANCE ==========\n")

            print("Employee        :", employee["name"])

            print(
                "Leaves Taken    :",
                employee["leave_days"]
            )

            print(
                "Remaining Leave :",
                employee["remaining_leave"]
            )

            return

    print("Employee Not Found.")


# ==========================================
# Pending Leave Requests
# ==========================================

def pending_leaves():

    employees = get_employees()

    print("\n========== PENDING LEAVE REQUESTS ==========\n")

    found = False

    for employee in employees:

        for leave in employee.get("leave_history", []):

            if leave["status"] == "Pending":

                found = True

                print("-" * 50)

                print("Employee :", employee["name"])

                print("Date     :", leave["date"])

                print("Days     :", leave["days"])

                print("Reason   :", leave["reason"])

    if not found:

        print("No Pending Leave Requests.")


# ==========================================
# Approved Leave Report
# ==========================================

def approved_leaves():

    employees = get_employees()

    print("\n========== APPROVED LEAVES ==========\n")

    found = False

    for employee in employees:

        for leave in employee.get("leave_history", []):

            if leave["status"] == "Approved":

                found = True

                print("-" * 50)

                print("Employee :", employee["name"])

                print("Date     :", leave["date"])

                print("Days     :", leave["days"])

    if not found:

        print("No Approved Leave Records.")


# ==========================================
# Rejected Leave Report
# ==========================================

def rejected_leaves():

    employees = get_employees()

    print("\n========== REJECTED LEAVES ==========\n")

    found = False

    for employee in employees:

        for leave in employee.get("leave_history", []):

            if leave["status"] == "Rejected":

                found = True

                print("-" * 50)

                print("Employee :", employee["name"])

                print("Date     :", leave["date"])

                print("Days     :", leave["days"])

    if not found:

        print("No Rejected Leave Records.")
import csv
import os

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Leave Statistics
# ==========================================

def leave_statistics():

    employees = get_employees()

    total_requests = 0
    approved = 0
    rejected = 0
    pending = 0

    for employee in employees:

        for leave in employee.get("leave_history", []):

            total_requests += 1

            if leave["status"] == "Approved":

                approved += 1

            elif leave["status"] == "Rejected":

                rejected += 1

            else:

                pending += 1

    print("\n")
    print("=" * 60)
    print("          LEAVE STATISTICS")
    print("=" * 60)

    print("Total Requests :", total_requests)
    print("Approved       :", approved)
    print("Rejected       :", rejected)
    print("Pending        :", pending)


# ==========================================
# Monthly Leave Report
# ==========================================

def monthly_leave_report():

    employees = get_employees()

    month = input(
        "\nEnter Month (YYYY-MM): "
    ).strip()

    print("\n========== MONTHLY LEAVE REPORT ==========\n")

    found = False

    for employee in employees:

        for leave in employee.get("leave_history", []):

            if leave["date"].startswith(month):

                found = True

                print("-" * 50)

                print("Employee :", employee["name"])
                print("Date     :", leave["date"])
                print("Days     :", leave["days"])
                print("Status   :", leave["status"])

    if not found:

        print("No Leave Records Found.")


# ==========================================
# Employee Leave Summary
# ==========================================

def employee_leave_summary():

    employees = get_employees()

    print("\n========== EMPLOYEE LEAVE SUMMARY ==========\n")

    for employee in employees:

        print("-" * 50)

        print("Employee :", employee["name"])

        print("Leave Taken :", employee["leave_days"])

        print(
            "Remaining Leave :",
            employee["remaining_leave"]
        )


# ==========================================
# Export Leave Report
# ==========================================

def export_leave_report():

    employees = get_employees()

    filename = os.path.join(

        REPORT_FOLDER,

        "Leave_Report.csv"

    )

    with open(

        filename,

        "w",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Employee ID",

            "Employee Name",

            "Leave Taken",

            "Remaining Leave"

        ])

        for employee in employees:

            writer.writerow([

                employee["employee_id"],

                employee["name"],

                employee["leave_days"],

                employee["remaining_leave"]

            ])

    print("\nLeave Report Exported Successfully.")
    print("Saved To :", filename)


# ==========================================
# Leave Dashboard
# ==========================================

def leave_dashboard():

    employees = get_employees()

    total_leave = sum(

        employee["leave_days"]

        for employee in employees

    )

    total_remaining = sum(

        employee["remaining_leave"]

        for employee in employees

    )

    print("\n")
    print("=" * 60)
    print("          LEAVE DASHBOARD")
    print("=" * 60)

    print("Total Employees :", len(employees))
    print("Total Leave Used :", total_leave)
    print("Remaining Leave :", total_remaining)


# ==========================================
# Leave Menu
# ==========================================

def leave_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("          LEAVE MANAGEMENT")
        print("=" * 60)

        print("1. Apply Leave")
        print("2. View Leave Requests")
        print("3. Search Leave")
        print("4. Leave History")
        print("5. Approve Leave")
        print("6. Reject Leave")
        print("7. Leave Balance")
        print("8. Pending Leave Requests")
        print("9. Approved Leaves")
        print("10. Rejected Leaves")
        print("11. Leave Statistics")
        print("12. Monthly Leave Report")
        print("13. Employee Leave Summary")
        print("14. Export Leave Report")
        print("15. Leave Dashboard")
        print("16. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            apply_leave()

        elif choice == "2":

            view_leave_requests()

        elif choice == "3":

            search_leave()

        elif choice == "4":

            leave_history()

        elif choice == "5":

            approve_leave()

        elif choice == "6":

            reject_leave()

        elif choice == "7":

            leave_balance()

        elif choice == "8":

            pending_leaves()

        elif choice == "9":

            approved_leaves()

        elif choice == "10":

            rejected_leaves()

        elif choice == "11":

            leave_statistics()

        elif choice == "12":

            monthly_leave_report()

        elif choice == "13":

            employee_leave_summary()

        elif choice == "14":

            export_leave_report()

        elif choice == "15":

            leave_dashboard()

        elif choice == "16":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    leave_menu()