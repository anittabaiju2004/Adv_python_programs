"""Load demo data: 15 employees, attendance for last month and this month,
leave requests, and last month's payroll.

Usage:  python seed_demo.py
Logins: admin / admin123     employees: EMP1001 ... EMP1015 / welcome1
"""
import random
from datetime import date, datetime, timedelta

from ems import utils
from ems.attendance import AttendanceManager
from ems.auth import AuthManager
from ems.database import JSONDatabase
from ems.employees import EmployeeManager
from ems.leaves import LeaveManager
from ems.payroll import PayrollManager

PEOPLE = [  # name, gender, dob, department, designation, basic, type
    ("Anitta Joseph", "Female", "1996-04-12", "Engineering", "Tech Lead", 62000, "Permanent"),
    ("Rahul Menon", "Male", "1990-11-02", "Engineering", "Senior Software Engineer", 48000, "Permanent"),
    ("Priya Nair", "Female", "1985-07-21", "Human Resources", "HR Manager", 55000, "Permanent"),
    ("Arjun Das", "Male", "1999-01-30", "Engineering", "Software Engineer", 28000, "Permanent"),
    ("Fathima Rasheed", "Female", "2001-09-30", "Engineering", "QA Engineer", 22000, "Permanent"),
    ("Thomas Kurian", "Male", "1972-02-09", "Finance", "Finance Manager", 70000, "Permanent"),
    ("Meera Pillai", "Female", "1994-06-18", "Finance", "Accountant", 26000, "Permanent"),
    ("Vishnu Varma", "Male", "1997-03-05", "Sales & Marketing", "Sales Executive", 18000, "Permanent"),
    ("Sneha George", "Female", "1992-12-11", "Sales & Marketing", "Marketing Manager", 52000, "Permanent"),
    ("Akhil Krishnan", "Male", "2000-08-25", "Operations", "Operations Executive", 16000, "Contract"),
    ("Divya Mathew", "Female", "1995-10-14", "Human Resources", "HR Executive", 21000, "Permanent"),
    ("Nikhil Raj", "Male", "2003-05-19", "Engineering", "Software Engineer", 12000, "Intern"),
    ("Lakshmi Iyer", "Female", "1988-01-08", "Operations", "Office Administrator", 19000, "Permanent"),
    ("Sreejith Babu", "Male", "1993-09-09", "Engineering", "Software Engineer", 34000, "Permanent"),
    ("Reshma Thomas", "Female", "1998-02-27", "Sales & Marketing", "Sales Executive", 17500, "Contract"),
]


def main():
    random.seed(21)
    db = JSONDatabase(utils.DATA_DIR)
    if db.all("employees"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth, em = AuthManager(db), EmployeeManager(db)
    am, lm, pm = AttendanceManager(db), LeaveManager(db), PayrollManager(db)
    today = date.today()
    last_month_end = today.replace(day=1) - timedelta(days=1)
    last_month = last_month_end.strftime("%Y-%m")

    emps = []
    for i, (name, gender, dob, dept, desig, basic, etype) in enumerate(PEOPLE):
        joined = today - timedelta(days=random.randint(400, 1800))
        if i == 14:
            joined = last_month_end.replace(day=10)          # mid-month joiner -> prorated salary
        first, last = name.lower().split()
        emp, _ = em.add(name=name, gender=gender, dob=dob, phone=f"9{random.randint(100000000, 999999999)}",
                        email=f"{first}.{last}@ociuz.com", department=dept, designation=desig,
                        join_date=joined.isoformat(), basic_salary=basic, employment_type=etype,
                        pan=f"{''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=5))}{random.randint(1000, 9999)}"
                            f"{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}",
                        bank_account=str(random.randint(10**11, 10**12 - 1)), ifsc="FDRL0001234",
                        address=random.choice(["Thiruvananthapuram", "Kochi", "Kollam", "Attingal"]))
        temp = auth.reset_password(emp.emp_id)
        auth.change_password(emp.emp_id, temp, "welcome1", "welcome1")
        emps.append(emp)
    em.revise_salary(emps[1].emp_id, 52000, "Annual increment", (today - timedelta(days=60)).isoformat())

    # Attendance: every working day from the 1st of last month to yesterday
    d = last_month_end.replace(day=1)
    while d < today:
        if utils.is_working_day(d):
            for e in emps:
                if e.join_date > d.isoformat():
                    continue
                r = random.random()
                if r < 0.03:
                    am.mark(e.emp_id, d, "ABSENT")
                elif r < 0.06:
                    am.mark(e.emp_id, d, "HALF_DAY")
                else:
                    start = datetime.combine(d, datetime.min.time()).replace(hour=9, minute=random.randint(0, 50))
                    am.check_in(e.emp_id, start)
                    am.check_out(e.emp_id, start + timedelta(hours=random.uniform(8, 9.5)))
        d += timedelta(days=1)

    # Leave: a few future requests (some approved, some pending) and one rejected
    def wd_from(offset, n):
        out, x = [], today + timedelta(days=offset)
        while len(out) < n:
            if utils.is_working_day(x):
                out.append(x.isoformat())
            x += timedelta(days=1)
        return out
    plans = [(0, "Casual", 8, 2, "Family function", "approve"), (2, "Earned", 12, 4, "Vacation to Munnar", "approve"),
             (3, "Sick", 5, 1, "Medical check-up", "pending"), (7, "Casual", 9, 1, "Personal work", "pending"),
             (9, "Loss of Pay", 15, 3, "Extended travel", "pending"), (4, "Casual", 6, 1, "Bank work", "reject")]
    for idx, ltype, offset, n, reason, action in plans:
        days = wd_from(offset, n)
        l = lm.apply(emps[idx].emp_id, ltype, days[0], days[-1], reason)
        if action == "approve":
            lm.approve(l["leave_id"], "admin")
        elif action == "reject":
            lm.reject(l["leave_id"], "admin", "Quarter-end closing; please reschedule")

    # Last month's payroll, paid
    r = pm.generate(last_month)
    pm.mark_paid(last_month, paid_on=(last_month_end + timedelta(days=1)).isoformat())

    # One employee who has left
    em.exit_employee(emps[12].emp_id, (today - timedelta(days=3)).isoformat(), "Relocated abroad")

    print(f"Seeded {len(emps)} employees, {len(db.all('attendance'))} attendance records, "
          f"{len(db.all('leaves'))} leave requests, payroll for {last_month} ({r['generated']} payslips, paid).")
    print("Logins: admin / admin123    employees: EMP1001 ... EMP1015 / welcome1")


if __name__ == "__main__":
    main()
