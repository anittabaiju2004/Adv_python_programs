# Admin module
# admin.py (Part 1)

from database import (
    get_admins,
    get_employees,
    save_employees
)

from report import report_menu
from backup import backup_menu


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
            admin["username"] == username and
            admin["password"] == password
        ):

            print("\nAdmin Login Successful.")

            admin_dashboard()

            return

    print("\nInvalid Username or Password.")


# ==========================================
# View All Employees
# ==========================================

def view_employees():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    print("\n========== EMPLOYEE LIST ==========\n")

    print("{:<8} {:<20} {:<15} {:<15}".format(
        "Emp ID",
        "Name",
        "Department",
        "Designation"
    ))

    print("-" * 65)

    for employee in employees:

        print("{:<8} {:<20} {:<15} {:<15}".format(

            employee["employee_id"],
            employee["name"],
            employee["department"],
            employee["designation"]

        ))


# ==========================================
# Search Employee
# ==========================================

def search_employee():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n========== EMPLOYEE DETAILS ==========\n")

            print("Employee ID :", employee["employee_id"])
            print("Name        :", employee["name"])
            print("Department  :", employee["department"])
            print("Designation :", employee["designation"])
            print("Salary      :", employee["salary"])
            print("Phone       :", employee["phone"])
            print("Email       :", employee["email"])

            return

    print("\nEmployee Not Found.")


# ==========================================
# Admin Dashboard
# ==========================================

def admin_dashboard():

    while True:

        print("\n")
        print("=" * 60)
        print("            ADMIN DASHBOARD")
        print("=" * 60)

        print("1. View Employees")
        print("2. Search Employee")
        print("3. Delete Employee")
        print("4. Department-wise Employees")
        print("5. Highest Salary Report")
        print("6. Employee Statistics")
        print("7. Attendance Summary")
        print("8. Leave Summary")
        print("9. Dashboard Summary")
        print("10. Recent Employees")
        print("11. Reports")
        print("12. Backup & Restore")
        print("13. Admin Information")
        print("14. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            view_employees()

        elif choice == "2":

            search_employee()

        elif choice == "3":

            delete_employee()

        elif choice == "4":

            department_employees()

        elif choice == "5":

            highest_salary_report()

        elif choice == "6":

            employee_statistics()

        elif choice == "7":

            attendance_summary()

        elif choice == "8":

            leave_summary()

        elif choice == "9":

            dashboard_summary()

        elif choice == "10":

            recent_employees()

        elif choice == "11":

            generate_reports()

        elif choice == "12":

            backup_database()

        elif choice == "13":

            admin_information()

        elif choice == "14":

            admin_logout()

            break

        else:

            print("\nInvalid Choice.")
            
# ==========================================
# Delete Employee
# ==========================================

def delete_employee():

    employees = get_employees()

    print("\n========== DELETE EMPLOYEE ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\nEmployee Found")
            print("-" * 30)
            print("Name       :", employee["name"])
            print("Department :", employee["department"])
            print("Designation:", employee["designation"])

            confirm = input(
                "\nDelete this employee? (Y/N): "
            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")

                return

            employees.remove(employee)

            save_employees(employees)

            print("\nEmployee Deleted Successfully.")

            return

    print("Employee Not Found.")


# ==========================================
# Department-wise Employees
# ==========================================

def department_employees():

    employees = get_employees()

    department = input(
        "\nEnter Department : "
    ).strip().lower()

    found = False

    print(f"\n========== {department.upper()} DEPARTMENT ==========\n")

    for employee in employees:

        if employee["department"].lower() == department:

            found = True

            print("-" * 50)
            print("Employee ID :", employee["employee_id"])
            print("Name        :", employee["name"])
            print("Designation :", employee["designation"])
            print("Salary      :", employee["salary"])

    if not found:

        print("No Employees Found.")


# ==========================================
# Highest Salary Report
# ==========================================

def highest_salary_report():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    highest = max(
        employees,
        key=lambda employee: employee["salary"]
    )

    print("\n========== HIGHEST SALARY ==========\n")

    print("Employee ID :", highest["employee_id"])
    print("Name        :", highest["name"])
    print("Department  :", highest["department"])
    print("Designation :", highest["designation"])
    print("Salary      : ₹", highest["salary"])


# ==========================================
# Employee Statistics
# ==========================================

def employee_statistics():

    employees = get_employees()

    departments = {}

    total_salary = 0

    for employee in employees:

        total_salary += employee["salary"]

        department = employee["department"]

        departments[department] = departments.get(
            department,
            0
        ) + 1

    print("\n========== EMPLOYEE STATISTICS ==========\n")

    print("Total Employees :", len(employees))

    print("Total Salary    : ₹", total_salary)

    if employees:

        average = total_salary / len(employees)

        print("Average Salary  : ₹", round(average, 2))

    print("\nDepartment Summary")

    print("-" * 30)

    for department, count in departments.items():

        print(f"{department:<15} : {count}")


# ==========================================
# Attendance Summary
# ==========================================

def attendance_summary():

    employees = get_employees()

    print("\n========== ATTENDANCE SUMMARY ==========\n")

    for employee in employees:

        print("-" * 50)

        print("Employee :", employee["name"])

        print(
            "Present Days :",
            employee.get("present_days", 0)
        )

        print(
            "Absent Days  :",
            employee.get("absent_days", 0)
        )


# ==========================================
# Leave Summary
# ==========================================

def leave_summary():

    employees = get_employees()

    print("\n========== LEAVE SUMMARY ==========\n")

    for employee in employees:

        print("-" * 50)

        print("Employee :", employee["name"])

        print(
            "Leaves Taken :",
            employee.get("leave_days", 0)
        )

        print(
            "Remaining Leave :",
            employee.get("remaining_leave", 30)
        )
# ==========================================
# Generate Reports
# ==========================================

def generate_reports():

    print("\n========== REPORT MANAGEMENT ==========\n")

    report_menu()


# ==========================================
# Backup Database
# ==========================================

def backup_database():

    print("\n========== DATABASE BACKUP ==========\n")

    backup_menu()


# ==========================================
# Dashboard Summary
# ==========================================

def dashboard_summary():

    employees = get_employees()

    total_employees = len(employees)

    total_salary = 0

    departments = {}

    highest_salary = 0

    highest_employee = None

    for employee in employees:

        total_salary += employee["salary"]

        department = employee["department"]

        departments[department] = departments.get(
            department,
            0
        ) + 1

        if employee["salary"] > highest_salary:

            highest_salary = employee["salary"]

            highest_employee = employee

    print("\n")
    print("=" * 60)
    print("           DASHBOARD SUMMARY")
    print("=" * 60)

    print("Total Employees :", total_employees)
    print("Total Payroll   : ₹", total_salary)

    if total_employees:

        print(
            "Average Salary : ₹",
            round(total_salary / total_employees, 2)
        )

    print("\nDepartment Summary")
    print("-" * 30)

    for department, count in departments.items():

        print(f"{department:<15} : {count}")

    if highest_employee:

        print("\nHighest Paid Employee")

        print("----------------------")

        print("Employee :", highest_employee["name"])

        print("Salary   : ₹", highest_salary)


# ==========================================
# Recent Employees
# ==========================================

def recent_employees():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    print("\n========== RECENT EMPLOYEES ==========\n")

    recent = employees[-5:]

    for employee in recent:

        print("-" * 50)

        print("Employee ID :", employee["employee_id"])
        print("Name        :", employee["name"])
        print("Department  :", employee["department"])
        print("Designation :", employee["designation"])


# ==========================================
# Admin Information
# ==========================================

def admin_information():

    print("\n")
    print("=" * 60)
    print("          ADMIN INFORMATION")
    print("=" * 60)

    print("Application : Employee Management System")
    print("Language    : Python")
    print("Database    : JSON File")
    print("Version     : 1.0")
    print("Access      : Administrator")

    print("=" * 60)


# ==========================================
# Logout
# ==========================================

def admin_logout():

    print("\n")
    print("=" * 60)
    print("Admin Logged Out Successfully")
    print("=" * 60)