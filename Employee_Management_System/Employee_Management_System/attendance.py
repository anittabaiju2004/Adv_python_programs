# Attendance module
# attendance.py (Part 1)

from datetime import datetime

from database import (
    get_employees,
    save_employees
)


# ==========================================
# Mark Attendance
# ==========================================

def mark_attendance():

    employees = get_employees()

    print("\n========== MARK ATTENDANCE ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            date = datetime.now().strftime("%Y-%m-%d")

            status = input(
                "Attendance (Present/Absent): "
            ).strip().capitalize()

            if status not in ["Present", "Absent"]:

                print("Invalid Attendance Status.")

                return

            attendance = employee.get(
                "attendance",
                []
            )

            for record in attendance:

                if record["date"] == date:

                    print(
                        "Attendance Already Marked Today."
                    )

                    return

            attendance.append({

                "date": date,
                "status": status

            })

            employee["attendance"] = attendance

            employee["present_days"] = len([

                record

                for record in attendance

                if record["status"] == "Present"

            ])

            employee["absent_days"] = len([

                record

                for record in attendance

                if record["status"] == "Absent"

            ])

            save_employees(employees)

            print("\nAttendance Marked Successfully.")

            return

    print("Employee Not Found.")


# ==========================================
# View Today's Attendance
# ==========================================

def today_attendance():

    employees = get_employees()

    today = datetime.now().strftime("%Y-%m-%d")

    print("\n========== TODAY'S ATTENDANCE ==========\n")

    found = False

    for employee in employees:

        for record in employee.get("attendance", []):

            if record["date"] == today:

                found = True

                print("-" * 50)

                print("Employee :", employee["name"])

                print("Status   :", record["status"])

    if not found:

        print("No Attendance Records Found.")


# ==========================================
# Search Attendance
# ==========================================

def search_attendance():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n========== ATTENDANCE ==========\n")

            attendance = employee.get(
                "attendance",
                []
            )

            if len(attendance) == 0:

                print("No Attendance Records.")

                return

            for record in attendance:

                print("-" * 40)

                print("Date   :", record["date"])

                print("Status :", record["status"])

            return

    print("Employee Not Found.")


# ==========================================
# Attendance History
# ==========================================

def attendance_history():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n")
            print("=" * 50)
            print("      ATTENDANCE HISTORY")
            print("=" * 50)

            attendance = employee.get(
                "attendance",
                []
            )

            if len(attendance) == 0:

                print("No Attendance Records.")

                return

            for record in attendance:

                print(
                    f"{record['date']} : "
                    f"{record['status']}"
                )

            return

    print("Employee Not Found.")
# ==========================================
# Monthly Attendance
# ==========================================

def monthly_attendance():

    employees = get_employees()

    month = input(
        "\nEnter Month (YYYY-MM): "
    ).strip()

    print("\n========== MONTHLY ATTENDANCE ==========\n")

    found = False

    for employee in employees:

        attendance = employee.get("attendance", [])

        monthly_records = [

            record

            for record in attendance

            if record["date"].startswith(month)

        ]

        if monthly_records:

            found = True

            present = len([

                record

                for record in monthly_records

                if record["status"] == "Present"

            ])

            absent = len(monthly_records) - present

            print("-" * 50)
            print("Employee :", employee["name"])
            print("Present  :", present)
            print("Absent   :", absent)

    if not found:

        print("No Attendance Records Found.")


# ==========================================
# Attendance Statistics
# ==========================================

def attendance_statistics():

    employees = get_employees()

    print("\n========== ATTENDANCE STATISTICS ==========\n")

    total_present = 0
    total_absent = 0

    for employee in employees:

        attendance = employee.get("attendance", [])

        total_present += len([

            record

            for record in attendance

            if record["status"] == "Present"

        ])

        total_absent += len([

            record

            for record in attendance

            if record["status"] == "Absent"

        ])

    print("Total Employees :", len(employees))
    print("Present Days    :", total_present)
    print("Absent Days     :", total_absent)


# ==========================================
# Present Employees
# ==========================================

def present_employees():

    employees = get_employees()

    today = datetime.now().strftime("%Y-%m-%d")

    print("\n========== PRESENT EMPLOYEES ==========\n")

    found = False

    for employee in employees:

        for record in employee.get("attendance", []):

            if (

                record["date"] == today and

                record["status"] == "Present"

            ):

                found = True

                print("-" * 40)

                print("Employee ID :", employee["employee_id"])
                print("Name        :", employee["name"])
                print("Department  :", employee["department"])

    if not found:

        print("No Present Employees.")


# ==========================================
# Absent Employees
# ==========================================

def absent_employees():

    employees = get_employees()

    today = datetime.now().strftime("%Y-%m-%d")

    print("\n========== ABSENT EMPLOYEES ==========\n")

    found = False

    for employee in employees:

        for record in employee.get("attendance", []):

            if (

                record["date"] == today and

                record["status"] == "Absent"

            ):

                found = True

                print("-" * 40)

                print("Employee ID :", employee["employee_id"])
                print("Name        :", employee["name"])
                print("Department  :", employee["department"])

    if not found:

        print("No Absent Employees.")


# ==========================================
# Attendance Percentage
# ==========================================

def attendance_percentage():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            attendance = employee.get("attendance", [])

            if len(attendance) == 0:

                print("No Attendance Records.")

                return

            present = len([

                record

                for record in attendance

                if record["status"] == "Present"

            ])

            percentage = (

                present / len(attendance)

            ) * 100

            print("\n========== ATTENDANCE PERCENTAGE ==========\n")

            print("Employee :", employee["name"])
            print("Present  :", present)
            print("Total    :", len(attendance))
            print(
                "Percentage : {:.2f}%".format(
                    percentage
                )
            )

            return

    print("Employee Not Found.")
import csv
import os

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Attendance Report
# ==========================================

def attendance_report():

    employees = get_employees()

    print("\n========== ATTENDANCE REPORT ==========\n")

    for employee in employees:

        attendance = employee.get("attendance", [])

        present = len([
            record
            for record in attendance
            if record["status"] == "Present"
        ])

        absent = len([
            record
            for record in attendance
            if record["status"] == "Absent"
        ])

        print("-" * 50)
        print("Employee ID :", employee["employee_id"])
        print("Name        :", employee["name"])
        print("Present     :", present)
        print("Absent      :", absent)


# ==========================================
# Export Attendance Report
# ==========================================

def export_attendance_report():

    employees = get_employees()

    filename = os.path.join(
        REPORT_FOLDER,
        "Attendance_Report.csv"
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
            "Present Days",
            "Absent Days",
            "Attendance %"
        ])

        for employee in employees:

            attendance = employee.get("attendance", [])

            present = len([
                record
                for record in attendance
                if record["status"] == "Present"
            ])

            absent = len(attendance) - present

            percentage = 0

            if len(attendance):

                percentage = (
                    present /
                    len(attendance)
                ) * 100

            writer.writerow([
                employee["employee_id"],
                employee["name"],
                present,
                absent,
                round(percentage, 2)
            ])

    print("\nAttendance Report Exported Successfully.")
    print("Saved To :", filename)


# ==========================================
# Best Attendance Employee
# ==========================================

def best_attendance_employee():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    best_employee = None
    best_percentage = 0

    for employee in employees:

        attendance = employee.get("attendance", [])

        if len(attendance) == 0:

            continue

        present = len([
            record
            for record in attendance
            if record["status"] == "Present"
        ])

        percentage = (
            present /
            len(attendance)
        ) * 100

        if percentage > best_percentage:

            best_percentage = percentage
            best_employee = employee

    if best_employee:

        print("\n========== BEST ATTENDANCE ==========\n")

        print("Employee ID :", best_employee["employee_id"])
        print("Name        :", best_employee["name"])
        print("Department  :", best_employee["department"])
        print("Attendance  : {:.2f}%".format(best_percentage))

    else:

        print("No Attendance Data Available.")


# ==========================================
# Daily Attendance Report
# ==========================================

def daily_attendance_report():

    date = input(
        "\nEnter Date (YYYY-MM-DD): "
    ).strip()

    employees = get_employees()

    print("\n========== DAILY ATTENDANCE ==========\n")

    found = False

    for employee in employees:

        for record in employee.get("attendance", []):

            if record["date"] == date:

                found = True

                print("-" * 50)

                print("Employee :", employee["name"])
                print("Status   :", record["status"])

    if not found:

        print("No Attendance Records Found.")


# ==========================================
# Attendance Dashboard
# ==========================================

def attendance_dashboard():

    employees = get_employees()

    total = len(employees)

    total_present = 0
    total_absent = 0

    for employee in employees:

        attendance = employee.get("attendance", [])

        total_present += len([
            record
            for record in attendance
            if record["status"] == "Present"
        ])

        total_absent += len([
            record
            for record in attendance
            if record["status"] == "Absent"
        ])

    print("\n")
    print("=" * 60)
    print("        ATTENDANCE DASHBOARD")
    print("=" * 60)

    print("Total Employees :", total)
    print("Present Days    :", total_present)
    print("Absent Days     :", total_absent)


# ==========================================
# Attendance Menu
# ==========================================

def attendance_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("        ATTENDANCE MANAGEMENT")
        print("=" * 60)

        print("1. Mark Attendance")
        print("2. Today's Attendance")
        print("3. Search Attendance")
        print("4. Attendance History")
        print("5. Monthly Attendance")
        print("6. Attendance Statistics")
        print("7. Present Employees")
        print("8. Absent Employees")
        print("9. Attendance Percentage")
        print("10. Attendance Report")
        print("11. Export Attendance Report")
        print("12. Best Attendance Employee")
        print("13. Daily Attendance Report")
        print("14. Attendance Dashboard")
        print("15. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            mark_attendance()

        elif choice == "2":

            today_attendance()

        elif choice == "3":

            search_attendance()

        elif choice == "4":

            attendance_history()

        elif choice == "5":

            monthly_attendance()

        elif choice == "6":

            attendance_statistics()

        elif choice == "7":

            present_employees()

        elif choice == "8":

            absent_employees()

        elif choice == "9":

            attendance_percentage()

        elif choice == "10":

            attendance_report()

        elif choice == "11":

            export_attendance_report()

        elif choice == "12":

            best_attendance_employee()

        elif choice == "13":

            daily_attendance_report()

        elif choice == "14":

            attendance_dashboard()

        elif choice == "15":

            print("\nReturning to Previous Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    attendance_menu()