"""Load demo customers with ~3 months of activity.

Usage: python seed_demo.py
Prints the demo account numbers; every demo PIN is 2580.
Admin login: admin / admin123
"""
import random
from datetime import datetime, timedelta

from account import AccountManager, FixedDepositManager, LoanManager
from admin import AdminManager
from auth import AuthManager
from database import JSONDatabase
from transaction import TransactionManager
from utils import DATA_DIR, DATETIME_FMT

PIN = "2580"
PEOPLE = [  # name, dob, phone, email, PAN, type, opening deposit, branch, nominee
    ("Anitta Joseph", "1998-04-12", "9847012345", "anitta@example.com", "AJKPJ4521L", "Savings", 45000, "101", "Mary Joseph"),
    ("Rahul Menon", "1990-11-02", "9895098765", "rahul@example.com", "BRMPM7812Q", "Salary", 0, "102", "Lakshmi Menon"),
    ("Priya Nair", "1985-07-21", "9746011223", "priya@example.com", "CPNPN3390D", "Current", 150000, "102", ""),
    ("Thomas Kurian", "1958-02-09", "8606543210", "thomas@example.com", "DTKPK1188H", "Savings", 300000, "103", "Annie Kurian"),
    ("Fathima Rasheed", "2001-09-30", "7012345678", "fathima@example.com", "EFRPR6655M", "Savings", 8000, "104", ""),
]


def main():
    random.seed(11)
    db = JSONDatabase(DATA_DIR)
    if db.all("customers"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth = AuthManager(db)
    acc, txn = AccountManager(db, auth), TransactionManager(db, auth)
    fd, loan, admin = FixedDepositManager(db, auth), LoanManager(db, auth), AdminManager(db, "admin")

    accounts = [acc.register(n, d, p, e, pan, PIN, PIN, t, dep, br, nominee=nom)["account_no"]
                for n, d, p, e, pan, t, dep, br, nom in PEOPLE]
    for month in range(3):
        txn.deposit(accounts[1], 62000, "Cash")                         # Rahul's salary
        for _ in range(18):
            a = random.choice(accounts)
            r = random.random()
            try:
                if r < 0.3:
                    txn.deposit(a, random.choice([2000, 3500, 5000, 12000]),
                                *random.choice([("Cash", ""), ("Cheque", str(random.randint(100000, 999999)))]))
                elif r < 0.65:
                    txn.withdraw(a, PIN, random.choice([1500, 2750, 4000, 6200]))
                else:
                    b = random.choice([x for x in accounts if x != a])
                    txn.transfer(a, PIN, b, random.choice([800, 1500, 3000, 7500]),
                                 random.choice(["Rent", "Dinner", "Books", "Repayment"]), random.choice(["IMPS", "NEFT"]))
            except Exception:
                pass                                    # e.g. insufficient funds — skip
        admin.apply_savings_interest(f"2026-{8 + month:02d}")
    fd.create(accounts[0], PIN, 20000, 12)
    fd.create(accounts[3], PIN, 200000, 36)             # senior citizen rate
    l1 = loan.apply(accounts[1], PIN, "Vehicle", 450000, 60, "New car")
    admin.approve_loan(l1["loan_id"])
    loan.repay(accounts[1], PIN, l1["loan_id"], l1["emi"])
    loan.apply(accounts[0], PIN, "Education", 300000, 48, "MBA fees")       # left pending for the admin
    l3 = loan.apply(accounts[4], PIN, "Personal", 500000, 36, "Travel")
    admin.reject_loan(l3["loan_id"], "Income not sufficient for requested amount")

    # Spread the activity over the last 90 days so history and statements look real.
    with db.editing("transactions") as txns:
        start = datetime.now() - timedelta(days=90)
        step = timedelta(days=90) / max(1, len(txns))
        for i, t in enumerate(txns):
            t["timestamp"] = (start + step * i + timedelta(minutes=random.randint(0, 50))).strftime(DATETIME_FMT)
    first = {}
    for t in db.all("transactions"):
        first.setdefault(t["account_no"], t["timestamp"])
    for no, ts in first.items():
        db.update("customers", "account_no", no, {"created_at": ts})

    print("Demo data loaded. All demo PINs are", PIN)
    for c in db.all("customers"):
        print(f"  {c['account_no']}  {c['name']:<16} {c['account_type']:<8} {c['branch']:<24} "
              f"balance {c['balance']:,.2f}")
    print("Admin login: admin / admin123  (1 loan application is waiting for approval)")


if __name__ == "__main__":
    main()
