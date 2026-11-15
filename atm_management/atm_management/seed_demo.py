"""Load demo customers with ~3 months of activity.

Usage: python seed_demo.py
Prints the demo account numbers; every demo PIN is 2580.
Admin login: admin / admin123
"""
import random
from datetime import datetime, timedelta

from account import AccountManager, FixedDepositManager, LoanManager
from auth import AuthManager
from database import JSONDatabase
from transaction import TransactionManager
from utils import DATA_DIR, DATETIME_FMT

PIN = "2580"
PEOPLE = [
    ("Anitta Joseph", "9847012345", "anitta@example.com", "Savings", 25000),
    ("Rahul Menon", "9895098765", "rahul@example.com", "Savings", 18000),
    ("Priya Nair", "9746011223", "priya@example.com", "Current", 60000),
    ("Arjun Das", "8606543210", "arjun@example.com", "Savings", 9000),
]


def main():
    random.seed(7)
    db = JSONDatabase(DATA_DIR)
    if db.all("customers"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth = AuthManager(db)
    acc, txn = AccountManager(db, auth), TransactionManager(db, auth)
    fd, loan = FixedDepositManager(db, auth), LoanManager(db, auth)

    accounts = [acc.register(n, p, e, PIN, PIN, t, d)["account_no"] for n, p, e, t, d in PEOPLE]
    for _ in range(60):
        a = random.choice(accounts)
        r = random.random()
        try:
            if r < 0.35:
                txn.deposit(a, random.choice([1000, 2000, 2500, 5000, 7500]))
            elif r < 0.7:
                txn.withdraw(a, PIN, random.choice([500, 1000, 2000, 3000]))
            else:
                b = random.choice([x for x in accounts if x != a])
                txn.transfer(a, PIN, b, random.choice([250, 500, 1200, 1500]), "Demo transfer")
        except Exception:
            pass                                    # e.g. insufficient funds — skip
    fd.create(accounts[0], PIN, 10000, 12)
    fd.create(accounts[2], PIN, 25000, 36)
    ln = loan.apply(accounts[1], PIN, "Education", 50000, 24)
    loan.repay(accounts[1], PIN, ln["loan_id"], ln["emi"])
    loan.apply(accounts[0], PIN, "Vehicle", 120000, 36)

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
        print(f"  {c['account_no']}  {c['name']:<15} {c['account_type']:<8} balance {c['balance']:,.2f}")
    print("Admin login: admin / admin123")


if __name__ == "__main__":
    main()
