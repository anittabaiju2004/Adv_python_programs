"""Menu-driven interface with role-based menus (admin, manager, cashier, storekeeper)."""
from __future__ import annotations

import getpass
import sys
from datetime import date

from . import utils
from .admin import AdminPanel
from .auth import AuthManager, UserManager, can
from .backup import BackupManager
from .categories import CategoryManager
from .customers import CustomerManager
from .database import JSONDatabase
from .products import ADJUST_REASONS, ProductManager
from .purchases import PurchaseManager
from .reports import ReportGenerator
from .sales import SalesManager
from .suppliers import SupplierManager
from .utils import (BUSINESS_NAME, GST_RATES, PAYMENT_MODES, ROLES, STATES, UNITS, WALK_IN_CUSTOMER,
                    InventoryError, money)

W = 84


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


def choose(prompt: str, options: list, allow_blank: bool = False) -> str:
    options = [str(o) for o in options]
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


def period() -> tuple[str, str]:
    first = date.today().replace(day=1)
    return ask("From YYYY-MM-DD", first.isoformat()), ask("To YYYY-MM-DD", date.today().isoformat())


def print_products(ps: list[dict]) -> None:
    if not ps:
        print("  No products.")
        return
    print(f"  {'ID':<7}{'Product':<30}{'Category':<15}{'Stock':>12}{'Price':>11}{'GST':>5}  Status")
    line()
    for p in ps:
        status = "OUT" if p["stock"] <= 0 else ("LOW" if p["stock"] <= p["reorder_level"] else "")
        if not p["active"]:
            status = "discontinued"
        name = f"{p['name']} {p['brand']}".strip()
        print(f"  {p['product_id']:<7}{name[:29]:<30}{p['category'][:14]:<15}{p['stock']:>8g} {p['unit']:<3}"
              f"{money(p['selling_price']):>11}{p['gst_rate']:>4g}%  {status}")
    line()
    print(f"  {len(ps)} product(s)")


def print_doc_totals(d: dict) -> None:
    print(f"  {'Gross':<22}{money(d['gross']):>14}")
    if d["discount"]:
        print(f"  {'Discount':<22}{'-' + money(d['discount']):>14}")
    print(f"  {'Taxable value':<22}{money(d['taxable']):>14}")
    if d["inter_state"]:
        print(f"  {'IGST':<22}{money(d['igst']):>14}")
    else:
        print(f"  {'CGST':<22}{money(d['cgst']):>14}")
        print(f"  {'SGST':<22}{money(d['sgst']):>14}")
    print(f"  {'Round off':<22}{d['round_off']:>+14,.2f}")
    line()
    print(f"  {'GRAND TOTAL':<22}{money(d['grand_total']):>14}")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)                     # data loaded automatically
        self.auth = AuthManager(self.db)
        CategoryManager(self.db)
        CustomerManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.report_dir = report_dir or utils.REPORT_DIR
        self.user: dict | None = None

    @property
    def actor(self) -> str:
        return self.user["username"] if self.user else "system"

    def products(self):
        return ProductManager(self.db, self.actor)

    def sales(self):
        return SalesManager(self.db, self.actor)

    def purchases(self):
        return PurchaseManager(self.db, self.actor)

    def customers(self):
        return CustomerManager(self.db, self.actor)

    def suppliers(self):
        return SupplierManager(self.db, self.actor)

    def reports(self):
        return ReportGenerator(self.db, self.report_dir)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(f"{BUSINESS_NAME.upper()} — INVENTORY MANAGEMENT", ["Login"], "Exit")
            try:
                if choice == "1":
                    self.login()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except InventoryError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def login(self) -> None:
        header("LOGIN")
        self.user = self.auth.login(ask("Username"), getpass.getpass("  Password: "))
        if self.user["must_change_password"]:
            print("\n  You are using a temporary password. Please set a new one.")
            while True:
                try:
                    self.change_password()
                    break
                except InventoryError as exc:
                    print(f"  ✖ {exc}")
        print(f"\n  Welcome, {self.user['name']} ({self.user['role']}).")
        self.alerts()
        items = [("Dashboard", self.dashboard, None, False), ("Sales & billing", self.sales_menu, "sales", True),
                 ("Products & stock", self.product_menu, "products", True),
                 ("Categories", self.category_menu, "categories", True),
                 ("Purchases", self.purchase_menu, "purchases", True),
                 ("Suppliers", self.supplier_menu, "suppliers", True),
                 ("Customers", self.customer_menu, "customers", True), ("Reports", self.report_menu, "reports", True),
                 ("Admin panel (users, activity log, backup)", self.admin_menu, "admin", True),
                 ("Change password", self.change_password, None, False)]
        items = [i for i in items if i[2] is None or can(self.user, i[2])]
        while self.user:
            choice = menu(f"{BUSINESS_NAME} — {self.user['name']} ({self.user['role']})", [i[0] for i in items], "Logout")
            if choice == "0":
                print("  Logged out.")
                self.user = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(items)):
                continue
            _, handler, _, sub = items[int(choice) - 1]
            try:
                handler()
            except InventoryError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            if not sub:
                pause()

    def submenu(self, title: str, options: list[tuple]) -> None:
        options = [o for o in options if len(o) < 3 or can(self.user, o[2])]
        while self.user:
            choice = menu(title, [o[0] for o in options])
            if choice == "0":
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(options)):
                continue
            try:
                options[int(choice) - 1][1]()
            except InventoryError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def change_password(self) -> None:
        self.auth.change_password(self.actor, getpass.getpass("  Current password: "),
                                  getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
        print("  ✔ Password changed.")

    def alerts(self) -> None:
        pm = self.products()
        low, out = pm.low_stock(), pm.out_of_stock()
        if out:
            print(f"  ⚠ Out of stock ({len(out)}): " + ", ".join(p["name"] for p in out[:6]) + (" ..." if len(out) > 6 else ""))
        if low:
            print(f"  ⚠ Low stock ({len(low)}): " + ", ".join(f"{p['name']} ({p['stock']:g})" for p in low[:6])
                  + (" ..." if len(low) > 6 else ""))

    def dashboard(self) -> None:
        d = AdminPanel(self.db, self.report_dir).dashboard()
        header(f"DASHBOARD — {d['date']}")
        print(f"  Today      : {money(d['today_sales'])} from {d['today_invoices']} invoice(s)")
        print(f"  This month : {money(d['month_sales'])} from {d['month_invoices']} invoice(s)", end="")
        print(f" · gross profit {money(d['month_profit'])} ({d['month_margin']}%)" if can(self.user, "reports") else "")
        print(f"  Stock      : {d['products']} products · value {money(d['stock_value'])} at cost · "
              f"{len(d['low_stock'])} low · {len(d['out_of_stock'])} out of stock")
        if can(self.user, "reports"):
            print(f"  Receivable : {money(d['receivable'])} · Payable {money(d['payable'])} · "
                  f"Open purchase orders {d['open_orders']}")
            if d["top_products"]:
                print("\n  Top sellers this month:")
                for p in d["top_products"]:
                    print(f"    {p['name'][:32]:<33}{p['qty']:>8g} {p['unit']:<6}{money(p['revenue']):>14}")
        self.alerts()

    # ------------------------------------------------------------- pickers
    def pick_product(self, prompt: str = "Product (name, ID, SKU or barcode)", include_inactive: bool = False) -> dict:
        pm = self.products()
        q = ask(prompt)
        if not q:
            raise InventoryError("No product selected.")
        try:
            return pm.get(q)
        except InventoryError:
            pass
        matches = pm.search(q, include_inactive)
        if not matches:
            raise InventoryError(f"No product matches '{q}'.")
        if len(matches) == 1:
            return matches[0]
        for i, p in enumerate(matches[:20], 1):
            print(f"   {i:>2}. {p['product_id']}  {(p['name'] + ' ' + p['brand']).strip()[:34]:<35}"
                  f"{p['stock']:>7g} {p['unit']:<5}{money(p['selling_price']):>11}")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= min(len(matches), 20)):
            raise InventoryError("Invalid selection.")
        return matches[int(n) - 1]

    def pick_party(self, mgr, allow_blank_default: str | None = None) -> dict:
        q = ask(f"{mgr.label} name, phone, ID or GSTIN" + (" (blank = walk-in)" if allow_blank_default else ""))
        if not q and allow_blank_default:
            return mgr.get(allow_blank_default)
        try:
            return mgr.get(q)
        except InventoryError:
            pass
        matches = [m for m in mgr.search(q) if m["active"]]
        if not matches:
            raise InventoryError(f"No {mgr.label.lower()} matches '{q}'.")
        if len(matches) == 1:
            print(f"  {mgr.label}: {matches[0]['name']} ({matches[0]['state']})")
            return matches[0]
        for i, m in enumerate(matches, 1):
            print(f"   {i:>2}. {m[mgr.id_field]:<9}{m['name'][:30]:<31}{m['phone']:<13}{m['state']}")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= len(matches)):
            raise InventoryError("Invalid selection.")
        return matches[int(n) - 1]

    # --------------------------------------------------------------- sales
    def sales_menu(self) -> None:
        self.submenu("SALES & BILLING", [
            ("New sale / bill", self.new_sale), ("Receive payment (credit invoice)", self.receive_payment),
            ("View invoice", self.view_invoice), ("Print invoice (PDF)", self.print_invoice),
            ("Sales history", self.sales_history), ("Cancel invoice", self.cancel_invoice, "sales.cancel")])

    def new_sale(self) -> None:
        header("NEW SALE")
        cust = self.pick_party(self.customers(), WALK_IN_CUSTOMER)
        sm, cart = self.sales(), []
        print("  Add items. Leave the product blank when done.")
        while True:
            q = ask("Product (name, ID, SKU or barcode; blank = done)")
            if not q:
                break
            try:
                pm = self.products()
                try:
                    p = pm.get(q)
                except InventoryError:
                    matches = pm.search(q)
                    if not matches:
                        raise InventoryError(f"No product matches '{q}'.")
                    if len(matches) > 1:
                        for i, m in enumerate(matches[:15], 1):
                            print(f"     {i:>2}. {m['name']} {m['brand']}  ({m['stock']:g} {m['unit']}) "
                                  f"{money(m['selling_price'])}")
                        n = ask("Select number")
                        if not (n.isdigit() and 1 <= int(n) <= min(len(matches), 15)):
                            continue
                        p = matches[int(n) - 1]
                    else:
                        p = matches[0]
                print(f"    {p['name']} — {money(p['selling_price'])}/{p['unit']} + GST {p['gst_rate']:g}% · "
                      f"in stock {p['stock']:g}")
                item = {"product_id": p["product_id"], "qty": ask("Quantity", "1")}
                if can(self.user, "discount"):
                    item["discount_pct"] = ask("Discount %", "0")
                # Validate against a trial cart; the real cart changes only if it passes.
                trial = [dict(c) for c in cart]
                existing = next((c for c in trial if c["product_id"] == p["product_id"]), None)
                if existing:
                    existing["qty"] = str(float(existing["qty"]) + float(item["qty"]))
                    existing["discount_pct"] = item.get("discount_pct", existing.get("discount_pct", 0))
                else:
                    trial.append(item)
                quote = sm.quote(cust["customer_id"], trial)     # validates stock / qty / discount
                cart = trial
                print(f"    ✔ Added. Cart: {len(cart)} item(s), total {money(quote['grand_total'])}")
            except (InventoryError, ValueError) as exc:
                print(f"    ✖ {exc}")
        if not cart:
            print("  Sale cancelled (no items).")
            return
        q = sm.quote(cust["customer_id"], cart)
        header(f"BILL — {cust['name']}")
        for l in q["lines"]:
            disc = f" -{l['discount_pct']:g}%" if l["discount_pct"] else ""
            print(f"  {l['name'][:30]:<31}{l['qty']:>7g} {l['unit']:<4} x {l['rate']:>9,.2f}{disc:<6}"
                  f"{l['gst_rate']:>4g}%{money(l['total']):>13}")
        line()
        print_doc_totals(q)
        modes = PAYMENT_MODES if cust["customer_id"] != WALK_IN_CUSTOMER else [m for m in PAYMENT_MODES if m != "Credit"]
        mode = choose("Payment mode", modes)
        paid, ref = None, ""
        if mode != "Credit":
            if cust["customer_id"] != WALK_IN_CUSTOMER:
                paid = ask("Amount received", f"{q['grand_total']:.2f}")
            if mode != "Cash":
                ref = ask("Transaction reference")
            elif cust["customer_id"] == WALK_IN_CUSTOMER:
                tendered = ask("Cash tendered", f"{q['grand_total']:.0f}")
                try:
                    change = float(tendered) - q["grand_total"]
                    if change > 0:
                        print(f"  Change to return: {money(change)}")
                except ValueError:
                    pass
        s = sm.create(cust["customer_id"], cart, mode, paid, ref)
        print(f"\n  ✔ Invoice {s['invoice_no']} saved — {money(s['grand_total'])} ({s['payment_status']}).")
        if confirm("Print invoice as PDF?"):
            print(f"  ✔ Saved: {sm.invoice_pdf(s['sale_id'], self.report_dir / 'invoices')}")

    def _pick_invoice(self) -> dict:
        return self.sales().get(ask("Invoice number or sale ID (e.g. INV/2026-27/0001 or S00001)"))

    def view_invoice(self) -> None:
        s = self._pick_invoice()
        header(f"{s['invoice_no']} — {s['date']} — {s['status']}")
        print(f"  Customer: {s['customer_name']} ({s['customer_id']}) · place of supply {s['place_of_supply']}")
        for l in s["lines"]:
            print(f"  {l['name'][:32]:<33}{l['qty']:>7g} {l['unit']:<4} x {l['rate']:>9,.2f}  {l['gst_rate']:>4g}%"
                  f"{money(l['total']):>13}")
        line()
        print_doc_totals(s)
        print(f"  Paid {money(s['amount_paid'])} · balance {money(s['grand_total'] - s['amount_paid'])} · {s['payment_status']}")
        if can(self.user, "reports"):
            print(f"  Cost {money(s['cost'])} · gross profit {money(s['profit'])}")

    def print_invoice(self) -> None:
        print(f"  ✔ Saved: {self.sales().invoice_pdf(self._pick_invoice()['sale_id'], self.report_dir / 'invoices')}")

    def receive_payment(self) -> None:
        dues = [s for s in self.sales().list() if s["grand_total"] - s["amount_paid"] > 0.005]
        for s in dues[:20]:
            print(f"  {s['invoice_no']:<20}{s['date']:<12}{s['customer_name'][:24]:<25}"
                  f"due {money(s['grand_total'] - s['amount_paid'])}")
        if not dues:
            print("  No unpaid invoices.")
            return
        s = self._pick_invoice()
        due = s["grand_total"] - s["amount_paid"]
        mode = choose("Mode", [m for m in PAYMENT_MODES if m != "Credit"])
        s = self.sales().receive_payment(s["sale_id"], ask("Amount", f"{due:.2f}"), mode,
                                         ask("Reference") if mode != "Cash" else "")
        print(f"  ✔ Payment recorded. Status: {s['payment_status']}.")

    def sales_history(self) -> None:
        start, end = period()
        ss = self.sales().list(start, end, include_cancelled=True)
        print(f"  {'Invoice':<20}{'Date':<12}{'Customer':<26}{'Total':>13}  Status")
        line()
        for s in ss:
            status = "CANCELLED" if s["status"] == "CANCELLED" else s["payment_status"]
            print(f"  {s['invoice_no']:<20}{s['date']:<12}{s['customer_name'][:25]:<26}{money(s['grand_total']):>13}  {status}")
        print(f"\n  {len([s for s in ss if s['status'] == 'COMPLETED'])} invoice(s), total "
              f"{money(sum(s['grand_total'] for s in ss if s['status'] == 'COMPLETED'))}")

    def cancel_invoice(self) -> None:
        s = self._pick_invoice()
        if confirm(f"Cancel {s['invoice_no']} ({money(s['grand_total'])})? Items return to stock"):
            s = self.sales().cancel(s["sale_id"], ask("Reason"))
            print("  ✔ Invoice cancelled; stock restored." +
                  (f" Refund {money(s['amount_paid'])} to the customer." if s["amount_paid"] else ""))

    # ------------------------------------------------------------ products
    def product_menu(self) -> None:
        self.submenu("PRODUCTS & STOCK", [
            ("List products", self.list_products), ("Search products", lambda: print_products(self.products().search(ask("Keyword")))),
            ("Product details & stock ledger", self.product_details),
            ("Add product", self.add_product, "products.manage"), ("Update product", self.update_product, "products.manage"),
            ("Discontinue / reactivate product", self.toggle_product, "products.manage"),
            ("Delete product", self.delete_product, "products.manage"),
            ("Stock adjustment (damage, expiry, audit)", self.adjust_stock, "stock.adjust"),
            ("Low & out-of-stock products", self.stock_alerts), ("Reorder suggestions", self.reorder)])

    def list_products(self) -> None:
        cat = choose("Category (blank = all)", CategoryManager(self.db).names(), allow_blank=True) or None
        sort = choose("Sort by", list(ProductManager.SORTS))
        print_products(self.products().list(cat, confirm("Include discontinued?"), sort))

    def product_details(self) -> None:
        p = self.pick_product(include_inactive=True)
        header(f"{p['product_id']} — {p['name']} {p['brand']}".strip())
        for label, val in [("Category", p["category"]), ("Unit", p["unit"]), ("HSN", p["hsn"]), ("GST", f"{p['gst_rate']:g}%"),
                           ("Selling price", f"{money(p['selling_price'])} (+GST = {money(ProductManager.price_with_gst(p))})"),
                           ("MRP", money(p["mrp"]) if p["mrp"] else "-"), ("Last purchase price", money(p["purchase_price"])),
                           ("Average cost", money(p["avg_cost"])), ("Stock", f"{p['stock']:g} {p['unit']}"),
                           ("Reorder level", f"{p['reorder_level']:g}"), ("SKU / Barcode", f"{p['sku'] or '-'} / {p['barcode'] or '-'}"),
                           ("Location", p["location"] or "-"), ("Status", "active" if p["active"] else "discontinued")]:
            print(f"  {label:<20}: {val}")
        if can(self.user, "reports"):
            margin = (p["selling_price"] - p["avg_cost"]) / p["selling_price"] * 100
            print(f"  {'Margin on cost':<20}: {margin:.1f}%")
        print("\n  Stock ledger (latest 15):")
        for m in self.products().ledger(p["product_id"])[-15:]:
            print(f"   {m['at'][:16].replace('T', ' ')}  {m['type']:<12}{m['qty']:>+10g}{m['balance']:>10g}  {m['ref']:<20}{m['by']}")

    def add_product(self) -> None:
        header("ADD PRODUCT")
        cm = CategoryManager(self.db)
        name = ask("Product name")
        brand = ask("Brand (optional)")
        cat = cm.get(choose("Category", cm.names()))
        unit = choose("Unit", UNITS)
        gst = ask(f"GST % ({'/'.join(f'{r:g}' for r in GST_RATES)})", f"{cat['gst_rate']:g}")
        hsn = ask("HSN code", cat["hsn"] or None)
        cost = ask("Purchase price (excl. GST)")
        selling = ask("Selling price (excl. GST)")
        mrp = ask("MRP incl. GST (optional)")
        p = self.products().add(name, cat["name"], unit, cost, selling, ask("Opening stock", "0"),
                                ask("Reorder level", "10"), gst, hsn, brand, ask("SKU (optional)"),
                                ask("Barcode (optional)"), mrp or None, ask("Rack / location (optional)"))
        print(f"  ✔ {p['name']} added as {p['product_id']} with {p['stock']:g} {p['unit']} in stock.")
        if p["selling_price"] <= p["purchase_price"]:
            print("  ⚠ Selling price is not above the purchase price.")

    def update_product(self) -> None:
        p = self.pick_product(include_inactive=True)
        print("  Leave blank to keep the current value.")
        fields = [("name", "Name"), ("brand", "Brand"), ("selling_price", "Selling price"), ("mrp", "MRP"),
                  ("gst_rate", "GST %"), ("hsn", "HSN"), ("reorder_level", "Reorder level"), ("location", "Location"),
                  ("sku", "SKU"), ("barcode", "Barcode")]
        changes = {}
        for key, label in fields:
            cur = p[key]
            shown = f"{cur:g}" if isinstance(cur, float) else (cur or None)
            v = ask(label, shown)
            if v and v != (shown or ""):
                changes[key] = v
        if confirm("Change category?"):
            changes["category"] = choose("Category", CategoryManager(self.db).names())
        if not changes:
            print("  No changes.")
            return
        self.products().update(p["product_id"], **changes)
        print(f"  ✔ Updated: {', '.join(changes)}.")

    def toggle_product(self) -> None:
        p = self.pick_product(include_inactive=True)
        self.products().set_active(p["product_id"], not p["active"])
        print(f"  ✔ {p['name']} is now {'discontinued' if p['active'] else 'active'}.")

    def delete_product(self) -> None:
        p = self.pick_product(include_inactive=True)
        if confirm(f"Delete {p['product_id']} {p['name']}?"):
            self.products().delete(p["product_id"])
            print("  ✔ Deleted.")

    def adjust_stock(self) -> None:
        p = self.pick_product()
        print(f"  Current stock: {p['stock']:g} {p['unit']}")
        reason = choose("Reason", ADJUST_REASONS)
        qty = ask("Quantity change (negative to remove, e.g. -3)")
        mv = self.products().adjust_stock(p["product_id"], qty, reason, ask("Note (optional)"))
        print(f"  ✔ Stock is now {mv['balance']:g} {p['unit']}.")

    def stock_alerts(self) -> None:
        header("OUT OF STOCK")
        print_products(self.products().out_of_stock())
        header("LOW STOCK (at or below reorder level)")
        print_products(self.products().low_stock())

    def reorder(self) -> None:
        sugg = self.products().reorder_suggestions()
        header("REORDER SUGGESTIONS")
        if not sugg:
            print("  All products are above their reorder levels.")
            return
        names = {s["supplier_id"]: s["name"] for s in self.suppliers().list(include_inactive=True)}
        for r in sugg:
            p = r["product"]
            print(f"  {p['product_id']:<7}{p['name'][:28]:<29}stock {p['stock']:>6g}/{p['reorder_level']:<6g}"
                  f"order {r['suggested_qty']:>6g} {p['unit']:<5}≈{money(r['estimated_cost']):>12}  "
                  f"{names.get(r['last_supplier'], '')}")
        print(f"\n  Estimated cost of all suggestions: {money(sum(r['estimated_cost'] for r in sugg))}")

    # ---------------------------------------------------------- categories
    def category_menu(self) -> None:
        cm = CategoryManager(self.db, self.actor)

        def listing():
            counts = cm.product_counts()
            for c in cm.list():
                print(f"  {c['name']:<20}GST {c['gst_rate']:>5g}%  HSN {c['hsn'] or '-':<9}{counts.get(c['name'], 0):>4} product(s)"
                      f"  {c['description']}")

        def edit():
            c = cm.get(choose("Category", cm.names()))
            cm.update(c["name"], ask("Name", c["name"]), ask("Default GST %", f"{c['gst_rate']:g}"),
                      ask("Default HSN", c["hsn"] or None), ask("Description", c["description"] or None))
            print("  ✔ Updated. (Existing products keep their own GST rate.)")
        self.submenu("CATEGORIES", [
            ("List categories", listing),
            ("Add category", lambda: print(f"  ✔ Added '{cm.add(ask('Name'), ask('Default GST %', '18'), ask('Default HSN (optional)'), ask('Description'))['name']}'.")),
            ("Edit category", edit),
            ("Delete category", lambda: (cm.delete(choose("Category", cm.names())), print("  ✔ Deleted.")))])

    # ------------------------------------------------------- party menus
    def _party_form(self, mgr, current: dict | None = None) -> dict:
        c = current or {}
        data = {"name": ask("Name", c.get("name")), "contact_person": ask("Contact person", c.get("contact_person") or None),
                "phone": ask("Phone", c.get("phone") or None), "email": ask("Email", c.get("email") or None),
                "gstin": ask("GSTIN (optional; sets the state)", c.get("gstin") or None),
                "address": ask("Address", c.get("address") or None)}
        if not data["gstin"]:
            data["state"] = ask("State", c.get("state") or utils.BUSINESS_STATE)
        return data

    def supplier_menu(self) -> None:
        mgr = self.suppliers()

        def listing():
            for s in mgr.list(include_inactive=True):
                print(f"  {s['supplier_id']:<9}{s['name'][:28]:<29}{s['phone']:<13}{s['state'][:14]:<15}"
                      f"{s['gstin'] or '-':<17}{'' if s['active'] else 'inactive'}")

        def statement():
            st = mgr.statement(self.pick_party(mgr)["supplier_id"])
            s = st["supplier"]
            header(f"{s['supplier_id']} — {s['name']}")
            print(f"  {s['contact_person'] or '-'} · {s['phone']} · {s['email'] or '-'} · GSTIN {s['gstin'] or '-'} · {s['state']}")
            print(f"  Billed {money(st['billed'])} · paid {money(st['paid'])} · PAYABLE {money(st['payable'])}")
            for p in st["purchases"][:15]:
                print(f"   {p['purchase_id']:<9}{p['date']:<12}{p['status']:<11}{money(p['grand_total']):>13}  {p['payment_status']}")

        def payables():
            rows = mgr.payables()
            for r in rows:
                print(f"  {r['supplier']['supplier_id']:<9}{r['supplier']['name'][:30]:<31}{money(r['payable']):>14}")
            print(f"\n  Total payable: {money(sum(r['payable'] for r in rows))}")
        self.submenu("SUPPLIERS", [
            ("List suppliers", listing),
            ("Add supplier", lambda: print(f"  ✔ Added {mgr.add(**self._party_form(mgr))['supplier_id']}.")),
            ("Supplier details & purchase history", statement),
            ("Update supplier", lambda: (lambda s: (mgr.update(s["supplier_id"], **self._party_form(mgr, s)),
                                                    print("  ✔ Updated.")))(self.pick_party(mgr))),
            ("Activate / deactivate supplier", lambda: (lambda s: (mgr.set_active(s["supplier_id"], not s["active"]),
                                                                   print("  ✔ Done.")))(mgr.get(ask("Supplier ID")))),
            ("Delete supplier", lambda: (mgr.delete(ask("Supplier ID")), print("  ✔ Deleted."))),
            ("Amounts payable", payables)])

    def customer_menu(self) -> None:
        mgr = self.customers()

        def listing():
            for c in mgr.list(include_inactive=True):
                print(f"  {c['customer_id']:<10}{c['name'][:28]:<29}{c['phone'] or '-':<13}{c['state'][:14]:<15}"
                      f"{c['gstin'] or '-':<17}{'' if c['active'] else 'inactive'}")

        def history():
            h = mgr.history(self.pick_party(mgr)["customer_id"])
            c = h["customer"]
            header(f"{c['customer_id']} — {c['name']}")
            print(f"  {c['phone'] or '-'} · {c['email'] or '-'} · GSTIN {c['gstin'] or '-'} · {c['state']}")
            print(f"  {h['invoices']} invoice(s) · billed {money(h['billed'])} · paid {money(h['paid'])} · "
                  f"RECEIVABLE {money(h['receivable'])} · last purchase {h['last_purchase'] or '-'}")
            for s in h["sales"][:15]:
                print(f"   {s['invoice_no']:<20}{s['date']:<12}{money(s['grand_total']):>13}  {s['payment_status']}")

        def receivables():
            rows = mgr.receivables()
            for r in rows:
                print(f"  {r['customer']['customer_id']:<10}{r['customer']['name'][:30]:<31}{money(r['receivable']):>14}"
                      f"   oldest due {r['oldest_due']}")
            print(f"\n  Total receivable: {money(sum(r['receivable'] for r in rows))}")
        self.submenu("CUSTOMERS", [
            ("List customers", listing),
            ("Add customer", lambda: print(f"  ✔ Added {mgr.add(**self._party_form(mgr))['customer_id']}.")),
            ("Customer details & purchase history", history),
            ("Update customer", lambda: (lambda c: (mgr.update(c["customer_id"], **self._party_form(mgr, c)),
                                                    print("  ✔ Updated.")))(self.pick_party(mgr))),
            ("Activate / deactivate customer", lambda: (lambda c: (mgr.set_active(c["customer_id"], not c["active"]),
                                                                   print("  ✔ Done.")))(mgr.get(ask("Customer ID")))),
            ("Delete customer", lambda: (mgr.delete(ask("Customer ID")), print("  ✔ Deleted."))),
            ("Amounts receivable", receivables)])

    # ----------------------------------------------------------- purchases
    def purchase_menu(self) -> None:
        self.submenu("PURCHASES", [
            ("New purchase / purchase order", self.new_purchase), ("Receive goods for an order", self.receive_order),
            ("Pay supplier", self.pay_supplier), ("View purchase", self.view_purchase),
            ("Purchase list", self.purchase_list), ("Cancel purchase order", self.cancel_order)])

    def new_purchase(self) -> None:
        header("NEW PURCHASE")
        sup = self.pick_party(self.suppliers())
        items = []
        print("  Add items. Leave the product blank when done.")
        while True:
            try:
                q = ask("Product (blank = done)")
                if not q:
                    break
                pm = self.products()
                try:
                    p = pm.get(q)
                except InventoryError:
                    m = pm.search(q, include_inactive=True)
                    if not m:
                        print("    ✖ Not found.")
                        continue
                    if len(m) > 1:
                        for i, x in enumerate(m[:15], 1):
                            print(f"     {i:>2}. {x['name']} {x['brand']} (stock {x['stock']:g})")
                        n = ask("Select number")
                        if not (n.isdigit() and 1 <= int(n) <= min(len(m), 15)):
                            continue
                        p = m[int(n) - 1]
                    else:
                        p = m[0]
                trial = items + [{"product_id": p["product_id"], "qty": ask(f"Quantity ({p['unit']})"),
                                  "cost": ask("Unit cost excl. GST", f"{p['purchase_price']:.2f}"),
                                  "discount_pct": ask("Trade discount %", "0")}]
                self.purchases().build_lines(trial)              # validates before accepting
                items = trial
                print(f"    ✔ {p['name']} added ({len(items)} item(s)).")
            except (InventoryError, ValueError) as exc:
                print(f"    ✖ {exc}")
        if not items:
            print("  Nothing to purchase.")
            return
        receive = confirm("Goods received now? (n = save as purchase order)")
        po = self.purchases().create(sup["supplier_id"], items, ask("Supplier invoice no. (optional)"), receive_now=receive)
        header(f"{po['purchase_id']} — {po['status']}")
        print_doc_totals(po)
        if receive:
            print("  ✔ Stock updated and average costs recalculated.")
            if confirm("Record a payment to the supplier now?"):
                self._pay(po)

    def _pay(self, po: dict) -> None:
        mode = choose("Mode", [m for m in PAYMENT_MODES if m != "Credit"])
        po = self.purchases().pay(po["purchase_id"], ask("Amount", f"{po['grand_total'] - po['amount_paid']:.2f}"), mode,
                                  ask("Reference") if mode != "Cash" else "")
        print(f"  ✔ Payment recorded. {po['payment_status']} (paid {money(po['amount_paid'])} of {money(po['grand_total'])}).")

    def receive_order(self) -> None:
        orders = self.purchases().list("ORDERED")
        for o in orders:
            print(f"  {o['purchase_id']:<9}{o['date']:<12}{o['supplier_name'][:28]:<29}{money(o['grand_total']):>13}")
        if not orders:
            print("  No pending purchase orders.")
            return
        po = self.purchases().receive(ask("Purchase ID"), supplier_invoice=ask("Supplier invoice no. (optional)") or None)
        print(f"  ✔ {po['purchase_id']} received; stock updated.")

    def pay_supplier(self) -> None:
        unpaid = [p for p in self.purchases().list("RECEIVED") if p["payment_status"] != "PAID"]
        for p in unpaid[:20]:
            print(f"  {p['purchase_id']:<9}{p['date']:<12}{p['supplier_name'][:26]:<27}"
                  f"due {money(p['grand_total'] - p['amount_paid'])}")
        if not unpaid:
            print("  No unpaid purchases.")
            return
        self._pay(self.purchases().get(ask("Purchase ID")))

    def view_purchase(self) -> None:
        p = self.purchases().get(ask("Purchase ID"))
        header(f"{p['purchase_id']} — {p['supplier_name']} — {p['status']}")
        print(f"  Date {p['date']} · received {p['received_on'] or '-'} · supplier invoice {p['supplier_invoice'] or '-'}")
        for l in p["lines"]:
            print(f"  {l['name'][:32]:<33}{l['qty']:>7g} {l['unit']:<4} x {l['rate']:>9,.2f}  {l['gst_rate']:>4g}%"
                  f"{money(l['total']):>13}")
        line()
        print_doc_totals(p)
        print(f"  Paid {money(p['amount_paid'])} · {p['payment_status']}")

    def purchase_list(self) -> None:
        start, end = period()
        for p in self.purchases().list(start=start, end=end):
            print(f"  {p['purchase_id']:<9}{p['date']:<12}{p['supplier_name'][:26]:<27}{money(p['grand_total']):>13}  "
                  f"{p['status']:<10}{p['payment_status']}")

    def cancel_order(self) -> None:
        self.purchases().cancel(ask("Purchase ID"), ask("Reason"))
        print("  ✔ Purchase order cancelled.")

    # ------------------------------------------------------------- reports
    def report_menu(self) -> None:
        rg = self.reports()

        def stock():
            r = rg.stock_report()
            header("STOCK REPORT")
            print(f"  {r['products']} products · {r['units']:g} units · cost value {money(r['cost_value'])} · "
                  f"selling value {money(r['selling_value'])} · potential margin {money(r['potential_margin'])}")
            for c, v in r["by_category"].items():
                print(f"    {c:<20}{v['products']:>4} products {money(v['cost_value']):>15} {money(v['selling_value']):>15}")
            print(f"\n  Low stock: {r['low_stock']} · out of stock: {r['out_of_stock']}")

        def sales():
            r = rg.sales_report(*period())
            header(f"SALES {r['start']} → {r['end']}")
            print(f"  Invoices {r['invoices']} (cancelled {r['cancelled']}) · average bill {money(r['avg_bill'])}")
            for label, key in [("Gross", "gross"), ("Discounts", "discount"), ("Taxable", "taxable"), ("CGST", "cgst"),
                               ("SGST", "sgst"), ("IGST", "igst"), ("Total incl. GST", "grand_total"),
                               ("Received", "amount_paid"), ("Outstanding", "outstanding")]:
                print(f"    {label:<18}{money(r[key]):>16}")
            print("\n  By payment mode:")
            for m, v in r["by_mode"].items():
                print(f"    {m:<22}{money(v):>16}")

        def profit():
            r = rg.profit_report(*period())
            header(f"PROFIT {r['start']} → {r['end']}")
            print(f"  Revenue (taxable) {money(r['revenue'])} · cost of goods {money(r['cogs'])} · "
                  f"GROSS PROFIT {money(r['gross_profit'])} ({r['margin']}%)")
            print("\n  By category:")
            for c, v in r["by_category"].items():
                print(f"    {c:<18}{money(v['revenue']):>14}{money(v['profit']):>14}{v['margin']:>7}%")
            print("\n  Top products by profit:")
            for p in r["top_by_profit"]:
                print(f"    {p['name'][:30]:<31}{p['qty']:>8g} {p['unit']:<5}{money(p['profit']):>14}{p['margin']:>7}%")

        def gst():
            r = rg.gst_report(*period())
            header(f"GST SUMMARY {r['start']} → {r['end']}")
            for label, rates, tot in (("Output GST (sales)", r["output"], r["output_total"]),
                                      ("Input GST (purchases)", r["input"], r["input_total"])):
                print(f"  {label}")
                for rate, v in rates.items():
                    print(f"    {rate:>5}%  taxable {money(v['taxable']):>14}  CGST {money(v['cgst']):>11}  "
                          f"SGST {money(v['sgst']):>11}  IGST {money(v['igst']):>11}")
                print(f"    Total GST {money(tot['tax'])}\n")
            print(f"  NET GST PAYABLE (output - input): {money(r['net_payable'])}")

        def purchases():
            r = rg.purchase_report(*period())
            header(f"PURCHASES {r['start']} → {r['end']}")
            print(f"  {r['bills']} bills · taxable {money(r['taxable'])} · GST {money(r['tax'])} · total {money(r['total'])}"
                  f" · paid {money(r['paid'])}")
            for s, v in r["by_supplier"].items():
                print(f"    {s[:30]:<31}{v['bills']:>3} bills {money(v['total']):>14}  paid {money(v['paid'])}")
            print(f"\n  Open purchase orders: {len(r['open_orders'])}")

        saved = lambda p: print(f"  ✔ Saved: {p}")  # noqa: E731

        def exports():
            self.submenu("CSV EXPORTS", [
                ("Stock", lambda: saved(rg.stock_csv())), ("Reorder list", lambda: saved(rg.reorder_csv())),
                ("Sales register", lambda: saved(rg.sales_csv(*period()))),
                ("Purchase register", lambda: saved(rg.purchases_csv(*period()))),
                ("Profit by product", lambda: saved(rg.profit_csv(*period()))),
                ("GST summary", lambda: saved(rg.gst_csv(*period()))),
                ("Customers", lambda: saved(rg.parties_csv("customers"))),
                ("Suppliers", lambda: saved(rg.parties_csv("suppliers"))),
                ("Stock ledger of a product", lambda: saved(rg.ledger_csv(self.pick_product(include_inactive=True)["product_id"])))])
        self.submenu("REPORTS", [
            ("Stock summary", stock), ("Low & out-of-stock", self.stock_alerts), ("Sales report", sales),
            ("Profit report", profit), ("Purchase report", purchases), ("GST summary (output vs input)", gst),
            ("Stock report (PDF)", lambda: saved(rg.stock_pdf())),
            ("Sales & profit report (PDF)", lambda: saved(rg.sales_profit_pdf(*period()))),
            ("CSV exports", exports)])

    # --------------------------------------------------------------- admin
    def admin_menu(self) -> None:
        um, panel = UserManager(self.db, self.actor), AdminPanel(self.db, self.report_dir)

        def users():
            for u in um.list():
                state = "LOCKED" if u["failed_attempts"] >= 5 else ("active" if u["active"] else "inactive")
                print(f"  {u['username']:<14}{u['name'][:22]:<23}{u['role']:<13}{state:<10}"
                      f"last login {(u['last_login'] or '-').replace('T', ' ')}")

        def add_user():
            u, temp = um.add(ask("Username"), ask("Full name"), choose("Role", ROLES), ask("Phone (optional)"),
                             ask("Email (optional)"))
            print(f"  ✔ {u['username']} created. Temporary password: {temp}")

        def restore():
            backups = self.backup.list_backups()
            for i, b in enumerate(backups, 1):
                print(f"  {i:>2}. {b.name}")
            n = ask("Backup number to restore")
            if n.isdigit() and 1 <= int(n) <= len(backups) and confirm("Replace ALL current data?"):
                safety = self.backup.restore(backups[int(n) - 1])
                print(f"  ✔ Restored. Previous data saved as {safety.name}. Please log in again.")
                self.user = None
        self.submenu("ADMIN PANEL", [
            ("List users", users), ("Add user", add_user),
            ("Change user role", lambda: (um.set_role(ask("Username"), choose("Role", ROLES)), print("  ✔ Updated."))),
            ("Activate / deactivate user", lambda: (lambda u: (um.set_active(u["username"], not u["active"]),
                                                               print("  ✔ Done.")))(um.get(ask("Username")))),
            ("Reset password / unlock", lambda: print(f"  ✔ Temporary password: {self.auth.reset_password(ask('Username'), self.actor)}")),
            ("Activity log", lambda: [print(f"  {a['at'].replace('T', ' ')}  {a['user']:<12}{a['action']:<22}{a['details']}")
                                      for a in panel.activity(40, ask("Filter by user (blank = all)") or None)]),
            ("System statistics", lambda: [print(f"  {k:<16}{v:>7} record(s)") for k, v in panel.system_stats().items()]),
            ("Create backup", lambda: print(f"  ✔ Backup created: {self.backup.create_backup().name}")),
            ("List backups", lambda: print("\n".join(f"  {b.name}" for b in self.backup.list_backups()) or "  None.")),
            ("Restore backup", restore)])


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except InventoryError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
