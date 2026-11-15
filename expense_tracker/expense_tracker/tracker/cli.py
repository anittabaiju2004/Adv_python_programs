"""Menu-driven command-line interface."""
from __future__ import annotations

import getpass
import sys
from datetime import date

from . import config
from .admin import AdminManager
from .auth import AuthManager
from .backup import BackupManager
from .bills import BillManager, RECURRENCE
from .budget import BudgetManager, OVERALL
from .database import JSONDatabase
from .exceptions import TrackerError
from .models import User
from .reports import ReportGenerator
from .savings import SavingsManager
from .transactions import ExpenseManager, IncomeManager

C = config.CURRENCY


# ======================================================================= ui
def line(char: str = "-", n: int = 64) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(f"  {title}")
    line("=")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def ask_float(prompt: str, optional: bool = False) -> float | None:
    while True:
        raw = ask(prompt)
        if optional and raw == "":
            return None
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a number.")


def choose(prompt: str, options: list[str], allow_blank: bool = False) -> str:
    for i, opt in enumerate(options, 1):
        print(f"   {i}. {opt}")
    while True:
        raw = ask(prompt)
        if allow_blank and raw == "":
            return ""
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        for opt in options:
            if opt.lower() == raw.lower():
                return opt
        print("  Invalid choice.")


def confirm(prompt: str) -> bool:
    return ask(f"{prompt} (y/n)").lower() in ("y", "yes")


def pause() -> None:
    input("\nPress Enter to continue...")


def menu(title: str, options: list[str]) -> str:
    header(title)
    for i, opt in enumerate(options, 1):
        print(f"  {i:>2}. {opt}")
    back = {"WELCOME": "Exit", "MAIN MENU": "Logout"}.get(title, "Back")
    print(f"   0. {back}")
    return ask("Select option")


def money(v: float) -> str:
    return f"{C}{v:,.2f}"


def bar(pct: float, width: int = 20) -> str:
    filled = int(min(pct, 100) / 100 * width)
    return "[" + "#" * filled + "." * (width - filled) + f"] {pct:5.1f}%"


def print_transactions(items, show_mode: bool = False) -> None:
    if not items:
        print("  No records found.")
        return
    hdr = f"  {'ID':<9}{'Date':<12}{'Category':<14}{'Amount':>12}  "
    hdr += f"{'Mode':<12}" if show_mode else ""
    print(hdr + "Description")
    line()
    for t in items:
        row = f"  {t.id:<9}{t.date:<12}{t.category:<14}{money(t.amount):>12}  "
        row += f"{getattr(t, 'payment_mode', ''):<12}" if show_mode else ""
        print(row + (t.description or "-")[:30])
    line()
    print(f"  {len(items)} record(s), total {money(sum(t.amount for t in items))}")


def this_month() -> str:
    return date.today().strftime("%Y-%m")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or config.DATA_DIR
        self.db = JSONDatabase(self.data_dir)
        self.auth = AuthManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or config.BACKUP_DIR)
        self.report_dir = report_dir or config.REPORT_DIR
        self.user: User | None = None

    # ----------------------------------------------------------- lifecycle
    def run(self) -> None:
        print("\n  ADVANCED PERSONAL EXPENSE TRACKER SYSTEM")
        while True:
            choice = menu("WELCOME", ["Login", "Register"]).strip()
            try:
                if choice == "1":
                    self.login()
                elif choice == "2":
                    self.register()
                elif choice == "0":
                    print("Goodbye!")
                    return
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            if self.user:
                self.session()

    def login(self) -> None:
        username = ask("Username")
        password = getpass.getpass("Password: ")
        self.user = self.auth.login(username, password)
        print(f"\n  Welcome, {self.user.full_name or self.user.username}!")
        self.show_alerts()

    def register(self) -> None:
        header("REGISTER")
        username = ask("Choose a username")
        full_name = ask("Full name (optional)")
        password = getpass.getpass("Password (min 6 chars, letters + digits): ")
        if password != getpass.getpass("Confirm password: "):
            print("  Passwords do not match.")
            return
        self.auth.register(username, password, full_name)
        print("  Registration successful. Please log in.")

    def show_alerts(self) -> None:
        msgs = BudgetManager(self.db, self.user.username).alerts(this_month())
        msgs += BillManager(self.db, self.user.username).reminders()
        if msgs:
            header("ALERTS")
            for m in msgs:
                print("  " + m)

    def session(self) -> None:
        options = ["Dashboard", "Expenses", "Income", "Budgets", "Savings Goals",
                   "Bill Reminders", "Reports & Analytics", "Backup & Restore", "Change Password"]
        if self.user.is_admin:
            options.append("Admin Panel")
        handlers = [self.dashboard, self.expense_menu, self.income_menu, self.budget_menu,
                    self.savings_menu, self.bill_menu, self.report_menu, self.backup_menu,
                    self.change_password, self.admin_menu]
        while self.user:
            choice = menu("MAIN MENU", options)
            if choice == "0":
                print(f"  Logged out {self.user.username}.")
                self.user = None
                return
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                self.safe(handlers[int(choice) - 1])

    @staticmethod
    def safe(fn, *args) -> None:
        """Run a handler, reporting errors instead of crashing."""
        try:
            fn(*args)
        except TrackerError as exc:
            print(f"\n  Error: {exc}")
            pause()
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled.")

    # ----------------------------------------------------------- dashboard
    def dashboard(self) -> None:
        rg = ReportGenerator(self.db, self.user.username, self.report_dir)
        s = rg.monthly_summary(this_month())
        header(f"DASHBOARD — {s['period']}")
        print(f"  Income       : {money(s['income'])}")
        print(f"  Expenses     : {money(s['expense'])}")
        print(f"  Net          : {money(s['net'])}   (savings rate {s['savings_rate']}%)")
        print(f"  Transactions : {s['transactions']}")
        if s["by_category"]:
            print("\n  Top categories:")
            for cat, amt in list(s["by_category"].items())[:5]:
                print(f"    {cat:<14}{money(amt):>12}")
        self.show_alerts()
        recent = ExpenseManager(self.db, self.user.username).list()[:5]
        if recent:
            print("\n  Recent expenses:")
            print_transactions(recent)
        pause()

    # ------------------------------------------------------- transactions
    def _txn_menu(self, mgr, label: str, cats: list[str], is_expense: bool) -> None:
        while True:
            choice = menu(f"{label.upper()} MANAGEMENT",
                          [f"Add {label}", f"View all {label.lower()}s", f"Update {label.lower()}",
                           f"Delete {label.lower()}", f"Search {label.lower()}s", "Filter by date range"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    amount = ask_float("Amount")
                    cat = choose("Category" if is_expense else "Source", cats)
                    d = ask("Date YYYY-MM-DD (blank = today)")
                    desc = ask("Description")
                    if is_expense:
                        mode = choose("Payment mode", config.PAYMENT_MODES)
                        t = mgr.add(amount, cat, d, desc, mode)
                        alerts = BudgetManager(self.db, self.user.username).alerts(t.date[:7])
                    else:
                        t = mgr.add(amount, cat, d, desc)
                        alerts = []
                    print(f"  Saved with id {t.id}.")
                    for a in alerts:
                        print("  " + a)
                elif choice == "2":
                    print_transactions(mgr.list(), is_expense)
                elif choice == "3":
                    t = mgr.get(ask("ID to update"))
                    print("  Leave blank to keep the current value.")
                    changes = {
                        "amount": ask("Amount", str(t.amount)),
                        "category": ask("Category" if is_expense else "Source", t.category),
                        "date": ask("Date", t.date),
                        "description": ask("Description", t.description),
                    }
                    if is_expense:
                        changes["payment_mode"] = ask("Payment mode", t.payment_mode)
                    mgr.update(t.id, **changes)
                    print("  Updated.")
                elif choice == "4":
                    t = mgr.get(ask("ID to delete"))
                    if confirm(f"Delete {money(t.amount)} {t.category} on {t.date}?"):
                        mgr.delete(t.id)
                        print("  Deleted.")
                elif choice == "5":
                    kw = ask("Keyword (blank = any)")
                    cat = ask("Category (blank = any)") or None
                    lo = ask_float("Min amount (blank = none)", optional=True)
                    hi = ask_float("Max amount (blank = none)", optional=True)
                    print_transactions(mgr.search(kw, lo, hi, category=cat), is_expense)
                elif choice == "6":
                    start = ask("Start date YYYY-MM-DD") or None
                    end = ask("End date YYYY-MM-DD") or None
                    print_transactions(mgr.list(start, end), is_expense)
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()

    def expense_menu(self) -> None:
        self._txn_menu(ExpenseManager(self.db, self.user.username), "Expense",
                       config.EXPENSE_CATEGORIES, True)

    def income_menu(self) -> None:
        self._txn_menu(IncomeManager(self.db, self.user.username), "Income",
                       config.INCOME_SOURCES, False)

    # -------------------------------------------------------------- budget
    def budget_menu(self) -> None:
        bm = BudgetManager(self.db, self.user.username)
        while True:
            choice = menu("BUDGET MANAGEMENT", ["Set / update budget", "Budget status",
                                                "List all budgets", "Delete budget"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    month = ask("Month YYYY-MM", this_month())
                    cat = choose("Category", [OVERALL] + config.EXPENSE_CATEGORIES)
                    b = bm.set_budget(month, ask_float("Monthly limit"), cat)
                    print(f"  Budget set: {b.category} {b.month} = {money(b.limit)}")
                elif choice == "2":
                    month = ask("Month YYYY-MM", this_month())
                    statuses = bm.status(month)
                    if not statuses:
                        print("  No budgets for that month.")
                    for s in statuses:
                        print(f"  {s.budget.category:<14}{money(s.spent):>12} / {money(s.budget.limit):<12}"
                              f"{bar(s.percent)}  {s.level}")
                    for a in bm.alerts(month):
                        print("  " + a)
                elif choice == "3":
                    for b in bm.list_budgets():
                        print(f"  {b.id:<9}{b.month:<9}{b.category:<14}{money(b.limit):>12}")
                elif choice == "4":
                    bm.delete_budget(ask("Budget ID"))
                    print("  Deleted.")
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()

    # ------------------------------------------------------------- savings
    def savings_menu(self) -> None:
        sm = SavingsManager(self.db, self.user.username)
        while True:
            choice = menu("SAVINGS GOALS", ["Create goal", "View goals", "Add money to goal",
                                            "Withdraw from goal", "Delete goal"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    g = sm.create_goal(ask("Goal name"), ask_float("Target amount"),
                                       ask("Deadline YYYY-MM-DD (optional)") or None,
                                       ask_float("Initial amount (blank = 0)", optional=True) or 0)
                    print(f"  Goal created with id {g.id}.")
                elif choice == "2":
                    goals = sm.list_goals()
                    if not goals:
                        print("  No savings goals yet.")
                    for g in goals:
                        status = "DONE" if g.completed else f"{money(g.remaining)} to go"
                        print(f"  {g.id:<9}{g.name:<20}{money(g.saved_amount):>12} / {money(g.target_amount):<12}"
                              f"{bar(g.progress)}  {status}")
                        need = sm.monthly_required(g)
                        if need:
                            print(f"{'':11}Deadline {g.deadline}: save {money(need)}/month")
                elif choice == "3":
                    g = sm.deposit(ask("Goal ID"), ask_float("Amount"))
                    print(f"  Saved {money(g.saved_amount)} ({g.progress:.1f}%).")
                    if g.completed:
                        print("  Congratulations, goal reached!")
                elif choice == "4":
                    g = sm.withdraw(ask("Goal ID"), ask_float("Amount"))
                    print(f"  Remaining balance {money(g.saved_amount)}.")
                elif choice == "5":
                    gid = ask("Goal ID")
                    if confirm("Delete this goal?"):
                        sm.delete_goal(gid)
                        print("  Deleted.")
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()

    # --------------------------------------------------------------- bills
    def bill_menu(self) -> None:
        bmgr = BillManager(self.db, self.user.username)
        while True:
            choice = menu("BILL REMINDERS", ["Add bill", "View unpaid bills", "Upcoming & overdue",
                                             "Mark bill as paid", "Delete bill", "View all bills"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    b = bmgr.add_bill(ask("Bill name"), ask_float("Amount"),
                                      ask("Due date YYYY-MM-DD"), choose("Recurrence", RECURRENCE))
                    print(f"  Bill added with id {b.id}.")
                elif choice in ("2", "6"):
                    bills = bmgr.list_bills(include_paid=(choice == "6"))
                    if not bills:
                        print("  No bills.")
                    for b in bills:
                        print(f"  {b.id:<9}{b.name:<20}{money(b.amount):>12}  due {b.due_date}  "
                              f"{b.recurring:<8}{'PAID' if b.paid else 'UNPAID'}")
                elif choice == "3":
                    msgs = bmgr.reminders()
                    print("\n".join("  " + m for m in msgs) if msgs else "  Nothing due soon.")
                elif choice == "4":
                    nxt = bmgr.mark_paid(ask("Bill ID"), confirm("Record as an expense?"))
                    print("  Marked as paid.")
                    if nxt:
                        print(f"  Next {nxt.recurring} bill scheduled for {nxt.due_date}.")
                elif choice == "5":
                    bmgr.delete_bill(ask("Bill ID"))
                    print("  Deleted.")
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()

    # ------------------------------------------------------------- reports
    def report_menu(self) -> None:
        rg = ReportGenerator(self.db, self.user.username, self.report_dir)
        while True:
            choice = menu("REPORTS & ANALYTICS", [
                "Monthly summary", "Yearly analytics", "Category-wise report",
                "Export transactions to CSV", "Export PDF report",
                "Chart: category pie", "Chart: monthly income vs expense", "Chart: budget utilisation"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    s = rg.monthly_summary(ask("Month YYYY-MM", this_month()))
                    header(f"MONTHLY SUMMARY — {s['period']}")
                    print(f"  Income {money(s['income'])} | Expense {money(s['expense'])} | "
                          f"Net {money(s['net'])} | Savings rate {s['savings_rate']}%")
                    print(f"  Avg spend per active day: {money(s['avg_per_active_day'])}")
                    if s["largest"]:
                        lg = s["largest"]
                        print(f"  Largest expense: {money(lg.amount)} ({lg.category}, {lg.date})")
                elif choice == "2":
                    s = rg.yearly_summary(ask("Year YYYY", str(date.today().year)))
                    header(f"YEARLY ANALYTICS — {s['period']}")
                    print(f"  Income {money(s['income'])} | Expense {money(s['expense'])} | "
                          f"Net {money(s['net'])} | Savings rate {s['savings_rate']}%")
                    print(f"  Avg monthly expense: {money(s['avg_monthly_expense'])}; "
                          f"highest month: {s['highest_spending_month'] or '-'}\n")
                    peak = max(s["monthly_expense"].values()) or 1
                    for m, v in s["monthly_expense"].items():
                        print(f"  {m}  {money(v):>12}  {'#' * int(v / peak * 30)}")
                elif choice == "3":
                    period = ask("Month YYYY-MM or year YYYY", this_month())
                    data = rg.expenses.by_category(**({"month": period} if "-" in period else {"year": period}))
                    total = sum(data.values()) or 1
                    if not data:
                        print("  No data.")
                    for cat, amt in data.items():
                        print(f"  {cat:<14}{money(amt):>12}  {bar(amt / total * 100)}")
                elif choice == "4":
                    p = rg.export_csv(ask("Start date (optional)") or None, ask("End date (optional)") or None)
                    print(f"  CSV saved to {p}")
                elif choice == "5":
                    period = ask("Month YYYY-MM or year YYYY", this_month())
                    p = rg.export_pdf(**({"month": period} if "-" in period else {"year": period}))
                    print(f"  PDF saved to {p}")
                elif choice == "6":
                    period = ask("Month YYYY-MM or year YYYY", this_month())
                    p = rg.chart_category_pie(**({"month": period} if "-" in period else {"year": period}))
                    print(f"  Chart saved to {p}")
                elif choice == "7":
                    print(f"  Chart saved to {rg.chart_monthly_trend(ask('Year YYYY', str(date.today().year)))}")
                elif choice == "8":
                    print(f"  Chart saved to {rg.chart_budget(ask('Month YYYY-MM', this_month()))}")
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()

    # -------------------------------------------------------------- backup
    def backup_menu(self) -> None:
        if not self.user.is_admin:
            print("\n  Backup covers all users' data. Creating a backup is allowed;"
                  " restore requires an admin.")
        while True:
            choice = menu("BACKUP & RESTORE", ["Create backup", "List backups", "Restore backup", "Delete backup"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print(f"  Backup created: {self.backup.create_backup().name}")
                elif choice == "2":
                    backups = self.backup.list_backups()
                    print("\n".join(f"  {i}. {b.name}  ({b.stat().st_size / 1024:.1f} KB)"
                                    for i, b in enumerate(backups, 1)) or "  No backups.")
                elif choice in ("3", "4"):
                    if not self.user.is_admin:
                        print("  Only an admin can restore or delete backups.")
                    else:
                        backups = self.backup.list_backups()
                        if not backups:
                            print("  No backups.")
                        else:
                            pick = choose("Backup number", [b.name for b in backups])
                            target = self.backup.backup_dir / pick
                            if choice == "3" and confirm("Current data will be replaced. Continue?"):
                                safety = self.backup.restore(target)
                                print(f"  Restored. Previous data saved as {safety.name}.")
                                self.user = None
                                print("  Please log in again.")
                                return
                            if choice == "4" and confirm(f"Delete {pick}?"):
                                self.backup.delete_backup(target)
                                print("  Deleted.")
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()

    def change_password(self) -> None:
        old = getpass.getpass("Current password: ")
        new = getpass.getpass("New password: ")
        if new != getpass.getpass("Confirm new password: "):
            print("  Passwords do not match.")
        else:
            self.auth.change_password(self.user.username, old, new)
            print("  Password changed.")
        pause()

    # --------------------------------------------------------------- admin
    def admin_menu(self) -> None:
        am = AdminManager(self.db, self.user)
        while True:
            choice = menu("ADMIN PANEL", ["List users", "System statistics", "Create user",
                                          "Activate / deactivate user", "Change user role",
                                          "Reset user password", "Delete user"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print(f"  {'Username':<16}{'Role':<8}{'Active':<8}{'Last login':<22}Name")
                    line()
                    for u in am.list_users():
                        print(f"  {u.username:<16}{u.role:<8}{'yes' if u.active else 'no':<8}"
                              f"{u.last_login or '-':<22}{u.full_name}")
                elif choice == "2":
                    s = am.system_stats()
                    for k, v in s.items():
                        if k != "per_user":
                            print(f"  {k.replace('_', ' ').title():<26}{v}")
                    print("\n  Per user:")
                    for name, d in s["per_user"].items():
                        print(f"    {name:<16}expenses {money(d['expenses']):>12}  income {money(d['incomes']):>12}"
                              f"  ({d['transactions']} txns)")
                elif choice == "3":
                    role = choose("Role", ["user", "admin"])
                    self.auth.register(ask("Username"), getpass.getpass("Password: "),
                                       ask("Full name"), role)
                    print("  User created.")
                elif choice == "4":
                    name = ask("Username")
                    am.set_active(name, confirm("Activate? (n = deactivate)"))
                    print("  Updated.")
                elif choice == "5":
                    am.set_role(ask("Username"), choose("New role", ["user", "admin"]))
                    print("  Updated.")
                elif choice == "6":
                    am.reset_password(ask("Username"), getpass.getpass("New password: "))
                    print("  Password reset.")
                elif choice == "7":
                    name = ask("Username")
                    if confirm(f"Permanently delete '{name}' and ALL their data?"):
                        removed = am.delete_user(name)
                        print(f"  Deleted. Records removed: {removed}")
                else:
                    continue
            except TrackerError as exc:
                print(f"\n  Error: {exc}")
            pause()


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        sys.exit(0)
    except TrackerError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
