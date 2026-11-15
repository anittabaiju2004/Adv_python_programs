"""Populate the data folder with a demo user and a year of sample data.

Usage:  python seed_demo.py
Login:  demo / demo123
"""
import random
from datetime import date, timedelta

from tracker import config
from tracker.auth import AuthManager
from tracker.bills import BillManager
from tracker.budget import BudgetManager
from tracker.database import JSONDatabase
from tracker.savings import SavingsManager
from tracker.transactions import ExpenseManager, IncomeManager

SPEND = {  # category: (min, max, times per month, descriptions)
    "Food": (80, 900, 14, ["Groceries", "Restaurant", "Swiggy order", "Tea & snacks"]),
    "Transport": (40, 600, 8, ["Fuel", "Metro card", "Auto", "Uber"]),
    "Shopping": (300, 4000, 2, ["Clothes", "Amazon order", "Shoes"]),
    "Health": (150, 2500, 1, ["Pharmacy", "Doctor visit"]),
    "Entertainment": (150, 1200, 2, ["Movie", "OTT subscription", "Concert"]),
    "Education": (300, 3000, 1, ["Online course", "Books"]),
}


def main():
    random.seed(42)
    db = JSONDatabase(config.DATA_DIR)
    auth = AuthManager(db)
    if auth.get_user("demo"):
        print("Demo user already exists — nothing to do.")
        return
    auth.register("demo", "demo123", "Demo User")
    exp, inc = ExpenseManager(db, "demo"), IncomeManager(db, "demo")
    today = date.today()

    for back in range(11, -1, -1):
        first = date(today.year, today.month, 1)
        m = first.month - back
        y = first.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        current = (y, m) == (today.year, today.month)
        last_day = today.day if current else 28
        def day(d): return date(y, m, min(d, last_day)).isoformat()
        inc.add(55000, "Salary", day(1), "Monthly salary")
        if random.random() < 0.4:
            inc.add(random.randint(5000, 15000), "Freelance", day(random.randint(5, 25)), "Freelance project")
        exp.add(15000, "Rent", day(3), "House rent", "Net Banking")
        for cat, (lo, hi, n, descs) in SPEND.items():
            for _ in range(random.randint(max(0, n - 2), n + 1)):
                exp.add(random.randint(lo, hi), cat, day(random.randint(1, last_day)),
                        random.choice(descs), random.choice(["Cash", "UPI", "Card"]))

    month = today.strftime("%Y-%m")
    bm = BudgetManager(db, "demo")
    bm.set_budget(month, 40000)
    bm.set_budget(month, 8000, "Food")
    bm.set_budget(month, 3000, "Transport")
    bm.set_budget(month, 3000, "Shopping")

    sm = SavingsManager(db, "demo")
    sm.create_goal("Emergency Fund", 150000, (today + timedelta(days=365)).isoformat(), 62000)
    sm.create_goal("New Laptop", 80000, (today + timedelta(days=150)).isoformat(), 25000)

    bills = BillManager(db, "demo")
    bills.add_bill("Electricity", 1850, (today + timedelta(days=3)).isoformat(), "monthly")
    bills.add_bill("Internet", 799, (today + timedelta(days=12)).isoformat(), "monthly")
    bills.add_bill("Phone recharge", 299, (today - timedelta(days=2)).isoformat(), "monthly")
    bills.add_bill("Car insurance", 12500, (today + timedelta(days=60)).isoformat(), "yearly")

    print(f"Seeded {len(exp.list())} expenses and {len(inc.list())} incomes.")
    print("Log in with  demo / demo123   (admin: admin / admin123)")


if __name__ == "__main__":
    main()
