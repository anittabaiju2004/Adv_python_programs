# Payroll module
# payroll.py (Part 1)

from datetime import datetime

from database import (
    get_employees,
    get_payroll,
    save_payroll
)


# ==========================================
# Generate Payroll
# ==========================================

def generate_payroll():

    employees = get_employees()

    payroll = get_payroll()

    print("\n========== GENERATE PAYROLL ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    for employee in employees:

        if employee["employee_id"] == employee_id:

            month = input(
                "Enter Month (YYYY-MM): "
            ).strip()

            for record in payroll:

                if (

                    record["employee_id"] == employee_id

                    and

                    record["month"] == month

                ):

                    print(
                        "Payroll Already Generated."
                    )

                    return

            basic_salary = employee["salary"]

            hra = basic_salary * 0.20

            da = basic_salary * 0.10

            bonus = 0

            deduction = 0

            net_salary = (

                basic_salary

                + hra

                + da

                + bonus

                - deduction

            )

            payroll.append({

                "employee_id": employee_id,

                "name": employee["name"],

                "department": employee["department"],

                "designation": employee["designation"],

                "month": month,

                "basic_salary": basic_salary,

                "hra": hra,

                "da": da,

                "bonus": bonus,

                "deduction": deduction,

                "net_salary": net_salary,

                "generated_on": datetime.now().strftime(

                    "%Y-%m-%d"

                )

            })

            save_payroll(payroll)

            print("\nPayroll Generated Successfully.")

            return

    print("Employee Not Found.")


# ==========================================
# View Payroll
# ==========================================

def view_payroll():

    payroll = get_payroll()

    if len(payroll) == 0:

        print("\nNo Payroll Records Found.")

        return

    print("\n========== PAYROLL RECORDS ==========\n")

    for record in payroll:

        print("-" * 60)

        print("Employee ID :", record["employee_id"])

        print("Employee    :", record["name"])

        print("Month       :", record["month"])

        print("Net Salary  : ₹", record["net_salary"])


# ==========================================
# Search Payroll
# ==========================================

def search_payroll():

    payroll = get_payroll()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    found = False

    for record in payroll:

        if record["employee_id"] == employee_id:

            found = True

            print("\n========== PAYROLL DETAILS ==========\n")

            print("Month        :", record["month"])

            print("Basic Salary : ₹", record["basic_salary"])

            print("HRA          : ₹", record["hra"])

            print("DA           : ₹", record["da"])

            print("Bonus        : ₹", record["bonus"])

            print("Deduction    : ₹", record["deduction"])

            print("Net Salary   : ₹", record["net_salary"])

            print("-" * 50)

    if not found:

        print("Payroll Record Not Found.")


# ==========================================
# Employee Payslip
# ==========================================

def employee_payslip():

    payroll = get_payroll()

    employee_id = input(
        "\nEnter Employee ID : "
    ).strip()

    month = input(
        "Enter Month (YYYY-MM): "
    ).strip()

    for record in payroll:

        if (

            record["employee_id"] == employee_id

            and

            record["month"] == month

        ):

            print("\n")
            print("=" * 60)
            print("              PAYSLIP")
            print("=" * 60)

            print("Employee ID :", record["employee_id"])
            print("Employee    :", record["name"])
            print("Department  :", record["department"])
            print("Designation :", record["designation"])
            print("Month       :", record["month"])

            print("-" * 60)

            print("Basic Salary : ₹", record["basic_salary"])
            print("HRA          : ₹", record["hra"])
            print("DA           : ₹", record["da"])
            print("Bonus        : ₹", record["bonus"])
            print("Deduction    : ₹", record["deduction"])

            print("-" * 60)

            print("Net Salary   : ₹", record["net_salary"])

            print("=" * 60)

            return

    print("Payslip Not Found.")
# ==========================================
# Add Bonus
# ==========================================

def add_bonus():

    payroll = get_payroll()

    print("\n========== ADD BONUS ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    month = input("Enter Month (YYYY-MM) : ").strip()

    for record in payroll:

        if (

            record["employee_id"] == employee_id

            and

            record["month"] == month

        ):

            try:

                bonus = float(
                    input("Bonus Amount : ₹")
                )

            except ValueError:

                print("Invalid Amount.")

                return

            record["bonus"] += bonus

            record["net_salary"] = (

                record["basic_salary"]

                + record["hra"]

                + record["da"]

                + record["bonus"]

                - record["deduction"]

            )

            save_payroll(payroll)

            print("\nBonus Added Successfully.")

            return

    print("Payroll Record Not Found.")


# ==========================================
# Add Deduction
# ==========================================

def add_deduction():

    payroll = get_payroll()

    print("\n========== ADD DEDUCTION ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    month = input("Enter Month (YYYY-MM) : ").strip()

    for record in payroll:

        if (

            record["employee_id"] == employee_id

            and

            record["month"] == month

        ):

            try:

                deduction = float(

                    input("Deduction Amount : ₹")

                )

            except ValueError:

                print("Invalid Amount.")

                return

            record["deduction"] += deduction

            record["net_salary"] = (

                record["basic_salary"]

                + record["hra"]

                + record["da"]

                + record["bonus"]

                - record["deduction"]

            )

            save_payroll(payroll)

            print("\nDeduction Added Successfully.")

            return

    print("Payroll Record Not Found.")


# ==========================================
# Update Payroll
# ==========================================

def update_payroll():

    payroll = get_payroll()

    print("\n========== UPDATE PAYROLL ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    month = input("Enter Month (YYYY-MM) : ").strip()

    for record in payroll:

        if (

            record["employee_id"] == employee_id

            and

            record["month"] == month

        ):

            salary = input(

                f"Basic Salary [{record['basic_salary']}] : "

            ).strip()

            if salary:

                try:

                    record["basic_salary"] = float(salary)

                except ValueError:

                    print("Invalid Salary.")

                    return

            hra = input(

                f"HRA [{record['hra']}] : "

            ).strip()

            if hra:

                record["hra"] = float(hra)

            da = input(

                f"DA [{record['da']}] : "

            ).strip()

            if da:

                record["da"] = float(da)

            record["net_salary"] = (

                record["basic_salary"]

                + record["hra"]

                + record["da"]

                + record["bonus"]

                - record["deduction"]

            )

            save_payroll(payroll)

            print("\nPayroll Updated Successfully.")

            return

    print("Payroll Record Not Found.")


# ==========================================
# Delete Payroll
# ==========================================

def delete_payroll():

    payroll = get_payroll()

    print("\n========== DELETE PAYROLL ==========\n")

    employee_id = input("Enter Employee ID : ").strip()

    month = input("Enter Month (YYYY-MM) : ").strip()

    for record in payroll:

        if (

            record["employee_id"] == employee_id

            and

            record["month"] == month

        ):

            confirm = input(

                "Delete Payroll? (Y/N): "

            ).strip().upper()

            if confirm != "Y":

                print("Deletion Cancelled.")

                return

            payroll.remove(record)

            save_payroll(payroll)

            print("\nPayroll Deleted Successfully.")

            return

    print("Payroll Record Not Found.")


# ==========================================
# Monthly Payroll Report
# ==========================================

def monthly_payroll_report():

    payroll = get_payroll()

    month = input(

        "\nEnter Month (YYYY-MM) : "

    ).strip()

    found = False

    print("\n========== MONTHLY PAYROLL ==========\n")

    for record in payroll:

        if record["month"] == month:

            found = True

            print("-" * 60)

            print("Employee ID :", record["employee_id"])

            print("Employee    :", record["name"])

            print("Department  :", record["department"])

            print("Net Salary  : ₹", record["net_salary"])

    if not found:

        print("No Payroll Records Found.")
import csv
import os

# ==========================================
# Reports Folder
# ==========================================

REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ==========================================
# Payroll Statistics
# ==========================================

def payroll_statistics():

    payroll = get_payroll()

    if len(payroll) == 0:

        print("\nNo Payroll Records Found.")

        return

    total_payroll = sum(

        record["net_salary"]

        for record in payroll

    )

    highest_salary = max(

        record["net_salary"]

        for record in payroll

    )

    lowest_salary = min(

        record["net_salary"]

        for record in payroll

    )

    average_salary = total_payroll / len(payroll)

    print("\n")
    print("=" * 60)
    print("          PAYROLL STATISTICS")
    print("=" * 60)

    print("Total Payroll Records :", len(payroll))
    print("Total Payroll Amount  : ₹", round(total_payroll, 2))
    print("Average Salary        : ₹", round(average_salary, 2))
    print("Highest Salary        : ₹", round(highest_salary, 2))
    print("Lowest Salary         : ₹", round(lowest_salary, 2))


# ==========================================
# Department Payroll Report
# ==========================================

def department_payroll():

    payroll = get_payroll()

    department = input(
        "\nEnter Department : "
    ).strip().lower()

    found = False

    total = 0

    print("\n========== DEPARTMENT PAYROLL ==========\n")

    for record in payroll:

        if record["department"].lower() == department:

            found = True

            total += record["net_salary"]

            print("-" * 50)

            print("Employee :", record["name"])
            print("Month    :", record["month"])
            print("Salary   : ₹", record["net_salary"])

    if found:

        print("-" * 50)

        print("Department Total : ₹", total)

    else:

        print("No Payroll Records Found.")


# ==========================================
# Highest Salary Payroll
# ==========================================

def highest_salary_payroll():

    payroll = get_payroll()

    if len(payroll) == 0:

        print("\nNo Payroll Records Found.")

        return

    highest = max(

        payroll,

        key=lambda record: record["net_salary"]

    )

    print("\n========== HIGHEST PAYROLL ==========\n")

    print("Employee ID :", highest["employee_id"])
    print("Employee    :", highest["name"])
    print("Department  :", highest["department"])
    print("Month       :", highest["month"])
    print("Net Salary  : ₹", highest["net_salary"])


# ==========================================
# Lowest Salary Payroll
# ==========================================

def lowest_salary_payroll():

    payroll = get_payroll()

    if len(payroll) == 0:

        print("\nNo Payroll Records Found.")

        return

    lowest = min(

        payroll,

        key=lambda record: record["net_salary"]

    )

    print("\n========== LOWEST PAYROLL ==========\n")

    print("Employee ID :", lowest["employee_id"])
    print("Employee    :", lowest["name"])
    print("Department  :", lowest["department"])
    print("Month       :", lowest["month"])
    print("Net Salary  : ₹", lowest["net_salary"])


# ==========================================
# Export Payroll Report
# ==========================================

def export_payroll_report():

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
            "Designation",
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
                record["designation"],
                record["month"],
                record["basic_salary"],
                record["bonus"],
                record["deduction"],
                record["net_salary"]

            ])

    print("\nPayroll Report Exported Successfully.")
    print("Saved To :", filename)
# ==========================================
# Payroll Dashboard
# ==========================================

def payroll_dashboard():

    payroll = get_payroll()

    if len(payroll) == 0:

        print("\nNo Payroll Records Found.")

        return

    total_amount = sum(

        record["net_salary"]

        for record in payroll

    )

    average_salary = total_amount / len(payroll)

    print("\n")
    print("=" * 60)
    print("           PAYROLL DASHBOARD")
    print("=" * 60)

    print("Total Payroll Records :", len(payroll))
    print("Total Payroll Amount  : ₹", round(total_amount, 2))
    print("Average Salary        : ₹", round(average_salary, 2))


# ==========================================
# Payroll Summary
# ==========================================

def payroll_summary():

    payroll = get_payroll()

    print("\n========== PAYROLL SUMMARY ==========\n")

    if len(payroll) == 0:

        print("No Payroll Records Found.")

        return

    for record in payroll:

        print("-" * 60)

        print("Employee :", record["name"])
        print("Month    :", record["month"])
        print("Net Pay  : ₹", record["net_salary"])


# ==========================================
# Monthly Payroll Summary
# ==========================================

def monthly_summary():

    payroll = get_payroll()

    month = input(
        "\nEnter Month (YYYY-MM): "
    ).strip()

    total = 0

    found = False

    print("\n========== MONTHLY SUMMARY ==========\n")

    for record in payroll:

        if record["month"] == month:

            found = True

            total += record["net_salary"]

            print("-" * 50)

            print("Employee :", record["name"])
            print("Salary   : ₹", record["net_salary"])

    if found:

        print("-" * 50)

        print("Total Payroll : ₹", round(total, 2))

    else:

        print("No Payroll Records Found.")


# ==========================================
# Export All Payroll Records
# ==========================================

def export_all_payroll():

    export_payroll_report()

    print("\nAll Payroll Records Exported Successfully.")


# ==========================================
# Payroll Menu
# ==========================================

def payroll_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("          PAYROLL MANAGEMENT")
        print("=" * 60)

        print("1. Generate Payroll")
        print("2. View Payroll")
        print("3. Search Payroll")
        print("4. Employee Payslip")
        print("5. Add Bonus")
        print("6. Add Deduction")
        print("7. Update Payroll")
        print("8. Delete Payroll")
        print("9. Monthly Payroll Report")
        print("10. Payroll Statistics")
        print("11. Department Payroll")
        print("12. Highest Salary Payroll")
        print("13. Lowest Salary Payroll")
        print("14. Export Payroll Report")
        print("15. Payroll Dashboard")
        print("16. Payroll Summary")
        print("17. Monthly Summary")
        print("18. Export All Payroll")
        print("19. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            generate_payroll()

        elif choice == "2":

            view_payroll()

        elif choice == "3":

            search_payroll()

        elif choice == "4":

            employee_payslip()

        elif choice == "5":

            add_bonus()

        elif choice == "6":

            add_deduction()

        elif choice == "7":

            update_payroll()

        elif choice == "8":

            delete_payroll()

        elif choice == "9":

            monthly_payroll_report()

        elif choice == "10":

            payroll_statistics()

        elif choice == "11":

            department_payroll()

        elif choice == "12":

            highest_salary_payroll()

        elif choice == "13":

            lowest_salary_payroll()

        elif choice == "14":

            export_payroll_report()

        elif choice == "15":

            payroll_dashboard()

        elif choice == "16":

            payroll_summary()

        elif choice == "17":

            monthly_summary()

        elif choice == "18":

            export_all_payroll()

        elif choice == "19":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    payroll_menu()