"""Load demo data: users, suppliers, customers, ~30 products and 40 days of
purchases and sales (cash, UPI, credit, inter-state), with some low-stock items.

Usage:  python seed_demo.py
Logins: admin / admin123 · manager / manager1 · cashier / cash1234 · store / store123
"""
import random
from datetime import date, timedelta

from inventory import utils
from inventory.auth import AuthManager, UserManager
from inventory.customers import CustomerManager
from inventory.database import JSONDatabase
from inventory.products import ProductManager
from inventory.purchases import PurchaseManager
from inventory.sales import SalesManager
from inventory.suppliers import SupplierManager

PRODUCTS = [  # name, brand, category, unit, cost, selling, reorder, gst override, mrp
    ("Basmati Rice", "India Gate", "Groceries", "kg", 92, 118, 25, None, None),
    ("Matta Rice", "Nirapara", "Groceries", "kg", 48, 58, 40, None, None),
    ("Toor Dal", "Tata Sampann", "Groceries", "kg", 128, 152, 15, None, None),
    ("Wheat Atta 5kg", "Aashirvaad", "Groceries", "pack", 228, 262, 10, None, 290),
    ("Sunflower Oil 1L", "Freedom", "Groceries", "pcs", 118, 138, 20, None, 155),
    ("Coconut Oil 1L", "Parachute", "Groceries", "pcs", 205, 238, 12, None, 260),
    ("Sugar", "Madhur", "Groceries", "kg", 40, 47, 30, None, None),
    ("Tea Powder 250g", "Brooke Bond", "Groceries", "pack", 112, 132, 15, None, 145),
    ("Cola 750ml", "Coca-Cola", "Beverages", "pcs", 24, 29, 24, None, 42),
    ("Orange Drink 600ml", "Fanta", "Beverages", "pcs", 22, 26, 24, None, 40),
    ("Energy Drink 250ml", "Red Bull", "Beverages", "pcs", 72, 82, 12, None, 125),
    ("Bath Soap 100g", "Lux", "Personal Care", "pcs", 28, 36, 30, None, 42),
    ("Shampoo 340ml", "Clinic Plus", "Personal Care", "pcs", 152, 186, 10, None, 210),
    ("Toothpaste 150g", "Colgate", "Personal Care", "pcs", 72, 88, 20, None, 99),
    ("Hair Oil 300ml", "Dabur", "Personal Care", "pcs", 118, 142, 10, None, 160),
    ("Detergent Powder 1kg", "Surf Excel", "Household", "pack", 118, 138, 15, None, 170),
    ("Dishwash Liquid 500ml", "Vim", "Household", "pcs", 82, 98, 12, None, 120),
    ("Floor Cleaner 1L", "Lizol", "Household", "pcs", 158, 182, 8, None, 215),
    ("Toilet Cleaner 500ml", "Harpic", "Household", "pcs", 76, 89, 10, None, 110),
    ("Ball Pen (pack of 10)", "Reynolds", "Stationery", "pack", 58, 72, 10, None, 90),
    ("A4 Paper Ream", "JK Copier", "Stationery", "pack", 245, 289, 6, None, None),
    ("Notebook 200 pages", "Classmate", "Stationery", "pcs", 48, 62, 20, 0.0, 70),
    ("File Folder", "Solo", "Stationery", "pcs", 35, 48, 10, None, None),
    ("USB-C Charger 25W", "Samsung", "Electronics", "pcs", 980, 1199, 4, None, 1599),
    ("AA Batteries (4)", "Duracell", "Electronics", "pack", 132, 162, 10, None, 199),
    ("LED Bulb 9W", "Philips", "Electronics", "pcs", 88, 109, 15, None, 140),
    ("Extension Board", "Anchor", "Electronics", "pcs", 410, 499, 3, None, 650),
    ("Earphones", "boAt", "Electronics", "pcs", 380, 499, 4, None, 999),
]

HSN = {"Basmati Rice": "1006", "Matta Rice": "1006", "Toor Dal": "0713", "Wheat Atta 5kg": "1101",
       "Sunflower Oil 1L": "1512", "Coconut Oil 1L": "1513", "Sugar": "1701", "Tea Powder 250g": "0902",
       "Cola 750ml": "2202", "Orange Drink 600ml": "2202", "Energy Drink 250ml": "2202", "Bath Soap 100g": "3401",
       "Shampoo 340ml": "3305", "Toothpaste 150g": "3306", "Hair Oil 300ml": "3305",
       "Detergent Powder 1kg": "3402", "Dishwash Liquid 500ml": "3402", "Floor Cleaner 1L": "3808",
       "Toilet Cleaner 500ml": "3808", "Ball Pen (pack of 10)": "9608", "A4 Paper Ream": "4802",
       "Notebook 200 pages": "4820", "File Folder": "4820", "USB-C Charger 25W": "8504", "AA Batteries (4)": "8506",
       "LED Bulb 9W": "8539", "Extension Board": "8536", "Earphones": "8518"}


def main():
    random.seed(17)
    db = JSONDatabase(utils.DATA_DIR)
    if db.all("products"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth = AuthManager(db)
    um = UserManager(db, "admin")
    for u, name, role, pw in [("manager", "Suresh Nair", "manager", "manager1"), ("cashier", "Anitta Joseph", "cashier", "cash1234"),
                              ("store", "Rahul Menon", "storekeeper", "store123")]:
        _, temp = um.add(u, name, role)
        auth.change_password(u, temp, pw, pw)

    sm_ = SupplierManager(db, "store")
    sups = [sm_.add("Kerala Food Distributors", "9847011111", "orders@keralafood.in", "32AABCK1234L1Z5",
                    address="Kozhikode", contact_person="Joseph K"),
            sm_.add("Malabar FMCG Agencies", "9847022222", "", "32AAFCM5678P1Z9", address="Kannur", contact_person="Shameer"),
            sm_.add("Chennai Electricals", "9840033333", "sales@chennaielec.com", "33AABCC9012Q1Z1",
                    address="Chennai", contact_person="Murugan"),
            sm_.add("Bengaluru Stationery House", "9900044444", "", "29AACCB3456R1Z3", address="Bengaluru")]
    cm = CustomerManager(db, "manager")
    custs = [cm.add("Hotel Sea Queen", "9895055555", "purchase@seaqueen.in", "32AAEHS7788N1Z4", address="Beach Road, Kozhikode"),
             cm.add("St. Joseph's School", "9895066666", "", "", "Kerala", "Kozhikode", "Fr. Thomas"),
             cm.add("Green Mart Supermarket", "9895077777", "", "32AAGFG1122M1Z8", address="Feroke"),
             cm.add("Coimbatore Traders", "9843088888", "", "33AACFC3344L1Z6", address="Coimbatore"),
             cm.add("Ravi Kumar", "9946099999")]

    pm = ProductManager(db, "store")
    prods = []
    for name, brand, cat, unit, cost, sell, reorder, gst, mrp in PRODUCTS:
        prods.append(pm.add(name, cat, unit, cost, sell, 0, reorder, gst, HSN[name], brand, mrp=mrp,
                            location=f"R{random.randint(1, 8)}-{random.choice('ABC')}"))
    supplier_for = {"Groceries": [0, 1], "Beverages": [1], "Personal Care": [1], "Household": [1],
                    "Stationery": [3], "Electronics": [2]}

    pur, sales = PurchaseManager(db, "store"), SalesManager(db, "cashier")
    today = date.today()
    start = today - timedelta(days=40)

    def restock(day, force=False):
        """Buy for products below ~2x reorder level, grouped by supplier."""
        orders = {}
        for p in pm.list():
            if force or p["stock"] <= p["reorder_level"] * 1.5:
                si = random.choice(supplier_for[p["category"]])
                qty = p["reorder_level"] * random.randint(3, 5)
                cost = round(p["purchase_price"] * random.uniform(0.97, 1.04), 2)
                orders.setdefault(si, []).append({"product_id": p["product_id"], "qty": qty, "cost": cost,
                                                  "discount_pct": random.choice([0, 0, 2, 5])})
        for si, items in orders.items():
            po = pur.create(sups[si]["supplier_id"], items, f"{sups[si]['name'][:3].upper()}/{random.randint(1000, 9999)}", day)
            if random.random() < 0.75:
                pur.pay(po["purchase_id"], po["grand_total"], random.choice(["Bank Transfer", "UPI"]), f"TRF{random.randint(10**5, 10**6)}", day)
            elif random.random() < 0.5:
                pur.pay(po["purchase_id"], round(po["grand_total"] / 2), "Cash", on=day)

    restock(start, force=True)
    for offset in range(1, 41):
        day = start + timedelta(days=offset)
        if offset % 6 == 0 and offset < 38:
            restock(day)
        for _ in range(random.randint(4, 9)):
            b2b = random.random() < 0.22
            cust = random.choice(custs) if b2b else None
            items, picked = [], random.sample(pm.list(), k=random.randint(1, 4))
            for p in picked:
                if p["stock"] <= 0:
                    continue
                qty = random.choice([1, 1, 2, 3, 5]) * (random.randint(2, 6) if b2b else 1)
                if p["unit"] == "kg":
                    qty = random.choice([0.5, 1, 2, 5]) * (3 if b2b else 1)
                qty = min(qty, p["stock"])
                items.append({"product_id": p["product_id"], "qty": qty,
                              "discount_pct": random.choice([0, 0, 0, 2, 5]) if b2b else 0})
            if not items:
                continue
            if b2b:
                mode = random.choice(["Credit", "Bank Transfer", "UPI", "Credit"])
                s = sales.create(cust["customer_id"], items, mode, None, "" if mode == "Credit" else f"PAY{random.randint(10**5, 10**6)}", day)
                if mode == "Credit" and day < today - timedelta(days=10) and random.random() < 0.6:
                    sales.receive_payment(s["sale_id"], s["grand_total"], "Bank Transfer", f"NEFT{random.randint(10**5, 10**6)}")
            else:
                mode = random.choice(["Cash", "Cash", "UPI", "Card"])
                sales.create(utils.WALK_IN_CUSTOMER, items, mode, None, "" if mode == "Cash" else f"TXN{random.randint(10**5, 10**6)}", day)
    # A cancelled invoice and a pending purchase order
    last = sales.list()[3]
    SalesManager(db, "manager").cancel(last["sale_id"], "Billing error — items re-billed")
    pur.create(sups[2]["supplier_id"], [{"product_id": prods[23]["product_id"], "qty": 10},
                                        {"product_id": prods[27]["product_id"], "qty": 12}], receive_now=False)
    # Make a couple of items low / out of stock for the alerts
    for idx, left in ((10, 0), (24, 3)):
        p = pm.get(prods[idx]["product_id"])
        if p["stock"] > left:
            pm.adjust_stock(p["product_id"], -(p["stock"] - left), "Audit correction", "Year-end count")

    # Back-date stock ledger entries to their document dates
    dates = {s["invoice_no"]: s["date"] for s in db.all("sales")}
    dates.update({p["purchase_id"]: p["received_on"] or p["date"] for p in db.all("purchases")})
    with db.editing("stock_movements") as moves:
        for m in moves:
            if m["ref"] in dates:
                m["at"] = f"{dates[m['ref']]}T{random.randint(9, 20):02d}:{random.randint(0, 59):02d}:00"
            elif m["type"] == "OPENING":
                m["at"] = f"{start.isoformat()}T09:00:00"

    v = pm.valuation()
    print(f"Seeded {len(prods)} products, {len(sups)} suppliers, {len(custs)} customers, "
          f"{len(db.all('purchases'))} purchases, {len(db.all('sales'))} invoices. "
          f"Stock value {v['cost_value']:,.0f}; {v['low_stock']} low, {v['out_of_stock']} out of stock.")
    print("Logins: admin/admin123 · manager/manager1 · cashier/cash1234 · store/store123")


if __name__ == "__main__":
    main()
