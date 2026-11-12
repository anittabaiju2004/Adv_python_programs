# Employee CRUD
# employee.py (Part 1)

from database import (
    get_employees,
    save_employees
)

from utils import (
    generate_employee_id,
    is_valid_phone,
    is_valid_email
)


# ==========================================
# Add Employee
# ==========================================

def add_employee():

    employees = get_employees()

    print("\n========== ADD EMPLOYEE ==========\n")

    name = input("Employee Name : ").strip()

    department = input("Department : ").strip()

    designation = input("Designation : ").strip()

    phone = input("Phone Number : ").strip()

    if not is_valid_phone(phone):

        print("Invalid Phone Number.")

        return

    for employee in employees:

        if employee["phone"] == phone:

            print("Phone Number Already Exists.")

            return

    email = input("Email Address : ").strip()

    if not is_valid_email(email):

        print("Invalid Email Address.")

        return

    for employee in employees:

        if employee["email"].lower() == email.lower():

            print("Email Already Exists.")

            return

    try:

        salary = float(input("Monthly Salary : ₹"))

    except ValueError:

        print("Invalid Salary.")

        return

    employee = {

        "employee_id": generate_employee_id(employees),

        "name": name,

        "department": department,

        "designation": designation,

        "phone": phone,

        "email": email,

        "salary": salary,

        "attendance": [],

        "present_days": 0,

        "absent_days": 0,

        "leave_days": 0,

        "remaining_leave": 30

    }

    employees.append(employee)

    save_employees(employees)

    print("\nEmployee Added Successfully.")

    print("Employee ID :", employee["employee_id"])


# ==========================================
# View Employees
# ==========================================

def view_employees():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    print("\n========== EMPLOYEE LIST ==========\n")

    print("{:<8} {:<20} {:<15} {:<15} {:>10}".format(

        "ID",
        "Name",
        "Department",
        "Designation",
        "Salary"

    ))

    print("-" * 80)

    for employee in employees:

        print("{:<8} {:<20} {:<15} {:<15} {:>10}".format(

            employee["employee_id"],

            employee["name"],

            employee["department"],

            employee["designation"],

            employee["salary"]

        ))


# ==========================================
# Search Employee by ID
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
            print("Phone       :", employee["phone"])
            print("Email       :", employee["email"])
            print("Salary      : ₹", employee["salary"])

            return

    print("Employee Not Found.")


# ==========================================
# Search Employee by Name
# ==========================================

def search_employee_name():

    employees = get_employees()

    keyword = input(
        "\nEnter Employee Name : "
    ).strip().lower()

    found = False

    print("\n========== SEARCH RESULT ==========\n")

    for employee in employees:

        if keyword in employee["name"].lower():

            found = True

            print("-" * 50)

            print("Employee ID :", employee["employee_id"])
            print("Name        :", employee["name"])
            print("Department  :", employee["department"])
            print("Designation :", employee["designation"])
            print("Salary      : ₹", employee["salary"])

    if not found:

        print("Employee Not Found.")
# ==========================================
# Update Employee
# ==========================================

def update_employee():

    employees = get_employees()

    print("\n========== UPDATE EMPLOYEE ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\nLeave blank to keep existing value.\n")

            name = input(
                f"Name [{employee['name']}] : "
            ).strip()

            if name:

                employee["name"] = name

            department = input(
                f"Department [{employee['department']}] : "
            ).strip()

            if department:

                employee["department"] = department

            designation = input(
                f"Designation [{employee['designation']}] : "
            ).strip()

            if designation:

                employee["designation"] = designation

            phone = input(
                f"Phone [{employee['phone']}] : "
            ).strip()

            if phone:

                if not is_valid_phone(phone):

                    print("Invalid Phone Number.")

                    return

                for emp in employees:

                    if (
                        emp["phone"] == phone and
                        emp["employee_id"] != employee_id
                    ):

                        print("Phone Number Already Exists.")

                        return

                employee["phone"] = phone

            email = input(
                f"Email [{employee['email']}] : "
            ).strip()

            if email:

                if not is_valid_email(email):

                    print("Invalid Email Address.")

                    return

                for emp in employees:

                    if (
                        emp["email"].lower() == email.lower() and
                        emp["employee_id"] != employee_id
                    ):

                        print("Email Already Exists.")

                        return

                employee["email"] = email

            salary = input(
                f"Salary [{employee['salary']}] : "
            ).strip()

            if salary:

                try:

                    employee["salary"] = float(salary)

                except ValueError:

                    print("Invalid Salary.")

                    return

            save_employees(employees)

            print("\nEmployee Updated Successfully.")

            return

    print("Employee Not Found.")


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
            print("-" * 40)
            print("Name        :", employee["name"])
            print("Department  :", employee["department"])
            print("Designation :", employee["designation"])

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
# Search by Department
# ==========================================

def search_department():

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
            print("Salary      : ₹", employee["salary"])

    if not found:

        print("No Employees Found.")


# ==========================================
# Search by Designation
# ==========================================

def search_designation():

    employees = get_employees()

    designation = input(
        "\nEnter Designation : "
    ).strip().lower()

    found = False

    print(f"\n========== {designation.upper()} ==========\n")

    for employee in employees:

        if employee["designation"].lower() == designation:

            found = True

            print("-" * 50)

            print("Employee ID :", employee["employee_id"])
            print("Name        :", employee["name"])
            print("Department  :", employee["department"])
            print("Salary      : ₹", employee["salary"])

    if not found:

        print("No Employees Found.")


# ==========================================
# Total Employees
# ==========================================

def total_employees():

    employees = get_employees()

    print("\nTotal Employees :", len(employees))
# ==========================================
# View Complete Employee Details
# ==========================================

def employee_details():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n")
            print("=" * 60)
            print("          EMPLOYEE DETAILS")
            print("=" * 60)

            print("Employee ID      :", employee["employee_id"])
            print("Name             :", employee["name"])
            print("Department       :", employee["department"])
            print("Designation      :", employee["designation"])
            print("Phone            :", employee["phone"])
            print("Email            :", employee["email"])
            print("Salary           : ₹", employee["salary"])
            print("Present Days     :", employee["present_days"])
            print("Absent Days      :", employee["absent_days"])
            print("Leave Days       :", employee["leave_days"])
            print("Remaining Leave  :", employee["remaining_leave"])

            print("=" * 60)

            return

    print("Employee Not Found.")


# ==========================================
# Department Summary
# ==========================================

def department_summary():

    employees = get_employees()

    departments = {}

    for employee in employees:

        department = employee["department"]

        departments[department] = departments.get(
            department,
            0
        ) + 1

    print("\n========== DEPARTMENT SUMMARY ==========\n")

    if len(departments) == 0:

        print("No Employee Records Found.")

        return

    for department, count in departments.items():

        print(f"{department:<20} : {count}")


# ==========================================
# Designation Summary
# ==========================================

def designation_summary():

    employees = get_employees()

    designations = {}

    for employee in employees:

        designation = employee["designation"]

        designations[designation] = designations.get(
            designation,
            0
        ) + 1

    print("\n========== DESIGNATION SUMMARY ==========\n")

    if len(designations) == 0:

        print("No Employee Records Found.")

        return

    for designation, count in designations.items():

        print(f"{designation:<20} : {count}")


# ==========================================
# Salary Details
# ==========================================

def salary_details():

    employees = get_employees()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            print("\n========== SALARY DETAILS ==========\n")

            print("Employee ID :", employee["employee_id"])
            print("Employee    :", employee["name"])
            print("Department  :", employee["department"])
            print("Designation :", employee["designation"])
            print("Monthly Pay : ₹", employee["salary"])

            return

    print("Employee Not Found.")


# ==========================================
# Employee Statistics
# ==========================================

def employee_statistics():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    total_salary = sum(
        employee["salary"]
        for employee in employees
    )

    average_salary = total_salary / len(employees)

    highest_salary = max(
        employee["salary"]
        for employee in employees
    )

    lowest_salary = min(
        employee["salary"]
        for employee in employees
    )

    print("\n")
    print("=" * 60)
    print("        EMPLOYEE STATISTICS")
    print("=" * 60)

    print("Total Employees :", len(employees))
    print("Total Salary    : ₹", total_salary)
    print("Average Salary  : ₹", round(average_salary, 2))
    print("Highest Salary  : ₹", highest_salary)
    print("Lowest Salary   : ₹", lowest_salary)


# ==========================================
# Salary Range Report
# ==========================================

def salary_range_report():

    employees = get_employees()

    print("\n========== SALARY RANGE REPORT ==========\n")

    for employee in employees:

        salary = employee["salary"]

        if salary >= 100000:

            grade = "A"

        elif salary >= 70000:

            grade = "B"

        elif salary >= 40000:

            grade = "C"

        else:

            grade = "D"

        print("-" * 50)

        print("Employee :", employee["name"])
        print("Salary   : ₹", salary)
        print("Grade    :", grade)
import csv
import os


# ==========================================
# Export Employees to CSV
# ==========================================

def export_employees():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    filename = "employees.csv"

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Employee ID",
            "Name",
            "Department",
            "Designation",
            "Phone",
            "Email",
            "Salary"

        ])

        for employee in employees:

            writer.writerow([

                employee["employee_id"],
                employee["name"],
                employee["department"],
                employee["designation"],
                employee["phone"],
                employee["email"],
                employee["salary"]

            ])

    print("\nEmployees Exported Successfully.")
    print("File :", filename)


# ==========================================
# Import Employees from CSV
# ==========================================

def import_employees():

    employees = get_employees()

    filename = input(
        "\nEnter CSV File Name : "
    ).strip()

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            imported = 0

            for row in reader:

                duplicate = False

                for employee in employees:

                    if employee["email"].lower() == row["Email"].lower():

                        duplicate = True
                        break

                if duplicate:

                    continue

                employees.append({

                    "employee_id": generate_employee_id(employees),
                    "name": row["Name"],
                    "department": row["Department"],
                    "designation": row["Designation"],
                    "phone": row["Phone"],
                    "email": row["Email"],
                    "salary": float(row["Salary"]),
                    "attendance": [],
                    "present_days": 0,
                    "absent_days": 0,
                    "leave_days": 0,
                    "remaining_leave": 30

                })

                imported += 1

        save_employees(employees)

        print(f"\n{imported} Employees Imported Successfully.")

    except FileNotFoundError:

        print("CSV File Not Found.")

    except Exception as e:

        print("Import Error :", e)


# ==========================================
# Highest Salary Employee
# ==========================================

def highest_salary_employee():

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
# Lowest Salary Employee
# ==========================================

def lowest_salary_employee():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    lowest = min(

        employees,

        key=lambda employee: employee["salary"]

    )

    print("\n========== LOWEST SALARY ==========\n")

    print("Employee ID :", lowest["employee_id"])
    print("Name        :", lowest["name"])
    print("Department  :", lowest["department"])
    print("Designation :", lowest["designation"])
    print("Salary      : ₹", lowest["salary"])


# ==========================================
# Employee Dashboard
# ==========================================

def employee_dashboard():

    employees = get_employees()

    print("\n")
    print("=" * 60)
    print("        EMPLOYEE DASHBOARD")
    print("=" * 60)

    print("Total Employees :", len(employees))

    if len(employees):

        total_salary = sum(

            employee["salary"]

            for employee in employees

        )

        print("Total Payroll   : ₹", total_salary)

        print(

            "Average Salary : ₹",

            round(
                total_salary / len(employees),
                2
            )

        )


# ==========================================
# Employee Menu
# ==========================================

def employee_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("        EMPLOYEE MANAGEMENT")
        print("=" * 60)

        print("1. Add Employee")
        print("2. View Employees")
        print("3. Search by ID")
        print("4. Search by Name")
        print("5. Update Employee")
        print("6. Delete Employee")
        print("7. Search by Department")
        print("8. Search by Designation")
        print("9. Employee Details")
        print("10. Department Summary")
        print("11. Designation Summary")
        print("12. Salary Details")
        print("13. Employee Statistics")
        print("14. Salary Range Report")
        print("15. Highest Salary Employee")
        print("16. Lowest Salary Employee")
        print("17. Export Employees")
        print("18. Import Employees")
        print("19. Employee Dashboard")
        print("20. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            add_employee()

        elif choice == "2":

            view_employees()

        elif choice == "3":

            search_employee()

        elif choice == "4":

            search_employee_name()

        elif choice == "5":

            update_employee()

        elif choice == "6":

            delete_employee()

        elif choice == "7":

            search_department()

        elif choice == "8":

            search_designation()

        elif choice == "9":

            employee_details()

        elif choice == "10":

            department_summary()

        elif choice == "11":

            designation_summary()

        elif choice == "12":

            salary_details()

        elif choice == "13":

            employee_statistics()

        elif choice == "14":

            salary_range_report()

        elif choice == "15":

            highest_salary_employee()

        elif choice == "16":

            lowest_salary_employee()

        elif choice == "17":

            export_employees()

        elif choice == "18":

            import_employees()

        elif choice == "19":

            employee_dashboard()

        elif choice == "20":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    employee_menu()