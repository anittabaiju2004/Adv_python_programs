"""Unit tests — run with:  python -m pytest -q"""
import json
from datetime import date, timedelta

import pytest

from inventory.admin import AdminPanel
from inventory.auth import AuthManager, UserManager, can, require
from inventory.backup import BackupManager
from inventory.categories import CategoryManager
from inventory.customers import CustomerManager
from inventory.database import JSONDatabase
from inventory.products import ProductManager
from inventory.purchases import PurchaseManager
from inventory.reports import ReportGenerator
from inventory.sales import SalesManager, compute_lines
from inventory.suppliers import SupplierManager
from inventory.utils import (WALK_IN_CUSTOMER, AuthenticationError, BackupError, DatabaseError, InventoryError,
                             NotFoundError, PermissionDenied, StockError, ValidationError, financial_year,
                             gst_split, rupees_in_words, validate_gstin, validate_qty)

TODAY = date.today()


@pytest.fixture
def db(tmp_path):
    d = JSONDatabase(tmp_path / "data")
    AuthManager(d)
    CustomerManager(d)
    return d


@pytest.fixture
def pm(db):
    return ProductManager(db, "tester")


@pytest.fixture
def rice(pm):
    return pm.add("Basmati Rice", "Groceries", "kg", 80, 110, opening_stock=50, reorder_level=10, brand="India Gate")


@pytest.fixture
def soap(pm):
    return pm.add("Bath Soap 100g", "Personal Care", "pcs", 25, 38, opening_stock=100, reorder_level=20, mrp=45)


@pytest.fixture
def local_sup(db):
    return SupplierManager(db).add("Kerala Foods Ltd", "9847000001", gstin="32AAACK1234L1Z5")


@pytest.fixture
def tn_sup(db):
    return SupplierManager(db).add("Chennai Distributors", "9840000002", gstin="33AABCC5678M1Z2")


@pytest.fixture
def b2b(db):
    return CustomerManager(db).add("Bangalore Retail Mart", "9900000003", gstin="29AAFCB4321K1ZX")


# ================================================================ utilities
def test_gst_and_helpers():
    assert gst_split(1000, 18, False) == {"cgst": 90, "sgst": 90, "igst": 0, "tax": 180}
    assert gst_split(1000, 18, True) == {"cgst": 0, "sgst": 0, "igst": 180, "tax": 180}
    assert gst_split(91, 5, False)["cgst"] + gst_split(91, 5, False)["sgst"] == 4.55
    assert validate_gstin("29aafcb4321k1zx") == ("29AAFCB4321K1ZX", "Karnataka")
    with pytest.raises(ValidationError):
        validate_gstin("99AAFCB4321K1ZX")                         # unknown state code
    assert validate_qty("2.5", "kg") == 2.5
    with pytest.raises(ValidationError):
        validate_qty("2.5", "pcs")
    assert financial_year(date(2027, 3, 31)) == "2026-27"
    assert rupees_in_words(414) == "Four Hundred Fourteen Rupees Only"


def test_compute_lines_discount_and_round_off():
    d = compute_lines([{"qty": 3, "rate": 100, "discount_pct": 10, "gst_rate": 18},
                       {"qty": 2, "rate": 45.5, "gst_rate": 5}], inter_state=False)
    assert (d["gross"], d["discount"], d["taxable"], d["tax"]) == (391, 30, 361, 53.15)
    assert d["grand_total"] == 414 and d["round_off"] == -0.15
    assert d["gst_summary"]["18"] == {"taxable": 270, "cgst": 24.3, "sgst": 24.3, "igst": 0}


# ===================================================================== auth
def test_users_and_permissions(db):
    um = UserManager(db, "admin")
    user, temp = um.add("cashier1", "Asha", "cashier")
    auth = AuthManager(db)
    u = auth.login("cashier1", temp)
    assert u["must_change_password"] and can(u, "sales") and not can(u, "purchases")
    with pytest.raises(PermissionDenied):
        require(u, "reports")
    um.set_active("cashier1", False)
    with pytest.raises(AuthenticationError, match="disabled"):
        auth.login("cashier1", temp)
    with pytest.raises(InventoryError):
        um.set_role("admin", "cashier")                     # only admin
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            auth.login("admin", "nope")
    with pytest.raises(AuthenticationError, match="locked"):
        auth.login("admin", "admin123")


# ========================================================= categories/products
def test_categories(db, rice):
    cm = CategoryManager(db)
    assert cm.get("groceries")["gst_rate"] == 5
    cm.add("Dairy", 5, "0401")
    with pytest.raises(ValidationError):
        cm.add("dairy", 5)
    with pytest.raises(ValidationError):
        cm.add("Toys", 12)                                   # 12 % slab no longer exists
    with pytest.raises(InventoryError):
        cm.delete("Groceries")
    cm.update("Groceries", new_name="Food Grains")
    assert ProductManager(db).get(rice["product_id"])["category"] == "Food Grains"


def test_product_rules(pm, rice, soap):
    assert rice["product_id"] == "P0001" and rice["gst_rate"] == 5 and rice["hsn"] == "1006" and rice["stock"] == 50
    assert soap["gst_rate"] == 5 and ProductManager.price_with_gst(soap) == 39.9
    with pytest.raises(ValidationError, match="MRP"):
        pm.add("Shampoo", "Personal Care", "pcs", 80, 120, mrp=100)
    with pytest.raises(ValidationError, match="already exists"):
        pm.add("basmati rice", "Groceries", "kg", 80, 110, brand="India Gate")
    with pytest.raises(ValidationError):
        pm.update(rice["product_id"], stock=999)
    assert pm.update(rice["product_id"], selling_price=115)["selling_price"] == 115
    assert [p["product_id"] for p in pm.search("india gate")] == [rice["product_id"]]
    with pytest.raises(InventoryError):
        pm.update(rice["product_id"], unit="pcs")           # has stock history


def test_stock_adjustment_and_alerts(pm, rice, soap):
    pm.adjust_stock(soap["product_id"], -85, "Damaged", "Water leak")
    assert pm.get(soap["product_id"])["stock"] == 15
    assert [p["product_id"] for p in pm.low_stock()] == [soap["product_id"]]
    with pytest.raises(StockError):
        pm.adjust_stock(soap["product_id"], -20, "Lost / Theft")
    pm.adjust_stock(soap["product_id"], -15, "Expired")
    assert [p["product_id"] for p in pm.out_of_stock()] == [soap["product_id"]]
    sug = pm.reorder_suggestions()[0]
    assert sug["product"]["product_id"] == soap["product_id"] and sug["suggested_qty"] == 40
    assert [m["type"] for m in pm.ledger(soap["product_id"])] == ["OPENING", "ADJUSTMENT", "ADJUSTMENT"]


# ================================================================== parties
def test_parties(db, local_sup, tn_sup, b2b):
    assert local_sup["state"] == "Kerala" and tn_sup["state"] == "Tamil Nadu" and b2b["state"] == "Karnataka"
    with pytest.raises(ValidationError, match="belongs to"):
        SupplierManager(db).add("X Traders", "9000000009", gstin="33AABCC9999M1Z2", state="Kerala")
    with pytest.raises(ValidationError):
        SupplierManager(db).add("Y Traders", "9847000001")    # duplicate phone
    cm = CustomerManager(db)
    assert cm.get(WALK_IN_CUSTOMER)["name"] == "Walk-in Customer"
    with pytest.raises(InventoryError):
        cm.delete(WALK_IN_CUSTOMER)
    assert [c["customer_id"] for c in cm.search("bangalore")] == [b2b["customer_id"]]


# ================================================================= purchases
def test_purchase_order_receive_and_average_cost(db, pm, rice, local_sup, tn_sup):
    pur = PurchaseManager(db, "store")
    po = pur.create(local_sup["supplier_id"], [{"product_id": rice["product_id"], "qty": 50, "cost": 90}],
                    "KF/889", receive_now=False)
    assert po["status"] == "ORDERED" and pm.get(rice["product_id"])["stock"] == 50
    po = pur.receive(po["purchase_id"])
    p = pm.get(rice["product_id"])
    assert p["stock"] == 100 and p["avg_cost"] == 85 and p["purchase_price"] == 90     # (50x80 + 50x90) / 100
    assert po["cgst"] == po["sgst"] == 112.5 and po["igst"] == 0                       # intra-state, 5 %
    inter = pur.create(tn_sup["supplier_id"], [{"product_id": rice["product_id"], "qty": 10, "cost": 100,
                                               "discount_pct": 10}])
    assert inter["igst"] == 45 and inter["cgst"] == 0                                  # 900 taxable x 5 %
    assert pm.get(rice["product_id"])["avg_cost"] == round((100 * 85 + 10 * 90) / 110, 4)
    pur.pay(po["purchase_id"], 2000, "Bank Transfer", "NEFT1")
    assert pur.get(po["purchase_id"])["payment_status"] == "PARTIAL"
    assert SupplierManager(db).statement(local_sup["supplier_id"])["payable"] == po["grand_total"] - 2000
    with pytest.raises(ValidationError):
        pur.pay(po["purchase_id"], 99999, "Cash")
    o2 = pur.create(local_sup["supplier_id"], [{"product_id": rice["product_id"], "qty": 5}], receive_now=False)
    pur.cancel(o2["purchase_id"], "Supplier out of stock")
    with pytest.raises(InventoryError):
        pur.receive(o2["purchase_id"])


# ===================================================================== sales
def test_sale_stock_profit_and_invoice(db, pm, rice, soap, tmp_path):
    sm = SalesManager(db, "cashier")
    s = sm.create(WALK_IN_CUSTOMER, [{"product_id": rice["product_id"], "qty": 2.5},
                                      {"product_id": soap["product_id"], "qty": 4, "discount_pct": 5}], "Cash")
    assert s["invoice_no"] == f"INV/{financial_year(TODAY)}/0001"
    assert pm.get(rice["product_id"])["stock"] == 47.5 and pm.get(soap["product_id"])["stock"] == 96
    assert s["taxable"] == round(2.5 * 110 + 4 * 38 * 0.95, 2) and s["igst"] == 0
    assert round(s["cgst"] + s["sgst"], 2) == s["tax"] and abs(s["cgst"] - s["sgst"]) <= 0.01   # odd paisa split
    assert s["cost"] == 2.5 * 80 + 4 * 25 and s["profit"] == round(s["taxable"] - s["cost"], 2)
    assert s["payment_status"] == "PAID" and s["amount_paid"] == s["grand_total"]
    with pytest.raises(StockError):
        sm.create(WALK_IN_CUSTOMER, [{"product_id": soap["product_id"], "qty": 500}])
    with pytest.raises(ValidationError, match="registered"):
        sm.create(WALK_IN_CUSTOMER, [{"product_id": soap["product_id"], "qty": 1}], "Credit")
    with pytest.raises(ValidationError, match="reference"):
        sm.create(WALK_IN_CUSTOMER, [{"product_id": soap["product_id"], "qty": 1}], "UPI")
    assert sm.invoice_pdf(s["invoice_no"], tmp_path).read_bytes()[:4] == b"%PDF"
    sm.cancel(s["sale_id"], "Customer returned all items")
    assert pm.get(rice["product_id"])["stock"] == 50 and pm.get(soap["product_id"])["stock"] == 100
    assert sm.list() == []


def test_credit_sale_inter_state_and_receivable(db, pm, rice, b2b):
    sm = SalesManager(db)
    s = sm.create(b2b["customer_id"], [{"product_id": rice["product_id"], "qty": 20}], "Credit")
    assert s["inter_state"] and s["igst"] == 110 and s["cgst"] == 0 and s["payment_status"] == "UNPAID"
    assert CustomerManager(db).history(b2b["customer_id"])["receivable"] == s["grand_total"]
    sm.receive_payment(s["invoice_no"], 1000, "UPI", "UPI77")
    s = sm.receive_payment(s["sale_id"], s["grand_total"] - 1000, "Cash")
    assert s["payment_status"] == "PAID" and CustomerManager(db).receivables() == []
    with pytest.raises(InventoryError):
        sm.receive_payment(s["sale_id"], 1, "Cash")


# =================================================================== reports
def test_reports_and_dashboard(db, pm, rice, soap, local_sup, b2b, tmp_path):
    PurchaseManager(db).create(local_sup["supplier_id"], [{"product_id": soap["product_id"], "qty": 50, "cost": 25}])
    sm = SalesManager(db)
    sm.create(WALK_IN_CUSTOMER, [{"product_id": rice["product_id"], "qty": 10}], "Cash")
    sm.create(b2b["customer_id"], [{"product_id": soap["product_id"], "qty": 10}], "Credit")
    rg = ReportGenerator(db, tmp_path)
    sr = rg.sales_report(TODAY, TODAY)
    assert sr["invoices"] == 2 and sr["outstanding"] > 0 and "Credit (outstanding)" in sr["by_mode"]
    pr = rg.profit_report(TODAY, TODAY)
    assert pr["revenue"] == 10 * 110 + 10 * 38 and pr["cogs"] == 10 * 80 + 10 * 25 and pr["gross_profit"] == 430
    g = rg.gst_report(TODAY, TODAY)
    assert g["output_total"]["tax"] == round(1100 * .05 + 380 * .05, 2) and g["input_total"]["tax"] == 62.5
    assert g["net_payable"] == round(g["output_total"]["tax"] - 62.5, 2)
    st = rg.stock_report()
    assert st["cost_value"] == round(40 * 80 + 140 * 25, 2)
    for path in (rg.stock_csv(), rg.reorder_csv(), rg.sales_csv(TODAY, TODAY), rg.purchases_csv(TODAY, TODAY),
                 rg.profit_csv(TODAY, TODAY), rg.gst_csv(TODAY, TODAY), rg.parties_csv("customers"),
                 rg.parties_csv("suppliers"), rg.ledger_csv(rice["product_id"]), rg.stock_pdf(),
                 rg.sales_profit_pdf(TODAY.replace(day=1), TODAY)):
        assert path.exists() and path.stat().st_size > 50
    d = AdminPanel(db, tmp_path).dashboard()
    assert d["today_invoices"] == 2 and d["receivable"] > 0 and d["payable"] > 0


# ============================================================ backup & db
def test_backup_and_persistence(db, pm, rice, tmp_path):
    bm = BackupManager(db.data_dir, tmp_path / "b")
    archive = bm.create_backup()
    pm.adjust_stock(rice["product_id"], -10, "Damaged")
    bm.restore(archive)
    assert ProductManager(JSONDatabase(db.data_dir)).get(rice["product_id"])["stock"] == 50
    assert json.loads((db.data_dir / "products.json").read_text())[0]["name"] == "Basmati Rice"
    (db.data_dir / "sales.json").write_text("[{oops")
    with pytest.raises(DatabaseError):
        SalesManager(db).list()
    bad = tmp_path / "b" / "inventory_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bm.restore(bad)
    with pytest.raises(NotFoundError):
        pm.get("P9999")
