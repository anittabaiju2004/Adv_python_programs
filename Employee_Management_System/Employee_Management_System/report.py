# Reports
# report.py (Part 1)

import csv
import os

from database import (
    get_employees,
    get_payroll
)

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Employee Report
# ==========================================

def employee_report():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    filename = os.path.join(

        REPORT_FOLDER,

        "Employee_Report.csv"

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

    print("\nEmployee Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Attendance Report
# ==========================================

def attendance_report():

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
            "Absent Days"

        ])

        for employee in employees:

            writer.writerow([

                employee["employee_id"],
                employee["name"],
                employee["present_days"],
                employee["absent_days"]

            ])

    print("\nAttendance Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Leave Report
# ==========================================

def leave_report():

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

    print("\nLeave Report Generated Successfully.")
    print("Saved To :", filename)


# ==========================================
# Payroll Report
# ==========================================

def payroll_report():

    payroll = get_payroll()

    if len(payroll) == 0:

        print("\nNo Payroll Records Found.")

        return

    filename = os.path.join(

        REPORT_FOLDER,

        "Payroll_Report.csv"

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
            "Department",
            "Month",
            "Basic Salary",
            "Bonus",
            "Deduction",
            "Net Salary"

        ])

        for record in payroll:

            writer.writerow([

                record["employee_id"],
                record["name"],
                record["department"],
                record["month"],
                record["basic_salary"],
                record["bonus"],
                record["deduction"],
                record["net_salary"]

            ])

    print("\nPayroll Report Generated Successfully.")
    print("Saved To :", filename)
# ==========================================
# Employee Summary Report
# ==========================================

def employee_summary():

    employees = get_employees()

    print("\n")
    print("=" * 60)
    print("         EMPLOYEE SUMMARY")
    print("=" * 60)

    if len(employees) == 0:

        print("No Employee Records Found.")

        return

    print("Total Employees :", len(employees))

    total_salary = sum(

        employee["salary"]

        for employee in employees

    )

    print("Total Salary    : ₹", total_salary)

    print(

        "Average Salary : ₹",

        round(
            total_salary / len(employees),
            2
        )

    )


# ==========================================
# Department Report
# ==========================================

def department_report():

    employees = get_employees()

    departments = {}

    for employee in employees:

        department = employee["department"]

        departments[department] = departments.get(

            department,

            0

        ) + 1

    print("\n")
    print("=" * 60)
    print("         DEPARTMENT REPORT")
    print("=" * 60)

    if len(departments) == 0:

        print("No Department Records Found.")

        return

    for department, count in departments.items():

        print(f"{department:<20} : {count}")


# ==========================================
# Salary Report
# ==========================================

def salary_report():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    print("\n")
    print("=" * 60)
    print("           SALARY REPORT")
    print("=" * 60)

    for employee in employees:

        print("-" * 50)

        print("Employee ID :", employee["employee_id"])

        print("Name        :", employee["name"])

        print("Department  :", employee["department"])

        print("Salary      : ₹", employee["salary"])


# ==========================================
# Attendance Summary
# ==========================================

def attendance_summary():

    employees = get_employees()

    print("\n")
    print("=" * 60)
    print("       ATTENDANCE SUMMARY")
    print("=" * 60)

    if len(employees) == 0:

        print("No Employee Records Found.")

        return

    for employee in employees:

        total_days = (

            employee["present_days"]

            + employee["absent_days"]

        )

        if total_days > 0:

            percentage = (

                employee["present_days"]

                / total_days

            ) * 100

        else:

            percentage = 0

        print("-" * 50)

        print("Employee :", employee["name"])

        print("Present  :", employee["present_days"])

        print("Absent   :", employee["absent_days"])

        print(

            "Attendance : {:.2f}%".format(

                percentage

            )

        )


# ==========================================
# Leave Summary
# ==========================================

def leave_summary():

    employees = get_employees()

    print("\n")
    print("=" * 60)
    print("          LEAVE SUMMARY")
    print("=" * 60)

    if len(employees) == 0:

        print("No Employee Records Found.")

        return

    for employee in employees:

        print("-" * 50)

        print("Employee :", employee["name"])

        print("Leave Taken     :", employee["leave_days"])

        print(

            "Remaining Leave :",

            employee["remaining_leave"]

        )
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)


# ==========================================
# Payroll Summary
# ==========================================

def payroll_summary():

    payroll = get_payroll()

    print("\n")
    print("=" * 60)
    print("          PAYROLL SUMMARY")
    print("=" * 60)

    if len(payroll) == 0:

        print("No Payroll Records Found.")

        return

    total = 0

    for record in payroll:

        total += record["net_salary"]

        print("-" * 50)

        print("Employee :", record["name"])

        print("Month    :", record["month"])

        print("Salary   : ₹", record["net_salary"])

    print("-" * 50)

    print("Total Payroll : ₹", round(total, 2))


# ==========================================
# Employee Statistics
# ==========================================

def employee_statistics_report():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    highest = max(

        employees,

        key=lambda employee: employee["salary"]

    )

    lowest = min(

        employees,

        key=lambda employee: employee["salary"]

    )

    average = sum(

        employee["salary"]

        for employee in employees

    ) / len(employees)

    print("\n")
    print("=" * 60)
    print("       EMPLOYEE STATISTICS")
    print("=" * 60)

    print("Total Employees :", len(employees))

    print("Average Salary  : ₹", round(average, 2))

    print("\nHighest Salary")

    print("----------------")

    print(highest["name"])

    print("₹", highest["salary"])

    print("\nLowest Salary")

    print("----------------")

    print(lowest["name"])

    print("₹", lowest["salary"])


# ==========================================
# Department Statistics
# ==========================================

def department_statistics():

    employees = get_employees()

    departments = {}

    salary = {}

    for employee in employees:

        department = employee["department"]

        departments[department] = departments.get(

            department,

            0

        ) + 1

        salary[department] = salary.get(

            department,

            0

        ) + employee["salary"]

    print("\n")
    print("=" * 60)
    print("      DEPARTMENT STATISTICS")
    print("=" * 60)

    for department in departments:

        average = (

            salary[department]

            / departments[department]

        )

        print("-" * 50)

        print("Department :", department)

        print("Employees  :", departments[department])

        print("Avg Salary : ₹", round(average, 2))


# ==========================================
# Monthly Payroll Summary
# ==========================================

def monthly_report():

    payroll = get_payroll()

    month = input(

        "\nEnter Month (YYYY-MM): "

    ).strip()

    total = 0

    found = False

    print("\n========== MONTHLY REPORT ==========\n")

    for record in payroll:

        if record["month"] == month:

            found = True

            total += record["net_salary"]

            print("-" * 50)

            print("Employee :", record["name"])

            print("Department :", record["department"])

            print("Salary : ₹", record["net_salary"])

    if found:

        print("-" * 50)

        print("Total Payroll :", round(total, 2))

    else:

        print("No Records Found.")


# ==========================================
# Employee PDF Report
# ==========================================

def employee_pdf_report():

    employees = get_employees()

    if len(employees) == 0:

        print("\nNo Employee Records Found.")

        return

    filename = os.path.join(

        REPORT_FOLDER,

        "Employee_Report.pdf"

    )

    styles = getSampleStyleSheet()

    story = []

    story.append(

        Paragraph(

            "<b>EMPLOYEE MANAGEMENT REPORT</b>",

            styles["Title"]

        )

    )

    story.append(

        Spacer(1, 15)

    )

    for employee in employees:

        story.append(

            Paragraph(

                f"<b>{employee['name']}</b>",

                styles["Heading2"]

            )

        )

        story.append(

            Paragraph(

                f"Employee ID : {employee['employee_id']}",

                styles["BodyText"]

            )

        )

        story.append(

            Paragraph(

                f"Department : {employee['department']}",

                styles["BodyText"]

            )

        )

        story.append(

            Paragraph(

                f"Designation : {employee['designation']}",

                styles["BodyText"]

            )

        )

        story.append(

            Paragraph(

                f"Salary : ₹ {employee['salary']}",

                styles["BodyText"]

            )

        )

        story.append(

            Spacer(1, 10)

        )

    pdf = SimpleDocTemplate(filename)

    pdf.build(story)

    print("\nEmployee PDF Report Generated Successfully.")

    print("Saved To :", filename)
# ==========================================
# View Generated Reports
# ==========================================

def view_reports():

    files = os.listdir(REPORT_FOLDER)

    print("\n")
    print("=" * 60)
    print("          GENERATED REPORTS")
    print("=" * 60)

    if len(files) == 0:

        print("No Reports Available.")

        return

    for index, file in enumerate(files, start=1):

        print(f"{index}. {file}")


# ==========================================
# Export All Reports
# ==========================================

def export_all_reports():

    print("\nGenerating All Reports...\n")

    employee_report()

    attendance_report()

    leave_report()

    payroll_report()

    employee_pdf_report()

    print("\n")
    print("=" * 60)
    print("ALL REPORTS GENERATED SUCCESSFULLY")
    print("=" * 60)

    print("Location :", REPORT_FOLDER)


# ==========================================
# Report Dashboard
# ==========================================

def report_dashboard():

    employees = get_employees()

    payroll = get_payroll()

    reports = os.listdir(REPORT_FOLDER)

    print("\n")
    print("=" * 60)
    print("          REPORT DASHBOARD")
    print("=" * 60)

    print("Total Employees :", len(employees))

    print("Payroll Records :", len(payroll))

    print("Generated Reports :", len(reports))

    if payroll:

        total = sum(

            record["net_salary"]

            for record in payroll

        )

        print("Total Payroll : ₹", round(total, 2))


# ==========================================
# Overall Statistics
# ==========================================

def overall_statistics():

    employees = get_employees()

    payroll = get_payroll()

    print("\n")
    print("=" * 60)
    print("         OVERALL STATISTICS")
    print("=" * 60)

    print("Employees :", len(employees))

    print("Payroll Records :", len(payroll))

    if employees:

        total_salary = sum(

            employee["salary"]

            for employee in employees

        )

        print("Average Salary : ₹",

              round(

                  total_salary /

                  len(employees),

                  2

              ))


# ==========================================
# Report Menu
# ==========================================

def report_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("         REPORT MANAGEMENT")
        print("=" * 60)

        print("1. Employee Report")
        print("2. Attendance Report")
        print("3. Leave Report")
        print("4. Payroll Report")
        print("5. Employee Summary")
        print("6. Department Report")
        print("7. Salary Report")
        print("8. Attendance Summary")
        print("9. Leave Summary")
        print("10. Payroll Summary")
        print("11. Employee Statistics")
        print("12. Department Statistics")
        print("13. Monthly Report")
        print("14. Employee PDF Report")
        print("15. Export All Reports")
        print("16. View Generated Reports")
        print("17. Report Dashboard")
        print("18. Overall Statistics")
        print("19. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            employee_report()

        elif choice == "2":

            attendance_report()

        elif choice == "3":

            leave_report()

        elif choice == "4":

            payroll_report()

        elif choice == "5":

            employee_summary()

        elif choice == "6":

            department_report()

        elif choice == "7":

            salary_report()

        elif choice == "8":

            attendance_summary()

        elif choice == "9":

            leave_summary()

        elif choice == "10":

            payroll_summary()

        elif choice == "11":

            employee_statistics_report()

        elif choice == "12":

            department_statistics()

        elif choice == "13":

            monthly_report()

        elif choice == "14":

            employee_pdf_report()

        elif choice == "15":

            export_all_reports()

        elif choice == "16":

            view_reports()

        elif choice == "17":

            report_dashboard()

        elif choice == "18":

            overall_statistics()

        elif choice == "19":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    report_menu()