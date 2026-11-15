"""bank.py — Bank Management System console application (entry point).

Run:  python bank.py
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
from utils import (ACCOUNT_TYPES, AccountFrozenError, BACKUP_DIR, BANK_NAME, BRANCHES, BankError,
                   DATA_DIR, FD_RATES, LOAN_TYPES, MIN_OPENING_DEPOSIT, REPORT_DIR, SENIOR_CITIZEN_BONUS,
                   TRANSFER_MODES, mask_account, money, validate_amount)

W = 70


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
        for o in options:
            if v.lower() == str(o).lower():
                return o
        print("  Invalid choice.")


def print_txns(txns: list[dict], show_account: bool = False) -> None:
    if not txns:
        print("  No transactions found.")
        return
    acc = f"{'Account':<13}" if show_account else ""
    print(f"  {'Date/Time':<17}{acc}{'Type':<16}{'Amount':>14}{'Balance':>15}  Details")
    line()
    for t in txns:
        sign = "+" if t["type"] in CREDIT_TYPES else "-"
        acc = f"{t['account_no']:<13}" if show_account else ""
        print(f"  {t['timestamp'][:16]:<17}{acc}{TYPE_LABELS.get(t['type'], t['type']):<16}"
              f"{sign + money(t['amount']):>14}{money(t['balance_after']):>15}  {t['description'][:30]}")
    line()


def print_customers(customers: list[dict]) -> None:
    if not customers:
        print("  No customers found.")
        return
    print(f"  {'Account No':<13}{'Name':<20}{'Branch':<14}{'Type':<9}{'Balance':>13}  Status")
    line()
    for c in customers:
        print(f"  {c['account_no']:<13}{c['name'][:19]:<20}{c['branch'][:13]:<14}{c['account_type']:<9}"
              f"{money(c['balance']):>13}  {c['status']}")
    line()
    print(f"  {len(customers)} customer(s)")


def print_loans(loans: list[dict]) -> None:
    if not loans:
        print("  No loans.")
        return
    for l in loans:
        print(f"  {l['loan_id']}  {l['loan_type']:<10}{money(l['principal']):>14}  {l['rate']}%  "
              f"{l['months']}m  EMI {money(l['emi'])}")
        extra = f"paid {LoanManager.emis_paid(l)}/{l['months']} EMIs, outstanding {money(l['outstanding'])}" \
            if l["status"] in ("ACTIVE", "CLOSED") else (l.get("remarks") or "")
        print(f"  {'':22}[{l['status']}] applied {l['applied_on']}  {extra}")


# ===================================================================== app
class BankApp:
    def __init__(self, data_dir=DATA_DIR, backup_dir=BACKUP_DIR, report_dir=REPORT_DIR):
        self.db = JSONDatabase(data_dir)          # database is initialised on start-up
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
            choice = menu(BANK_NAME.upper(), ["Customer Login", "Open New Account", "Admin Login",
                                              "Interest Calculator", "Branch Directory"], "Exit")
            try:
                if choice == "1":
                    self.customer_login()
                elif choice == "2":
                    self.register()
                elif choice == "3":
                    self.admin_login()
                elif choice == "4":
                    self.interest_calculator()
                    pause()
                elif choice == "5":
                    header("BRANCH DIRECTORY")
                    for code, (name, ifsc) in BRANCHES.items():
                        print(f"  {code}  {name:<28} IFSC {ifsc}")
                    pause()
                elif choice == "0":
                    print(f"\n  Thank you for banking with {BANK_NAME}. Goodbye!\n")
                    return
            except BankError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    # ------------------------------------------------------- registration
    def register(self) -> None:
        header("OPEN NEW ACCOUNT")
        print("  Personal details (KYC)")
        name = ask("Full name")
        dob = ask("Date of birth (YYYY-MM-DD)")
        pan = ask("PAN number")
        phone = ask("Mobile number")
        email = ask("Email address")
        address = ask("Address (optional)")
        nominee = ask("Nominee name (optional)")
        print("\n  Branch")
        branch = choose("Branch", [f"{c} - {n}" for c, (n, _) in BRANCHES.items()]).split(" - ")[0]
        print("\n  Account type (minimum opening deposit)")
        acc_type = choose("Account type", [f"{t} ({money(MIN_OPENING_DEPOSIT[t])})" for t in ACCOUNT_TYPES]).split(" (")[0]
        deposit = ask("Opening deposit", f"{MIN_OPENING_DEPOSIT[acc_type]:.0f}")
        print("\n  Create a 4-digit PIN (avoid 1111, 1234 etc.)")
        pin, pin2 = ask_pin("New PIN"), ask_pin("Confirm PIN")
        c = self.accounts.register(name, dob, phone, email, pan, pin, pin2, acc_type, deposit,
                                   branch, address, nominee)
        header("ACCOUNT OPENED SUCCESSFULLY")
        for label, key in [("Account Number", "account_no"), ("Account Holder", "name"),
                           ("Account Type", "account_type"), ("Branch", "branch"), ("IFSC", "ifsc")]:
            print(f"  {label:<15}: {c[key]}")
        print(f"  {'Balance':<15}: {money(c['balance'])}")
        print("\n  Please note your account number — you need it to log in.")
        pause()

    # ------------------------------------------------------------ customer
    def customer_login(self) -> None:
        header("CUSTOMER LOGIN")
        c = self.auth.login(ask("Account number"), ask_pin())
        self.account_no = c["account_no"]
        print(f"\n  Welcome, {c['name']}!  ({c['branch']} branch)")
        pending = self.loans.list(self.account_no, "PENDING")
        if pending:
            print(f"  You have {len(pending)} loan application(s) awaiting approval.")
        self.customer_menu()

    def customer_menu(self) -> None:
        actions = [("Deposit Money", self.deposit), ("Withdraw Money", self.withdraw),
                   ("Fund Transfer", self.transfer), ("Balance Inquiry", self.balance),
                   ("Mini Statement", self.mini_statement), ("Transaction History", self.history),
                   ("Fixed Deposits", self.fd_menu), ("Loans", self.loan_menu),
                   ("Interest Calculator", self.interest_calculator),
                   ("PDF Account Statement", self.pdf_statement), ("My Profile", self.profile),
                   ("Change PIN", self.change_pin)]
        while self.account_no:
            c = self.accounts.get(self.account_no)
            choice = menu(f"{c['name'].upper()}  |  A/c {mask_account(c['account_no'])}  |  {c['account_type']}",
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
            except BankError as exc:
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
        mode = choose("Deposit mode", TransactionManager.DEPOSIT_MODES)
        ref = ask("Cheque number (6 digits)") if mode == "Cheque" else ""
        txn = self.txn.deposit(self.account_no, ask("Amount"), mode, ref)
        print(f"  ✔ {money(txn['amount'])} deposited. New balance: {money(txn['balance_after'])}")
        self._show_receipt(txn)

    def withdraw(self) -> None:
        header("WITHDRAWAL")
        amount = validate_amount(ask("Amount to withdraw"))
        txn = self.txn.withdraw(self.account_no, ask_pin(), amount)
        print(f"  ✔ {money(txn['amount'])} withdrawn. Remaining balance: {money(txn['balance_after'])}")
        self._show_receipt(txn)

    def transfer(self) -> None:
        header("FUND TRANSFER")
        to = ask("Beneficiary account number")
        receiver = self.accounts.get(to)
        print(f"  Beneficiary: {receiver['name']}  |  {receiver['branch']}  |  IFSC {receiver['ifsc']}")
        amount = validate_amount(ask("Amount"))
        print("  Transfer mode:")
        mode = choose("Mode", [f"{m} ({money(lo)} - {money(hi)})" for m, (lo, hi) in TRANSFER_MODES.items()]).split()[0]
        remarks = ask("Remarks (optional)")
        if not confirm(f"Send {money(amount)} via {mode} to {receiver['name']}?"):
            print("  Transfer cancelled.")
            return
        out, _ = self.txn.transfer(self.account_no, ask_pin(), to, amount, remarks, mode)
        print(f"  ✔ Transfer successful. Reference {out['txn_id']}")
        print(f"    Your balance: {money(out['balance_after'])}")
        self._show_receipt(out)

    def balance(self) -> None:
        header("BALANCE INQUIRY")
        b = self.txn.balance_inquiry(self.account_no, ask_pin())
        print(f"  Account          : {mask_account(b['account_no'])} ({b['account_type']})")
        print(f"  Ledger balance   : {money(b['balance'])}")
        print(f"  Available balance: {money(b['available'])}  (after minimum balance)")
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

    def profile(self) -> None:
        c = self.accounts.get(self.account_no)
        header("MY PROFILE")
        for label, key in [("Account No", "account_no"), ("Name", "name"), ("Date of Birth", "dob"),
                           ("PAN", "pan"), ("Phone", "phone"), ("Email", "email"), ("Address", "address"),
                           ("Nominee", "nominee"), ("Branch", "branch"), ("IFSC", "ifsc"),
                           ("Account Type", "account_type"), ("Customer Since", "created_at")]:
            print(f"  {label:<15}: {c.get(key) or '-'}")
        if self.accounts.is_senior(c):
            print(f"  {'':<15}  Senior citizen: +{SENIOR_CITIZEN_BONUS}% on fixed deposits")
        if confirm("\n  Update contact details / nominee?"):
            print("  Leave blank to keep current value.")
            self.accounts.update_contact(self.account_no, ask("Phone") or None, ask("Email") or None,
                                         ask("Address") or None, ask("Nominee") or None)
            print("  ✔ Profile updated.")

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

    # ------------------------------------------------------- fixed deposit
    def fd_menu(self) -> None:
        while True:
            choice = menu("FIXED DEPOSITS", ["Open new FD", "View my FDs", "Close FD"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    senior = self.accounts.is_senior(self.accounts.get(self.account_no))
                    print("  Interest rates" + (" (incl. senior citizen bonus)" if senior else "") + ":")
                    for lo, hi, _ in FD_RATES:
                        print(f"     {lo:>3}-{hi:<3} months : {fd_rate_for(lo, senior)}% p.a.")
                    amount = validate_amount(ask("Deposit amount"))
                    months = ask("Duration in months")
                    if not months.isdigit():
                        print("  Please enter the duration as a whole number of months.")
                    elif confirm(f"Open FD of {money(amount)} for {months} months at {fd_rate_for(int(months), senior)}%?"):
                        fd = self.fds.create(self.account_no, ask_pin(), amount, months)
                        print(f"  ✔ FD created. FD ID: {fd['fd_id']}")
                        print(f"    Matures on {fd['maturity_date']} for {money(fd['maturity_amount'])}")
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
            except BankError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    # --------------------------------------------------------------- loans
    def loan_menu(self) -> None:
        while True:
            choice = menu("LOAN MANAGEMENT", ["Apply for loan", "View my loans", "Repay loan (EMI)",
                                              "Cancel pending application", "Close completed loans"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print(f"  {'Type':<11}{'Rate':>7}{'Max amount':>16}{'Max tenure':>13}")
                    for t, (r, mx, mm) in LOAN_TYPES.items():
                        print(f"  {t:<11}{r:>6}%{money(mx):>16}{mm:>9} months")
                    q = self.loans.quote(choose("Loan type", LOAN_TYPES), ask("Loan amount"),
                                         ask("Tenure in months"))
                    print(f"\n  Monthly EMI : {money(q['emi'])}  for {q['months']} months")
                    print(f"  Interest    : {money(q['interest'])}   Total payable: {money(q['total_payable'])}")
                    purpose = ask("Purpose of loan")
                    if confirm("Submit loan application?"):
                        loan = self.loans.apply(self.account_no, ask_pin(), q["loan_type"], q["principal"],
                                                q["months"], purpose)
                        print(f"  ✔ Application {loan['loan_id']} submitted. The amount will be credited "
                              "once the bank approves it.")
                elif choice == "2":
                    print_loans(self.loans.list(self.account_no))
                elif choice == "3":
                    active = self.loans.list(self.account_no, "ACTIVE")
                    if not active:
                        print("  No active loans.")
                    else:
                        print_loans(active)
                        loan = next((l for l in active if l["loan_id"] == ask("Loan ID").upper()), None)
                        if not loan:
                            print("  Active loan not found.")
                        else:
                            amt = ask("Repayment amount", f"{min(loan['emi'], loan['outstanding']):.2f}")
                            l = self.loans.repay(self.account_no, ask_pin(), loan["loan_id"], amt)
                            print(f"  ✔ Payment received. Outstanding: {money(l['outstanding'])}")
                            if l["status"] == "CLOSED":
                                print("  🎉 Loan fully repaid and closed.")
                elif choice == "4":
                    self.loans.cancel(self.account_no, ask("Loan ID").upper())
                    print("  ✔ Application cancelled.")
                elif choice == "5":
                    closed = self.loans.close_completed(self.account_no)
                    print(f"  {len(closed)} completed loan(s) closed." if closed else "  No completed loans to close.")
                else:
                    continue
            except AccountFrozenError:
                raise
            except BankError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    # --------------------------------------------------------------- admin
    def admin_login(self) -> None:
        header("ADMIN LOGIN")
        admin = self.auth.admin_login(ask("Username"), getpass.getpass("  Password: "))
        am = AdminManager(self.db, admin["username"])
        print(f"\n  Welcome, administrator {admin['username']}.")
        pending = am.pending_loans()
        if pending:
            print(f"  ⚠ {len(pending)} loan application(s) awaiting your decision.")
        self.admin_menu(am)

    def admin_menu(self, am: AdminManager) -> None:
        while True:
            choice = menu("ADMINISTRATOR PANEL", [
                "View all customers", "Search customer", "Customer details", "Freeze account",
                "Unfreeze account", "Delete account", "Loan applications", "Post monthly savings interest",
                "Transaction monitor", "Reports", "Backup database", "Restore database", "View backups",
                "Change admin password"], "Logout")
            if choice == "0":
                return
            try:
                if choice == "1":
                    print_customers(am.view_customers())
                elif choice == "2":
                    print_customers(am.search_customers(ask("Name / account no / phone / email / PAN")))
                elif choice == "3":
                    c = am.get(ask("Account number"))
                    for k in ("account_no", "name", "dob", "pan", "phone", "email", "address", "nominee",
                              "branch", "ifsc", "account_type", "status", "frozen_reason", "created_at",
                              "last_login"):
                        print(f"  {k.replace('_', ' ').title():<16}: {c.get(k) or '-'}")
                    print(f"  {'Balance':<16}: {money(c['balance'])}")
                    print(f"  {'Active FDs':<16}: {len(self.fds.list(c['account_no'], True))}")
                    print("\n  Loans:")
                    print_loans(self.loans.list(c["account_no"]))
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
                    elif confirm(f"Permanently close {c['name']} ({c['account_no']}), balance {money(c['balance'])}?"):
                        self.backup.create_backup("pre_delete")
                        r = am.delete_account(acc)
                        print(f"  ✔ Account deleted. Balance to pay out to customer: {money(r['balance_to_refund'])}")
                        print("    (A backup was taken automatically before deletion.)")
                elif choice == "7":
                    self.loan_approvals(am)
                    continue
                elif choice == "8":
                    month = ask("Month YYYY-MM (blank = current)") or None
                    if confirm("Credit savings interest to all active Savings accounts?"):
                        r = am.apply_savings_interest(month)
                        print(f"  ✔ {r['month']}: interest credited to {r['accounts']} account(s), "
                              f"total {money(r['total'])}.")
                        if not r["accounts"]:
                            print("    (Accounts already credited for this month are skipped.)")
                elif choice == "9":
                    kind = choose("Type", ["All"] + list(TYPE_LABELS))
                    lo = ask("Minimum amount (blank = any)")
                    date = ask("Date YYYY-MM-DD (blank = any)") or None
                    print_txns(am.all_transactions(None if kind == "All" else kind,
                                                   float(lo) if lo.replace(".", "", 1).isdigit() else None,
                                                   date), show_account=True)
                elif choice == "10":
                    self.report_menu()
                    continue
                elif choice == "11":
                    print(f"  ✔ Backup created: {self.backup.create_backup().name}")
                elif choice in ("12", "13"):
                    backups = self.backup.list_backups()
                    if not backups:
                        print("  No backups available.")
                    else:
                        for i, b in enumerate(backups, 1):
                            print(f"  {i:>2}. {b['name']}  {b['created']}  {b['size_kb']} KB")
                        if choice == "12":
                            n = ask("Backup number to restore")
                            if n.isdigit() and 1 <= int(n) <= len(backups):
                                b = backups[int(n) - 1]
                                counts = self.backup.verify(b["path"])
                                print("  Contents: " + ", ".join(f"{k} ({v})" for k, v in counts.items()))
                                if confirm("Replace ALL current data with this backup?"):
                                    safety = self.backup.restore(b["path"])
                                    print(f"  ✔ Restored. Previous data saved as {safety.name}")
                elif choice == "14":
                    new = getpass.getpass("  New password: ")
                    if new != getpass.getpass("  Confirm new password: "):
                        print("  Passwords do not match.")
                    else:
                        self.auth.change_admin_password(am.admin, getpass.getpass("  Current password: "), new)
                        print("  ✔ Password changed.")
                else:
                    continue
            except BankError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
            pause()

    def loan_approvals(self, am: AdminManager) -> None:
        while True:
            pending = am.pending_loans()
            header(f"LOAN APPLICATIONS — {len(pending)} PENDING")
            if not pending:
                print("  No pending applications.")
                pause()
                return
            for i, l in enumerate(pending, 1):
                print(f"  {i:>2}. {l['loan_id']}  {l['customer'][:18]:<19}{l['loan_type']:<10}"
                      f"{money(l['principal']):>14}  {l['months']}m  EMI {money(l['emi'])}")
                print(f"      Purpose: {l.get('purpose') or '-'}   Customer balance: {money(l['customer_balance'])}")
            n = ask("Select application number (0 = back)")
            if n in ("", "0"):
                return
            if not (n.isdigit() and 1 <= int(n) <= len(pending)):
                continue
            loan = pending[int(n) - 1]
            try:
                action = choose("Decision", ["Approve", "Reject", "Skip"])
                if action == "Approve" and confirm(f"Approve and disburse {money(loan['principal'])}?"):
                    am.approve_loan(loan["loan_id"])
                    print("  ✔ Approved; amount credited to the customer's account.")
                elif action == "Reject":
                    am.reject_loan(loan["loan_id"], ask("Reason for rejection", "Not eligible"))
                    print("  ✔ Application rejected.")
            except BankError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    def report_menu(self) -> None:
        while True:
            choice = menu("REPORTS", ["Bank summary", "Customer report (CSV)", "Transaction report (CSV)",
                                      "Loan report (CSV)", "Account statement (PDF)"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    s = self.reports.system_summary()
                    for k, v in s.items():
                        if isinstance(v, dict):
                            continue
                        print(f"  {k.replace('_', ' ').title():<26}: {money(v) if isinstance(v, float) else v}")
                    print("\n  Accounts by branch:")
                    for b, n in s["accounts_by_branch"].items():
                        print(f"    {b:<28}{n:>4}")
                    print("\n  Transactions by type:")
                    for t, d in s["by_type"].items():
                        print(f"    {TYPE_LABELS.get(t, t):<18}{d['count']:>6}  {money(d['amount']):>16}")
                elif choice == "2":
                    print(f"  ✔ Saved: {self.reports.export_customers_csv()}")
                elif choice == "3":
                    acc = ask("Account number (blank = all accounts)") or None
                    start = ask("From date (optional)") or None
                    end = ask("To date (optional)") or None
                    print(f"  ✔ Saved: {self.reports.export_transactions_csv(acc, start, end)}")
                elif choice == "4":
                    st = choose("Status", ["All", "PENDING", "ACTIVE", "CLOSED", "REJECTED"])
                    print(f"  ✔ Saved: {self.reports.export_loans_csv(None if st == 'All' else st)}")
                elif choice == "5":
                    print(f"  ✔ Saved: {self.reports.account_statement_pdf(ask('Account number'))}")
                else:
                    continue
            except BankError as exc:
                print(f"\n  ✖ {exc}")
            pause()


def main() -> None:
    try:
        BankApp().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Session ended. Goodbye!")
    except BankError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
