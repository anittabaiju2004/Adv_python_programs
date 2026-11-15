"""atm.py — ATM Management System console application (entry point).

Run:  python atm.py
"""
from __future__ import annotations

import getpass
import sys

from account import AccountManager, FixedDepositManager, LoanManager, fd_rate_for
from admin import AdminManager
from auth import AuthManager
from backup import BackupManager
from database import JSONDatabase
from report import ReportGenerator
from transaction import CREDIT_TYPES, TYPE_LABELS, TransactionManager
from utils import (ACCOUNT_TYPES, ATMError, AccountFrozenError, BACKUP_DIR, BANK_NAME, DATA_DIR,
                   FD_RATES, LOAN_TYPES, REPORT_DIR, mask_account, money, validate_amount)

W = 66


# ====================================================================== ui
def line(ch: str = "-") -> None:
    print(ch * W)


def header(title: str) -> None:
    print()
    line("=")
    print(f"{title:^{W}}")
    line("=")


def ask(prompt: str, default: str | None = None) -> str:
    v = input(f"  {prompt}{f' [{default}]' if default else ''}: ").strip()
    return v or (default or "")


def ask_pin(prompt: str = "Enter PIN") -> str:
    return getpass.getpass(f"  {prompt}: ").strip()


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


def choose(prompt: str, options) -> str:
    options = list(options)
    for i, o in enumerate(options, 1):
        print(f"     {i}. {o}")
    while True:
        v = ask(prompt)
        if v.isdigit() and 1 <= int(v) <= len(options):
            return options[int(v) - 1]
        if v in options:
            return v
        print("  Invalid choice.")


def print_txns(txns: list[dict]) -> None:
    if not txns:
        print("  No transactions found.")
        return
    print(f"  {'Date/Time':<17}{'Type':<16}{'Amount':>14}{'Balance':>15}  Details")
    line()
    for t in txns:
        sign = "+" if t["type"] in CREDIT_TYPES else "-"
        print(f"  {t['timestamp'][:16]:<17}{TYPE_LABELS.get(t['type'], t['type']):<16}"
              f"{sign + money(t['amount']):>14}{money(t['balance_after']):>15}  {t['description'][:28]}")
    line()


def print_customers(customers: list[dict]) -> None:
    if not customers:
        print("  No customers found.")
        return
    print(f"  {'Account No':<14}{'Name':<20}{'Phone':<12}{'Type':<9}{'Balance':>13}  Status")
    line()
    for c in customers:
        print(f"  {c['account_no']:<14}{c['name'][:19]:<20}{c['phone']:<12}{c['account_type']:<9}"
              f"{money(c['balance']):>13}  {c['status']}")
    line()
    print(f"  {len(customers)} customer(s)")


# ===================================================================== app
class ATMApp:
    def __init__(self, data_dir=DATA_DIR, backup_dir=BACKUP_DIR, report_dir=REPORT_DIR):
        self.db = JSONDatabase(data_dir)          # automatic data loading
        self.auth = AuthManager(self.db)
        self.accounts = AccountManager(self.db, self.auth)
        self.txn = TransactionManager(self.db, self.auth)
        self.fds = FixedDepositManager(self.db, self.auth)
        self.loans = LoanManager(self.db, self.auth)
        self.reports = ReportGenerator(self.db, report_dir)
        self.backup = BackupManager(data_dir, backup_dir)
        self.account_no: str | None = None

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(f"WELCOME TO {BANK_NAME.upper()}",
                          ["Customer Login", "Open New Account", "Admin Login", "Interest Calculator"], "Exit")
            try:
                if choice == "1":
                    self.customer_login()
                elif choice == "2":
                    self.register()
                elif choice == "3":
                    self.admin_login()
                elif choice == "4":
                    self.interest_calculator()
                elif choice == "0":
                    print("\n  Thank you for using " + BANK_NAME + ". Goodbye!\n")
                    return
            except ATMError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    # ------------------------------------------------------- registration
    def register(self) -> None:
        header("OPEN NEW ACCOUNT")
        name = ask("Full name")
        phone = ask("Mobile number")
        email = ask("Email address")
        address = ask("Address (optional)")
        acc_type = choose("Account type", ACCOUNT_TYPES)
        deposit = ask("Opening deposit", "500")
        print("  Create a 4-digit PIN (avoid 1111, 1234 etc.)")
        pin, pin2 = ask_pin("New PIN"), ask_pin("Confirm PIN")
        c = self.accounts.register(name, phone, email, pin, pin2, acc_type, deposit, address)
        header("ACCOUNT CREATED SUCCESSFULLY")
        print(f"  Account Number : {c['account_no']}")
        print(f"  Name           : {c['name']}")
        print(f"  Account Type   : {c['account_type']}")
        print(f"  Balance        : {money(c['balance'])}")
        print("\n  Please note your account number — you need it to log in.")
        pause()

    # ------------------------------------------------------------ customer
    def customer_login(self) -> None:
        header("CUSTOMER LOGIN")
        acc = ask("Account number")
        c = self.auth.login(acc, ask_pin())
        self.account_no = c["account_no"]
        print(f"\n  Welcome, {c['name']}!  (A/c {mask_account(c['account_no'])})")
        self.customer_menu()

    def customer_menu(self) -> None:
        actions = [("Deposit Money", self.deposit), ("Withdraw Money", self.withdraw),
                   ("Transfer Money", self.transfer), ("Balance Inquiry", self.balance),
                   ("Mini Statement", self.mini_statement), ("Transaction History", self.history),
                   ("Fixed Deposits", self.fd_menu), ("Loans", self.loan_menu),
                   ("Interest Calculator", self.interest_calculator),
                   ("Download PDF Statement", self.pdf_statement), ("Change PIN", self.change_pin)]
        while self.account_no:
            c = self.accounts.get(self.account_no)
            choice = menu(f"{c['name'].upper()}  |  A/c {mask_account(c['account_no'])}",
                          [a[0] for a in actions], "Logout")
            if choice == "0":
                print("  Logged out successfully.")
                self.account_no = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(actions)):
                continue
            handler = actions[int(choice) - 1][1]
            try:
                handler()
                if handler in (self.fd_menu, self.loan_menu):
                    continue                    # submenus pause on their own
            except AccountFrozenError as exc:
                print(f"\n  ✖ {exc}\n  You have been logged out.")
                self.account_no = None
                pause()
                return
            except ATMError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def _show_receipt(self, txn: dict) -> None:
        if confirm("Print receipt?"):
            print()
            for row in self.txn.receipt(txn).splitlines():
                print("  " + row)

    def deposit(self) -> None:
        header("DEPOSIT")
        txn = self.txn.deposit(self.account_no, ask("Amount to deposit"))
        print(f"  ✔ {money(txn['amount'])} deposited. New balance: {money(txn['balance_after'])}")
        self._show_receipt(txn)

    def withdraw(self) -> None:
        header("CASH WITHDRAWAL")
        print("  Quick cash: 1) 500  2) 1000  3) 2000  4) 5000  5) 10000  or type an amount")
        v = ask("Amount")
        amount = {"1": 500, "2": 1000, "3": 2000, "4": 5000, "5": 10000}.get(v, v)
        txn = self.txn.withdraw(self.account_no, ask_pin(), amount)
        print(f"  ✔ Please collect your cash: {money(txn['amount'])}")
        print(f"    Remaining balance: {money(txn['balance_after'])}")
        self._show_receipt(txn)

    def transfer(self) -> None:
        header("FUND TRANSFER")
        to = ask("Receiver account number")
        receiver = self.accounts.get(to)
        print(f"  Receiver: {receiver['name']} ({mask_account(receiver['account_no'])})")
        amount = validate_amount(ask("Amount"))
        remarks = ask("Remarks (optional)")
        if not confirm(f"Transfer {money(amount)} to {receiver['name']}?"):
            print("  Transfer cancelled.")
            return
        out, _ = self.txn.transfer(self.account_no, ask_pin(), to, amount, remarks)
        print(f"  ✔ Transfer successful. Txn ID {out['txn_id']}")
        print(f"    Your balance: {money(out['balance_after'])}")
        self._show_receipt(out)

    def balance(self) -> None:
        header("BALANCE INQUIRY")
        b = self.txn.balance_inquiry(self.account_no, ask_pin())
        print(f"  Account          : {mask_account(b['account_no'])} ({b['account_type']})")
        print(f"  Ledger balance   : {money(b['balance'])}")
        print(f"  Available balance: {money(b['available'])}  (after minimum balance)")
        print(f"  Withdrawn today  : {money(b['withdrawn_today'])}")
        print(f"  As of            : {b['checked_at']}")

    def mini_statement(self) -> None:
        s = self.txn.mini_statement(self.account_no)
        header(f"MINI STATEMENT — {mask_account(s['account_no'])}")
        print_txns(s["transactions"])
        print(f"  Credits: {money(s['credits'])}   Debits: {money(s['debits'])}   "
              f"Current balance: {money(s['balance'])}")

    def history(self) -> None:
        header("TRANSACTION HISTORY")
        kind = choose("Show", ["All", "Deposit", "Withdrawal", "Transfer"])
        start = ask("From date YYYY-MM-DD (blank = beginning)") or None
        end = ask("To date YYYY-MM-DD (blank = today)") or None
        print_txns(self.txn.history(self.account_no, None if kind == "All" else kind, start, end))

    def pdf_statement(self) -> None:
        start = ask("From date YYYY-MM-DD (blank = all)") or None
        end = ask("To date YYYY-MM-DD (blank = today)") or None
        print(f"  ✔ Statement saved: {self.reports.account_statement_pdf(self.account_no, start, end)}")

    def change_pin(self) -> None:
        header("CHANGE PIN")
        self.auth.change_pin(self.account_no, ask_pin("Current PIN"), ask_pin("New PIN"), ask_pin("Confirm new PIN"))
        print("  ✔ PIN changed successfully.")

    def interest_calculator(self) -> None:
        header("SIMPLE INTEREST CALCULATOR")
        r = self.accounts.interest_calculator(ask("Principal amount"), ask("Annual interest rate (%)"),
                                              ask("Duration (years, e.g. 1.5)"))
        print(f"\n  Principal       : {money(r['principal'])}")
        print(f"  Rate / Duration : {r['rate']}% for {r['years']} year(s)")
        print(f"  Interest        : {money(r['interest'])}")
        print(f"  Maturity amount : {money(r['maturity_amount'])}")
        if not self.account_no:
            pause()

    # ------------------------------------------------------- fixed deposit
    def fd_menu(self) -> None:
        while True:
            choice = menu("FIXED DEPOSITS", ["Open new FD", "View my FDs", "Close FD"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print("  Interest rates:")
                    for lo, hi, rate in FD_RATES:
                        print(f"     {lo:>3}-{hi:<3} months : {rate}% p.a.")
                    amount = validate_amount(ask("Deposit amount"))
                    months = ask("Duration in months")
                    rate = fd_rate_for(int(months)) if months.isdigit() else None
                    if rate and confirm(f"Open FD of {money(amount)} for {months} months at {rate}%?"):
                        fd = self.fds.create(self.account_no, ask_pin(), amount, months)
                        print(f"  ✔ FD created. FD ID: {fd['fd_id']}")
                        print(f"    Matures on {fd['maturity_date']} for {money(fd['maturity_amount'])}")
                    elif not rate:
                        print("  Please enter the duration as a whole number of months.")
                elif choice == "2":
                    fds = self.fds.list(self.account_no)
                    if not fds:
                        print("  No fixed deposits.")
                    for f in fds:
                        print(f"  {f['fd_id']}  {money(f['principal']):>12} @ {f['rate']}%  {f['months']}m  "
                              f"matures {f['maturity_date']} → {money(f['maturity_amount'])}  [{f['status']}]")
                elif choice == "3":
                    fd_id = ask("FD ID").upper()
                    q = self.fds.closure_quote(self.account_no, fd_id)
                    if q["premature"]:
                        print(f"  ⚠ Premature closure: interest at {q['rate']}% for {q['days']} days.")
                    print(f"  You will receive {money(q['payout'])} (interest {money(q['interest'])}).")
                    if confirm("Close this FD?"):
                        self.fds.close(self.account_no, ask_pin(), fd_id)
                        print("  ✔ FD closed; amount credited to your account.")
                else:
                    continue
            except AccountFrozenError:
                raise
            except ATMError as exc:
                print(f"\n  ✖ {exc}")
            except ValueError:
                print("\n  ✖ Please enter valid numbers.")
            pause()

    # --------------------------------------------------------------- loans
    def loan_menu(self) -> None:
        while True:
            choice = menu("LOAN MANAGEMENT", ["Apply for loan", "View active loans", "Repay loan",
                                              "Loan history", "Close completed loans"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print("  Loan types:")
                    for t, r in LOAN_TYPES.items():
                        print(f"     {t:<10} {r}% p.a. (simple interest)")
                    q = self.loans.quote(choose("Loan type", LOAN_TYPES), ask("Loan amount"),
                                         ask("Tenure in months"))
                    print(f"\n  Principal {money(q['principal'])} | Interest {money(q['interest'])} | "
                          f"Total {money(q['total_payable'])}")
                    print(f"  Monthly EMI: {money(q['emi'])} for {q['months']} months")
                    if confirm("Confirm loan application?"):
                        loan = self.loans.apply(self.account_no, ask_pin(), q["loan_type"], q["principal"], q["months"])
                        print(f"  ✔ Loan approved. Loan ID {loan['loan_id']}. "
                              f"{money(loan['principal'])} credited to your account.")
                elif choice in ("2", "4"):
                    loans = self.loans.list(self.account_no, active_only=(choice == "2"))
                    if not loans:
                        print("  No loans.")
                    for l in loans:
                        print(f"  {l['loan_id']}  {l['loan_type']:<10}{money(l['principal']):>13}  "
                              f"EMI {money(l['emi'])}  paid {self.loans.emis_paid(l)}/{l['months']}  "
                              f"outstanding {money(l['outstanding'])}  [{l['status']}]")
                elif choice == "3":
                    loan_id = ask("Loan ID").upper()
                    loan = next((l for l in self.loans.list(self.account_no, True) if l["loan_id"] == loan_id), None)
                    if not loan:
                        print("  Active loan not found.")
                    else:
                        print(f"  Outstanding {money(loan['outstanding'])}; EMI {money(loan['emi'])}")
                        amt = ask("Repayment amount", f"{min(loan['emi'], loan['outstanding']):.2f}")
                        l = self.loans.repay(self.account_no, ask_pin(), loan_id, amt)
                        print(f"  ✔ Payment received. Outstanding: {money(l['outstanding'])}")
                        if l["status"] == "CLOSED":
                            print("  🎉 Loan fully repaid and closed.")
                elif choice == "5":
                    closed = self.loans.close_completed(self.account_no)
                    print(f"  {len(closed)} completed loan(s) closed." if closed else "  No completed loans to close.")
                else:
                    continue
            except AccountFrozenError:
                raise
            except ATMError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    # --------------------------------------------------------------- admin
    def admin_login(self) -> None:
        header("ADMIN LOGIN")
        admin = self.auth.admin_login(ask("Username"), getpass.getpass("  Password: "))
        print(f"\n  Welcome, administrator {admin['username']}.")
        self.admin_menu(AdminManager(self.db, admin["username"]))

    def admin_menu(self, am: AdminManager) -> None:
        while True:
            choice = menu("ADMINISTRATOR PANEL", [
                "View all customers", "Search customer", "Customer details", "Freeze account",
                "Unfreeze account", "Delete account", "Reports", "Backup database",
                "Restore database", "View backups", "Change admin password"], "Logout")
            if choice == "0":
                return
            try:
                if choice == "1":
                    print_customers(am.view_customers())
                elif choice == "2":
                    print_customers(am.search_customers(ask("Name / account no / phone / email")))
                elif choice == "3":
                    c = am.get(ask("Account number"))
                    for k in ("account_no", "name", "phone", "email", "address", "account_type",
                              "status", "frozen_reason", "created_at", "last_login"):
                        print(f"  {k.replace('_', ' ').title():<16}: {c.get(k) or '-'}")
                    print(f"  {'Balance':<16}: {money(c['balance'])}")
                    print(f"  {'Active FDs':<16}: {len(self.fds.list(c['account_no'], True))}")
                    print(f"  {'Active loans':<16}: {len(self.loans.list(c['account_no'], True))}")
                    print("\n  Recent transactions:")
                    print_txns(self.txn.history(c["account_no"])[:5])
                elif choice == "4":
                    acc = ask("Account number")
                    c = am.freeze(acc, ask("Reason", "Suspicious activity"))
                    print(f"  ✔ Account {c['account_no']} frozen.")
                elif choice == "5":
                    c = am.unfreeze(ask("Account number"))
                    print(f"  ✔ Account {c['account_no']} is active again (PIN attempts reset).")
                elif choice == "6":
                    acc = ask("Account number")
                    c = am.get(acc)
                    problems = am.delete_check(acc)
                    if problems:
                        print("  ✖ Cannot delete: " + "; ".join(problems))
                    elif confirm(f"Permanently delete {c['name']} ({c['account_no']}), balance {money(c['balance'])}?"):
                        self.backup.create_backup("pre_delete")
                        r = am.delete_account(acc)
                        print(f"  ✔ Deleted. Balance to refund to customer: {money(r['balance_to_refund'])}")
                        print("    (A backup was taken automatically before deletion.)")
                elif choice == "7":
                    self.report_menu()
                    continue
                elif choice == "8":
                    print(f"  ✔ Backup created: {self.backup.create_backup().name}")
                elif choice in ("9", "10"):
                    backups = self.backup.list_backups()
                    if not backups:
                        print("  No backups available.")
                    else:
                        for i, b in enumerate(backups, 1):
                            print(f"  {i:>2}. {b['name']}  {b['created']}  {b['size_kb']} KB")
                        if choice == "9":
                            n = ask("Backup number to restore")
                            if n.isdigit() and 1 <= int(n) <= len(backups):
                                b = backups[int(n) - 1]
                                counts = self.backup.verify(b["path"])
                                print("  Contents: " + ", ".join(f"{k} ({v})" for k, v in counts.items()))
                                if confirm("Replace ALL current data with this backup?"):
                                    safety = self.backup.restore(b["path"])
                                    print(f"  ✔ Restored. Previous data saved as {safety.name}")
                elif choice == "11":
                    new = getpass.getpass("  New password: ")
                    if new != getpass.getpass("  Confirm new password: "):
                        print("  Passwords do not match.")
                    else:
                        self.auth.change_admin_password(am.admin, getpass.getpass("  Current password: "), new)
                        print("  ✔ Password changed.")
                else:
                    continue
            except ATMError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
            pause()

    def report_menu(self) -> None:
        while True:
            choice = menu("REPORTS", ["System summary", "Export customer report (CSV)",
                                      "Export transaction report (CSV)", "Account statement (PDF)"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    s = self.reports.system_summary()
                    for k, v in s.items():
                        if k == "by_type":
                            continue
                        val = money(v) if isinstance(v, float) else v
                        print(f"  {k.replace('_', ' ').title():<24}: {val}")
                    print("\n  Transactions by type:")
                    for t, d in s["by_type"].items():
                        print(f"    {t:<16}{d['count']:>6}  {money(d['amount']):>16}")
                elif choice == "2":
                    print(f"  ✔ Saved: {self.reports.export_customers_csv()}")
                elif choice == "3":
                    acc = ask("Account number (blank = all accounts)") or None
                    start = ask("From date (optional)") or None
                    end = ask("To date (optional)") or None
                    print(f"  ✔ Saved: {self.reports.export_transactions_csv(acc, start, end)}")
                elif choice == "4":
                    print(f"  ✔ Saved: {self.reports.account_statement_pdf(ask('Account number'))}")
                else:
                    continue
            except ATMError as exc:
                print(f"\n  ✖ {exc}")
            pause()


def main() -> None:
    try:
        ATMApp().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Session ended. Goodbye!")
    except ATMError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
