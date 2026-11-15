"""Menu-driven command-line interface: admin (HR) panel and employee self-service."""
from __future__ import annotations

import getpass
import sys
from datetime import date, timedelta

from . import utils
from .attendance import MARKABLE, AttendanceManager
from .auth import AuthManager
from .backup import BackupManager
from .database import JSONDatabase
from .employees import DepartmentManager, Employee, EmployeeManager
from .leaves import LeaveManager
from .payroll import PayrollManager, calculate_salary
from .reports import ReportGenerator
from .utils import (COMPANY_NAME, EMPLOYMENT_TYPES, GENDERS, LEAVE_TYPES, EMSError, money)

W = 78


# ======================================================================= ui
def line(ch: str = "-") -> None:
    print(ch * W)


def header(title: str) -> None:
    print()
    line("=")
    print(f"{title:^{W}}")
    line("=")


def ask(prompt: str, default: str | None = None) -> str:
    v = input(f"  {prompt}{f' [{default}]' if default else ''}: ").strip()
    return v if v else (default or "")


def confirm(prompt: str) -> bool:
    return ask(f"{prompt} (y/n)").lower() in ("y", "yes")


def pause() -> None:
    input("\n  Press Enter to continue...")


def menu(title: str, options: list[str], back: str = "Back") -> str:
    header(title)
    for i, o in enumerate(options, 1):
        print(f"  {i:>2}. {o}")
    print(f"   0. {back}")
    return ask("Choose an option")


def choose(prompt: str, options: list[str], allow_blank: bool = False) -> str:
    for i, o in enumerate(options, 1):
        print(f"     {i}. {o}")
    while True:
        v = ask(prompt)
        if allow_blank and not v:
            return ""
        if v.isdigit() and 1 <= int(v) <= len(options):
            return options[int(v) - 1]
        for o in options:
            if o.lower() == v.lower():
                return o
        print("  Invalid choice.")


def this_month() -> str:
    return date.today().strftime("%Y-%m")


def last_month() -> str:
    return (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def print_employees(emps: list[Employee]) -> None:
    if not emps:
        print("  No employees found.")
        return
    print(f"  {'Emp ID':<9}{'Name':<22}{'Department':<19}{'Designation':<22}{'Basic':>12}  Status")
    line()
    for e in emps:
        print(f"  {e.emp_id:<9}{e.name[:21]:<22}{e.department[:18]:<19}{e.designation[:21]:<22}"
              f"{money(e.basic_salary):>12}  {e.status}")
    line()
    print(f"  {len(emps)} employee(s)")


def print_employee(e: Employee) -> None:
    header(f"{e.emp_id} — {e.name}")
    rows = [("Gender", e.gender), ("Date of birth", f"{e.dob} (age {e.age})"), ("Phone", e.phone),
            ("Email", e.email), ("PAN", e.pan), ("Address", e.address), ("Department", e.department),
            ("Designation", e.designation), ("Employment type", e.employment_type),
            ("Joining date", f"{e.join_date} ({e.experience_years} yrs)"), ("Basic salary", money(e.basic_salary)),
            ("Bank account", f"{e.bank_account} {e.ifsc}".strip()), ("Status", e.status)]
    if e.exit_date:
        rows.append(("Exit", f"{e.exit_date} — {e.exit_reason}"))
    for label, value in rows:
        print(f"  {label:<16}: {value or '-'}")
    if len(e.salary_history) > 1:
        print("\n  Salary history:")
        for h in e.salary_history:
            old = money(h["old"]) if h["old"] else "-"
            print(f"    {h['date']}  {old:>12} → {money(h['new']):<12} {h['reason']}")


def print_salary(c: dict) -> None:
    lop = c["lop_days"] > 0
    print(f"  {'Earnings':<24}{'Full month':>14}" + (f"{'Earned':>14}" if lop else ""))
    for label, key in [("Basic", "basic"), ("HRA", "hra"), ("DA", "da"), ("Conveyance", "conveyance"),
                       ("Medical allowance", "medical")]:
        print(f"  {label:<24}{money(c[key + '_full']):>14}" + (f"{money(c[key]):>14}" if lop else ""))
    print(f"  {'Gross':<24}{money(c['gross_full']):>14}" + (f"{money(c['gross']):>14}" if lop else ""))
    if lop:
        print(f"  LOP: {c['lop_days']:g} of {c['working_days']} working days = -{money(c['lop_deduction'])}")
    print(f"\n  {'Provident Fund':<24}{money(c['pf']):>14}")
    print(f"  {'ESI':<24}{money(c['esi']):>14}")
    print(f"  {'Professional tax':<24}{money(c['professional_tax']):>14}")
    print(f"  {'Total deductions':<24}{money(c['total_deductions']):>14}")
    line()
    print(f"  {'NET PAY':<24}{money(c['net']):>14}")
    print(f"  {'Annual CTC (incl. employer PF)':<32}{money(c['annual_ctc'])}")


def print_leaves(leaves: list[dict], names: dict | None = None) -> None:
    if not leaves:
        print("  No leave records.")
        return
    for l in leaves:
        who = f"{l['emp_id']} {names.get(l['emp_id'], '')[:16]:<17}" if names else ""
        print(f"  {l['leave_id']:<11}{who}{l['leave_type']:<12}{l['start']} → {l['end']}  "
              f"{l['days']:>2}d  {l['status']:<9} {l['reason'][:22]}")
        if l.get("remarks"):
            print(f"  {'':<11}Remarks: {l['remarks']}")


def print_balance(bal: dict) -> None:
    print(f"  {'Leave type':<14}{'Entitled':>9}{'Used':>7}{'Pending':>9}{'Available':>11}")
    for t, b in bal.items():
        ent = "-" if b["entitled"] is None else f"{b['entitled']:g}"
        avail = "unlimited" if b["available"] is None else f"{b['available']:g}"
        print(f"  {t:<14}{ent:>9}{b['used']:>7}{b['pending']:>9}{avail:>11}")


def print_summary(s: dict) -> None:
    print(f"  Working days so far : {s['working_days']}")
    print(f"  Present / Half days : {s['present']} / {s['half_day']}   Late arrivals: {s['late']}")
    print(f"  Absent              : {s['absent']}")
    print(f"  Leave (paid/unpaid) : {s['leave_paid']} / {s['leave_unpaid']}")
    print(f"  Not marked          : {s['unmarked']}")
    print(f"  LOP days            : {s['lop_days']:g}     Attendance: {s['attendance_percent']}%")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)                # data loaded automatically at start-up
        self.auth = AuthManager(self.db)
        self.em = EmployeeManager(self.db, self.auth)
        self.dm = DepartmentManager(self.db)
        self.am = AttendanceManager(self.db)
        self.lm = LeaveManager(self.db)
        self.pm = PayrollManager(self.db)
        self.reports = ReportGenerator(self.db, report_dir or utils.REPORT_DIR)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.user: dict | None = None

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(f"EMPLOYEE MANAGEMENT SYSTEM — {COMPANY_NAME}",
                          ["Admin login", "Employee login", "Salary calculator"], "Exit")
            try:
                if choice in ("1", "2"):
                    self.login(admin=(choice == "1"))
                elif choice == "3":
                    self.salary_calculator()
                    pause()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except EMSError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def login(self, admin: bool) -> None:
        header("ADMIN LOGIN" if admin else "EMPLOYEE LOGIN")
        user = self.auth.login(ask("Username" if admin else "Employee ID"), getpass.getpass("  Password: "))
        if (user["role"] == "admin") != admin:
            raise EMSError("Please use the " + ("employee" if admin else "admin") + " login for this account.")
        self.user = user
        if user["must_change_password"]:
            print("\n  You are using a temporary password. Please set a new one now.")
            self.change_password(first_time=True)
        if admin:
            pending = len(self.lm.pending())
            print(f"\n  Welcome, {user['username']}." + (f"  ⚠ {pending} leave request(s) pending." if pending else ""))
            self.loop(self.admin_actions(), f"ADMIN PANEL — {user['username']}")
        else:
            emp = self.em.get(user["emp_id"])
            print(f"\n  Welcome, {emp.name}!")
            self.loop(self.employee_actions(), f"EMPLOYEE PORTAL — {emp.emp_id} {emp.name}")

    def loop(self, actions: list[tuple[str, callable, bool]], title: str) -> None:
        """actions: (label, handler, is_submenu)."""
        while self.user:
            choice = menu(title, [a[0] for a in actions], "Logout")
            if choice == "0":
                print("  Logged out.")
                self.user = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(actions)):
                continue
            label, handler, submenu = actions[int(choice) - 1]
            try:
                handler()
                if submenu:
                    continue
            except EMSError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def change_password(self, first_time: bool = False) -> None:
        while True:
            try:
                self.auth.change_password(self.user["username"], getpass.getpass("  Current password: "),
                                          getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
                print("  ✔ Password changed.")
                return
            except EMSError as exc:
                print(f"  ✖ {exc}")
                if not first_time:
                    return

    def salary_calculator(self) -> None:
        header("SALARY CALCULATOR")
        basic = ask("Monthly basic salary")
        wd = ask("Working days in month (blank = no LOP)")
        lop = ask("LOP days", "0") if wd else "0"
        try:
            c = calculate_salary(basic, int(wd) if wd.isdigit() else 0, float(lop))
        except ValueError:
            raise EMSError("Please enter numbers only.")
        print()
        print_salary(c)

    # ============================================================ employee
    def employee_actions(self):
        return [("My profile", self.my_profile, False), ("Check in", self.my_check_in, False),
                ("Check out", self.my_check_out, False), ("My attendance", self.my_attendance, False),
                ("Apply for leave", self.my_apply_leave, False), ("My leaves & balance", self.my_leaves, False),
                ("Cancel a leave request", self.my_cancel_leave, False), ("My payslips", self.my_payslips, False),
                ("Change password", self.change_password, False)]

    @property
    def me(self) -> str:
        return self.user["emp_id"]

    def my_profile(self) -> None:
        print_employee(self.em.get(self.me))

    def my_check_in(self) -> None:
        r = self.am.check_in(self.me)
        print(f"  ✔ Checked in at {r['check_in']}" + ("  (late)" if r["late"] else ""))

    def my_check_out(self) -> None:
        r = self.am.check_out(self.me)
        print(f"  ✔ Checked out at {r['check_out']} — {r['hours']} hours" +
              ("  (marked half day)" if r["status"] == "HALF_DAY" else ""))

    def my_attendance(self) -> None:
        month = ask("Month YYYY-MM", this_month())
        header(f"MY ATTENDANCE — {month}")
        for r in self.am.records(self.me, month):
            times = f"{r['check_in'] or '':>9} {r['check_out'] or '':>9}" if r.get("check_in") else " " * 19
            extra = (" late" if r.get("late") else "") + (f" {r['leave_type']}" if r.get("leave_type") else "")
            print(f"  {r['date']}  {r['status']:<9}{times}{extra}")
        print()
        print_summary(self.am.monthly_summary(self.me, month))

    def my_apply_leave(self) -> None:
        header("APPLY FOR LEAVE")
        print_balance(self.lm.balance(self.me))
        print()
        lt = choose("Leave type", list(LEAVE_TYPES))
        start = ask("From date YYYY-MM-DD")
        end = ask("To date YYYY-MM-DD", start)
        l = self.lm.apply(self.me, lt, start, end, ask("Reason"))
        print(f"  ✔ Leave request {l['leave_id']} submitted for {l['days']} working day(s). Awaiting approval.")

    def my_leaves(self) -> None:
        header("MY LEAVES")
        print_balance(self.lm.balance(self.me))
        print()
        print_leaves(self.lm.list(self.me))

    def my_cancel_leave(self) -> None:
        open_ = [l for l in self.lm.list(self.me) if l["status"] in ("PENDING", "APPROVED")]
        print_leaves(open_)
        if open_:
            self.lm.cancel(ask("Leave ID to cancel").upper(), by_emp=self.me)
            print("  ✔ Leave cancelled.")

    def my_payslips(self) -> None:
        slips = self.pm.payslips_for(self.me)
        if not slips:
            print("  No payslips yet.")
            return
        for i, p in enumerate(slips, 1):
            print(f"  {i:>2}. {p['month']}   net {money(p['net']):>13}   {p['status']}")
        n = ask("Number to download as PDF (blank = none)")
        if n.isdigit() and 1 <= int(n) <= len(slips):
            print(f"  ✔ Saved: {self.reports.payslip_pdf(self.me, slips[int(n) - 1]['month'])}")

    # =============================================================== admin
    def admin_actions(self):
        return [("Employees", self.employee_menu, True), ("Departments & designations", self.department_menu, True),
                ("Attendance", self.attendance_menu, True), ("Leave management", self.leave_menu, True),
                ("Payroll", self.payroll_menu, True), ("Reports", self.report_menu, True),
                ("Backup & restore", self.backup_menu, True), ("User accounts", self.account_menu, True),
                ("Change password", self.change_password, False)]

    def _submenu(self, title: str, options: list[tuple[str, callable]]) -> None:
        while True:
            choice = menu(title, [o[0] for o in options])
            if choice == "0":
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(options)):
                continue
            try:
                options[int(choice) - 1][1]()
            except EMSError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def pick_employee(self, include_exited: bool = False) -> Employee:
        q = ask("Employee ID or name")
        try:
            return self.em.get(q)
        except EMSError:
            pass
        matches = self.em.search(q, include_exited)
        if not matches:
            raise EMSError(f"No employee matches '{q}'.")
        if len(matches) == 1:
            return matches[0]
        for i, e in enumerate(matches, 1):
            print(f"  {i:>2}. {e.emp_id}  {e.name}  ({e.department})")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= len(matches)):
            raise EMSError("Invalid selection.")
        return matches[int(n) - 1]

    # --------------------------------------------------------- employees
    def employee_menu(self) -> None:
        self._submenu("EMPLOYEES", [
            ("Add employee", self.add_employee), ("View all employees", self.view_employees),
            ("Search employees", lambda: print_employees(self.em.search(ask("Keyword (ID, name, phone, email, department)"),
                                                                         confirm("Include exited employees?")))),
            ("Employee details", lambda: print_employee(self.pick_employee(True))),
            ("Update employee", self.update_employee), ("Revise salary", self.revise_salary),
            ("Exit employee (resignation / termination)", self.exit_employee),
            ("Rehire exited employee", self.rehire), ("Delete employee permanently", self.delete_employee)])

    def add_employee(self) -> None:
        header("ADD EMPLOYEE")
        data = {"name": ask("Full name"), "gender": choose("Gender", GENDERS), "dob": ask("Date of birth YYYY-MM-DD"),
                "phone": ask("Mobile number"), "email": ask("Email"), "pan": ask("PAN (optional)"),
                "address": ask("Address (optional)")}
        data["department"] = choose("Department", self.dm.names())
        data["designation"] = choose("Designation", self.dm.get(data["department"])["designations"])
        data["employment_type"] = choose("Employment type", EMPLOYMENT_TYPES)
        data["join_date"] = ask("Joining date YYYY-MM-DD", date.today().isoformat())
        data["basic_salary"] = ask("Monthly basic salary")
        data["bank_account"] = ask("Bank account no. (optional)")
        data["ifsc"] = ask("IFSC (optional)") if data["bank_account"] else ""
        emp, temp = self.em.add(**data)
        print(f"\n  ✔ {emp.name} added as {emp.emp_id}.")
        print(f"    Login: {emp.emp_id}   Temporary password: {temp}")
        print("    (Share this with the employee — they must change it at first login.)")

    def view_employees(self) -> None:
        status = choose("Show", ["Active", "Exited", "All"])
        sort = choose("Sort by", list(self.em.SORTS))
        dept = choose("Department (blank = all)", self.dm.names(), allow_blank=True) or None
        print_employees(self.em.list(None if status == "All" else status, dept, sort_by=sort))

    def update_employee(self) -> None:
        e = self.pick_employee()
        print_employee(e)
        print("\n  Leave blank to keep the current value.")
        changes = {k: ask(label, getattr(e, k) or None) for k, label in
                   [("name", "Name"), ("phone", "Phone"), ("email", "Email"), ("pan", "PAN"), ("address", "Address"),
                    ("bank_account", "Bank account"), ("ifsc", "IFSC")]}
        changes = {k: v for k, v in changes.items() if v != (getattr(e, k) or "")}
        if confirm("Change department / designation?"):
            changes["department"] = choose("Department", self.dm.names())
            changes["designation"] = choose("Designation", self.dm.get(changes["department"])["designations"])
        if confirm("Change employment type?"):
            changes["employment_type"] = choose("Employment type", EMPLOYMENT_TYPES)
        if not changes:
            print("  No changes.")
            return
        self.em.update(e.emp_id, **changes)
        print(f"  ✔ Updated: {', '.join(changes)}.")

    def revise_salary(self) -> None:
        e = self.pick_employee()
        print(f"  Current basic: {money(e.basic_salary)}")
        pct = ask("Increment % (or blank to enter an amount)")
        new = round(e.basic_salary * (1 + float(pct) / 100), 2) if pct.replace(".", "", 1).isdigit() else ask("New basic salary")
        e2 = self.em.revise_salary(e.emp_id, new, ask("Reason", "Annual increment"))
        print(f"  ✔ Basic revised {money(e.basic_salary)} → {money(e2.basic_salary)}.")

    def exit_employee(self) -> None:
        e = self.pick_employee()
        if confirm(f"Mark {e.emp_id} {e.name} as exited? Their login will be disabled"):
            self.em.exit_employee(e.emp_id, ask("Last working day YYYY-MM-DD", date.today().isoformat()),
                                  ask("Reason", "Resigned"))
            print("  ✔ Employee exited. Records are kept for reports and payroll.")

    def rehire(self) -> None:
        e = self.pick_employee(include_exited=True)
        self.em.rehire(e.emp_id)
        print(f"  ✔ {e.emp_id} is active again.")

    def delete_employee(self) -> None:
        e = self.pick_employee(include_exited=True)
        print("  ⚠ This removes the employee and ALL their attendance, leave and payroll records.")
        print("    (To keep history, use 'Exit employee' instead.)")
        if confirm(f"Permanently delete {e.emp_id} {e.name}?"):
            self.backup.create_backup("pre_delete")
            r = self.em.delete(e.emp_id)
            print(f"  ✔ Deleted (attendance {r['attendance']}, leaves {r['leaves']}, payslips {r['payroll']}). "
                  "A backup was taken first.")

    # ------------------------------------------------------- departments
    def department_menu(self) -> None:
        def show():
            counts = self.dm.headcount()
            for d in self.dm.list():
                print(f"  {d['name']:<26}{counts.get(d['name'], 0):>3} employee(s)")
                print(f"  {'':<4}{', '.join(d['designations']) or '(no designations)'}")
        self._submenu("DEPARTMENTS & DESIGNATIONS", [
            ("List departments", show),
            ("Add department", lambda: print(f"  ✔ Added '{self.dm.add(ask('Department name'))['name']}'.")),
            ("Rename department", lambda: print(f"  ✔ Renamed; {self.dm.rename(choose('Department', self.dm.names()), ask('New name'))} employee(s) updated.")),
            ("Delete department", lambda: (self.dm.delete(choose("Department", self.dm.names())), print("  ✔ Deleted."))),
            ("Add designation", lambda: (self.dm.add_designation(choose("Department", self.dm.names()), ask("Designation")),
                                         print("  ✔ Added."))),
            ("Remove designation", self._remove_designation)])

    def _remove_designation(self) -> None:
        dept = choose("Department", self.dm.names())
        self.dm.remove_designation(dept, choose("Designation", self.dm.get(dept)["designations"]))
        print("  ✔ Removed.")

    # -------------------------------------------------------- attendance
    def attendance_menu(self) -> None:
        self._submenu("ATTENDANCE", [
            ("Mark attendance for all employees", self.mark_all), ("Mark / correct one employee", self.mark_one),
            ("Daily register", self.daily_register), ("Monthly summary (one employee)", self.monthly_one),
            ("Monthly overview (all employees)", self.monthly_all)])

    def mark_all(self) -> None:
        day = ask("Date YYYY-MM-DD", date.today().isoformat())
        print("  Everyone will be marked PRESENT except those you list.")
        exceptions = {}
        while True:
            emp_id = ask("Exception employee ID (blank = done)").upper()
            if not emp_id:
                break
            exceptions[emp_id] = choose(f"Status for {emp_id}", MARKABLE)
        r = self.am.mark_all(day, "PRESENT", exceptions)
        print(f"  ✔ Marked {r['marked']}; on leave {r['on_leave']}; skipped {r['skipped']} "
              "(not yet joined or already checked in).")

    def mark_one(self) -> None:
        e = self.pick_employee()
        r = self.am.mark(e.emp_id, ask("Date YYYY-MM-DD", date.today().isoformat()), choose("Status", MARKABLE))
        print(f"  ✔ {e.emp_id} marked {r['status']} on {r['date']}.")

    def daily_register(self) -> None:
        day = ask("Date YYYY-MM-DD", date.today().isoformat())
        header(f"ATTENDANCE REGISTER — {day}" + ("" if utils.is_working_day(utils.parse_date(day)) else " (non-working day)"))
        for row in self.am.register(day):
            e, r = row["employee"], row["record"]
            status = r["status"] if r else "— not marked"
            times = f"in {r['check_in']} out {r['check_out'] or '-'}" if r and r.get("check_in") else ""
            print(f"  {e.emp_id:<9}{e.name[:22]:<23}{status:<14}{times}{'  late' if r and r.get('late') else ''}")

    def monthly_one(self) -> None:
        e = self.pick_employee(True)
        month = ask("Month YYYY-MM", this_month())
        header(f"{e.emp_id} {e.name} — {month}")
        print_summary(self.am.monthly_summary(e.emp_id, month))

    def monthly_all(self) -> None:
        month = ask("Month YYYY-MM", this_month())
        header(f"MONTHLY ATTENDANCE — {month}")
        print(f"  {'Emp ID':<9}{'Name':<22}{'WD':>4}{'P':>5}{'HD':>4}{'A':>4}{'L':>4}{'LOP':>6}{'Late':>6}{'%':>7}")
        line()
        for e in self.em.list():
            s = self.am.monthly_summary(e.emp_id, month)
            print(f"  {e.emp_id:<9}{e.name[:21]:<22}{s['working_days']:>4}{s['present']:>5}{s['half_day']:>4}"
                  f"{s['absent']:>4}{s['leave_paid'] + s['leave_unpaid']:>4}{s['lop_days']:>6g}{s['late']:>6}"
                  f"{s['attendance_percent']:>7}")

    # ------------------------------------------------------------- leave
    def leave_menu(self) -> None:
        names = lambda: {e.emp_id: e.name for e in self.em.list(None)}  # noqa: E731
        self._submenu("LEAVE MANAGEMENT", [
            ("Pending requests (approve / reject)", self.leave_approvals),
            ("All leave records", lambda: print_leaves(self.lm.list(), names())),
            ("Employee leave balance", self.leave_balance),
            ("Who is on leave today", lambda: print_leaves(self.lm.on_leave(), names())),
            ("Apply leave on behalf of an employee", self.apply_for),
            ("Cancel a leave", lambda: (self.lm.cancel(ask("Leave ID").upper()), print("  ✔ Cancelled.")))])

    def leave_approvals(self) -> None:
        names = {e.emp_id: e.name for e in self.em.list(None)}
        while True:
            pending = self.lm.pending()
            header(f"PENDING LEAVE REQUESTS ({len(pending)})")
            if not pending:
                print("  Nothing pending.")
                return
            for i, l in enumerate(pending, 1):
                bal = self.lm.balance(l["emp_id"], int(l["start"][:4]))[l["leave_type"]]
                avail = "∞" if bal["available"] is None else f"{bal['available'] + l['days']:g}"
                print(f"  {i:>2}. {l['emp_id']} {names.get(l['emp_id'], '')[:18]:<19}{l['leave_type']:<12}"
                      f"{l['start']} → {l['end']} ({l['days']}d)  balance {avail}")
                print(f"      Reason: {l['reason']}")
            n = ask("Select number (blank = back)")
            if not (n.isdigit() and 1 <= int(n) <= len(pending)):
                return
            l = pending[int(n) - 1]
            action = choose("Decision", ["Approve", "Reject", "Skip"])
            try:
                if action == "Approve":
                    self.lm.approve(l["leave_id"], self.user["username"], ask("Remarks (optional)"))
                    print("  ✔ Approved; attendance updated.")
                elif action == "Reject":
                    self.lm.reject(l["leave_id"], self.user["username"], ask("Reason for rejection"))
                    print("  ✔ Rejected.")
            except EMSError as exc:
                print(f"  ✖ {exc}")

    def leave_balance(self) -> None:
        e = self.pick_employee()
        year = ask("Year", str(date.today().year))
        header(f"LEAVE BALANCE — {e.emp_id} {e.name} — {year}")
        print_balance(self.lm.balance(e.emp_id, int(year)))
        print()
        print_leaves(self.lm.list(e.emp_id, year=int(year)))

    def apply_for(self) -> None:
        e = self.pick_employee()
        l = self.lm.apply(e.emp_id, choose("Leave type", list(LEAVE_TYPES)), ask("From YYYY-MM-DD"),
                          ask("To YYYY-MM-DD"), ask("Reason"))
        if confirm("Approve immediately?"):
            self.lm.approve(l["leave_id"], self.user["username"])
        print(f"  ✔ Leave {l['leave_id']} recorded.")

    # ----------------------------------------------------------- payroll
    def payroll_menu(self) -> None:
        self._submenu("PAYROLL", [
            ("Salary calculator", self.salary_calculator), ("Generate monthly payroll", self.generate_payroll),
            ("View payroll register", self.view_register), ("View / download a payslip", self.view_payslip),
            ("Mark payroll as paid", self.mark_paid), ("Highest salary report", self.highest_salary),
            ("Department salary summary", self.dept_salary)])

    def generate_payroll(self) -> None:
        month = ask("Month YYYY-MM", last_month())
        if month == this_month():
            print("  ⚠ This month is still in progress — only attendance up to today will be used.")
        strict = confirm("Treat unmarked working days as absent (LOP)?")
        r = self.pm.generate(month, unmarked_as_absent=strict)
        print(f"  ✔ {r['generated']} payslip(s) generated for {month}; total net pay {money(r['total_net'])}.")
        if r["skipped_paid"]:
            print(f"    {r['skipped_paid']} already-paid payslip(s) were left unchanged.")

    def view_register(self) -> None:
        month = ask("Month YYYY-MM", last_month())
        slips = self.pm.list(month)
        if not slips:
            print("  No payroll for this month. Generate it first.")
            return
        header(f"PAYROLL REGISTER — {month}")
        print(f"  {'Emp ID':<9}{'Name':<20}{'Gross':>12}{'LOP':>6}{'Deductions':>13}{'Net Pay':>13}  Status")
        line()
        for p in slips:
            print(f"  {p['emp_id']:<9}{p['name'][:19]:<20}{money(p['gross']):>12}{p['lop_days']:>6g}"
                  f"{money(p['total_deductions']):>13}{money(p['net']):>13}  {p['status']}")
        t = self.pm.register_totals(month)
        line()
        print(f"  {'TOTAL':<29}{money(t['gross']):>12}{'':>6}{money(t['total_deductions']):>13}{money(t['net']):>13}")
        print(f"  {t['paid']} of {t['payslips']} paid.")

    def view_payslip(self) -> None:
        e = self.pick_employee(True)
        month = ask("Month YYYY-MM", last_month())
        p = self.pm.get(e.emp_id, month)
        header(f"PAYSLIP — {e.emp_id} {e.name} — {month}")
        print_salary(p)
        if confirm("\n  Save as PDF?"):
            print(f"  ✔ Saved: {self.reports.payslip_pdf(e.emp_id, month)}")

    def mark_paid(self) -> None:
        month = ask("Month YYYY-MM", last_month())
        ids = ask("Employee IDs separated by commas (blank = all unpaid)")
        n = self.pm.mark_paid(month, [i.strip() for i in ids.split(",") if i.strip()] or None)
        print(f"  ✔ {n} payslip(s) marked as paid.")

    def highest_salary(self) -> None:
        dept = choose("Department (blank = all)", self.dm.names(), allow_blank=True) or None
        n = ask("How many", "10")
        header("HIGHEST SALARIES" + (f" — {dept}" if dept else ""))
        print(f"  {'#':<4}{'Emp ID':<9}{'Name':<22}{'Designation':<24}{'Gross/month':>14}{'Annual CTC':>16}")
        line()
        for i, r in enumerate(self.pm.highest_salaries(int(n) if n.isdigit() else 10, dept), 1):
            e = r["employee"]
            print(f"  {i:<4}{e.emp_id:<9}{e.name[:21]:<22}{e.designation[:23]:<24}{money(r['gross']):>14}"
                  f"{money(r['annual_ctc']):>16}")

    def dept_salary(self) -> None:
        header("DEPARTMENT SALARY SUMMARY (monthly gross)")
        print(f"  {'Department':<22}{'Staff':>6}{'Total':>15}{'Average':>13}{'Highest':>13}{'Lowest':>13}")
        line()
        for d in self.pm.department_salary_summary():
            print(f"  {d['department'][:21]:<22}{d['employees']:>6}{money(d['total_gross']):>15}"
                  f"{money(d['average_gross']):>13}{money(d['highest']):>13}{money(d['lowest']):>13}")

    # ----------------------------------------------------------- reports
    def report_menu(self) -> None:
        saved = lambda p: print(f"  ✔ Saved: {p}")  # noqa: E731
        self._submenu("REPORTS", [
            ("Employee list (CSV)", lambda: saved(self.reports.employees_csv(
                None if confirm("Include exited employees?") else "ACTIVE"))),
            ("Employee directory with department summary (PDF)", lambda: saved(self.reports.employees_pdf())),
            ("Highest salary report (CSV)", lambda: saved(self.reports.highest_salary_csv(
                int(ask("How many", "10") or 10)))),
            ("Monthly attendance report (CSV)", lambda: saved(self.reports.attendance_csv(ask("Month YYYY-MM", this_month())))),
            ("Leave report (CSV)", lambda: saved(self.reports.leaves_csv(int(ask("Year", str(date.today().year)))))),
            ("Payroll register (CSV)", lambda: saved(self.reports.payroll_csv(ask("Month YYYY-MM", last_month())))),
            ("Payroll register (PDF)", lambda: saved(self.reports.payroll_register_pdf(ask("Month YYYY-MM", last_month())))),
            ("Company summary", self.company_summary)])

    def company_summary(self) -> None:
        s = self.em.summary()
        header("COMPANY SUMMARY")
        print(f"  Active employees : {s['active']}     Exited: {s['exited']}")
        print(f"  Average experience: {s['avg_experience']} years")
        print(f"  By type          : {', '.join(f'{k} {v}' for k, v in s['by_type'].items())}")
        print(f"  By gender        : {', '.join(f'{k} {v}' for k, v in s['by_gender'].items())}")
        print("\n  Headcount by department:")
        peak = max(s["by_department"].values() or [1]) or 1
        for d, n in s["by_department"].items():
            print(f"    {d:<24}{n:>4}  {'█' * round(n / peak * 30)}")
        print(f"\n  On leave today: {len(self.lm.on_leave())}    Pending leave requests: {len(self.lm.pending())}")

    # ------------------------------------------------------------ backup
    def backup_menu(self) -> None:
        def restore():
            backups = self.backup.list_backups()
            if not backups:
                print("  No backups.")
                return
            for i, b in enumerate(backups, 1):
                print(f"  {i:>2}. {b.name}")
            n = ask("Backup number to restore")
            if n.isdigit() and 1 <= int(n) <= len(backups) and confirm("Replace ALL current data with this backup?"):
                safety = self.backup.restore(backups[int(n) - 1])
                print(f"  ✔ Restored. Previous data saved as {safety.name}. Please log in again.")
                self.user = None
        self._submenu("BACKUP & RESTORE", [
            ("Create backup", lambda: print(f"  ✔ Backup created: {self.backup.create_backup().name}")),
            ("List backups", lambda: print("\n".join(f"  {b.name}  ({b.stat().st_size / 1024:.1f} KB)"
                                                     for b in self.backup.list_backups()) or "  No backups.")),
            ("Restore backup", restore)])

    # ----------------------------------------------------------- accounts
    def account_menu(self) -> None:
        def list_accounts():
            for u in sorted(self.db.all("users"), key=lambda u: (u["role"], u["username"])):
                state = "active" if u["active"] else "disabled"
                if u["failed_attempts"] >= 5:
                    state = "LOCKED"
                print(f"  {u['username']:<14}{u['role']:<10}{state:<10}last login {(u['last_login'] or '-').replace('T', ' ')}")

        def reset():
            name = ask("Username / employee ID")
            print(f"  ✔ Temporary password for {name.upper()}: {self.auth.reset_password(name)}  (account unlocked)")

        def new_admin():
            pw = getpass.getpass("  Password: ")
            if pw != getpass.getpass("  Confirm password: "):
                raise EMSError("Passwords do not match.")
            print(f"  ✔ Admin '{self.auth.create_admin(ask('Username'), pw)['username']}' created.")
        self._submenu("USER ACCOUNTS", [("List accounts", list_accounts),
                                        ("Reset password / unlock account", reset), ("Create admin", new_admin)])


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except EMSError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
