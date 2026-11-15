# Inventory Management System

**Advanced Inventory & Stock Management Using Python and JSON File Handling**

A menu-driven inventory, purchasing and billing application for *Malabar Wholesale
Traders*. It manages products, categories, suppliers, customers, purchases, sales and
billing with **automatic stock updates**. It produces **GST tax invoices (PDF)** with
discounts and reports on stock, sales, profit and GST. It also has role-based logins,
an admin panel, CSV exports and backup & restore. All data is stored permanently in
JSON files.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: 28 products, suppliers, customers, 40 days of purchases & sales (~10 s)
python main.py
```

| Role | Login | Can use |
|---|---|---|
| Admin | `admin` / `admin123` | Everything, including users, activity log, backup & restore |
| Manager | `manager` / `manager1` | Sales (incl. cancel), products, stock adjustment, purchases, suppliers, customers, reports |
| Cashier | `cashier` / `cash1234` | Billing, product lookup, customers |
| Storekeeper | `store` / `store123` | Products, categories, stock adjustment, purchases, suppliers |

The demo logins exist only after running `seed_demo.py`; `admin` is always created on
first run. Run the tests with `python -m pytest -q` (12 tests).

---

## Project structure

```
inventory_management/
├── main.py                   Entry point
├── seed_demo.py              Demo data loader
├── inventory/
│   ├── products.py           Product Management (CRUD, stock ledger, average cost, adjustments, alerts)
│   ├── categories.py         Category Management (default HSN & GST rate)
│   ├── suppliers.py          Supplier Management (statements, payables)
│   ├── customers.py          Customer Management (history, receivables)
│   ├── parties.py            Shared base class for suppliers & customers (GSTIN, state)
│   ├── purchases.py          Purchase Management (orders, goods receipt, supplier payments)
│   ├── sales.py              Sales & Billing (GST invoice maths, payments, cancel, PDF invoice)
│   ├── auth.py               Authentication & user management (hashing, roles, lockout, activity log)
│   ├── admin.py              Admin Panel (dashboard, statistics, activity log)
│   ├── reports.py            Reports (stock, sales, profit, purchases, GST; CSV & PDF)
│   ├── backup.py             Backup & Restore
│   ├── database.py           JSON Database
│   ├── utils.py              Business settings, GST rules, state codes, validation, helpers
│   └── cli.py                Role-based menu interface
├── tests/test_inventory.py   Unit tests (pytest)
├── data/                     users, categories, products, suppliers, customers, purchases, sales,
│                             stock_movements, activity (.json)
├── backups/                  Backup zip files
└── reports/                  Reports; invoices in reports/invoices/
```

---

## Modules

| Module | What it does |
|---|---|
| **Product Management** | Add, view, search (name, brand, ID, SKU, barcode), update, discontinue or reactivate, delete (only if never traded). Fields: unit (whole or decimal quantities), HSN, GST rate, purchase and selling price, MRP (selling price incl. GST may not exceed it), reorder level, SKU/barcode, rack location. A **stock ledger** records every movement (opening, purchase, sale, cancellation, adjustment) with the running balance. **Stock adjustments** for damage, expiry, theft or audit need a reason |
| **Category Management** | Categories with a default HSN code and GST rate for new products; rename (products follow) and delete (blocked while products exist) |
| **Supplier / Customer Management** | Shared `PartyManager` base class. The **GSTIN is validated and the state is detected from it**, which decides CGST+SGST or IGST. Supplier statement and payables; customer purchase history and receivables. A built-in walk-in customer handles cash sales; records with transactions are deactivated rather than deleted |
| **Purchase Management** | Purchase order → **goods receipt** (stock in) or receive immediately. Trade discounts; intra- or inter-state GST; **weighted-average cost** updated on receipt (GST is input credit, not cost). Part or full supplier payments; orders can be cancelled before receipt |
| **Sales & Billing** | Cart-style billing with product search, a stock check (no negative stock), and line discounts for allowed roles. GST per line with **CGST+SGST or IGST** by place of supply, round-off, and payment by cash (with change calculation), UPI, card, bank transfer or **credit** (registered customers only). Partial payments are supported. **Automatic stock deduction**; the cost of goods is captured at sale for profit. Invoices can be cancelled (stock is restored). Invoice numbers run per financial year (`INV/2026-27/0001`) |
| **Invoice (PDF)** | GST tax invoice with GSTINs, place of supply, HSN, qty, rate, discount, taxable value, GST rate and tax per line, a GST summary by rate, round-off, amount in words, and payment status |
| **Reports** | **Stock:** valuation at cost and selling price, by category, **low and out-of-stock**, **reorder suggestions** with estimated cost. **Sales:** totals, discounts, GST, collections by mode, outstanding. **Profit:** revenue vs cost of goods, margin by category and product, top sellers. **Purchases:** by supplier, open orders. **GST summary:** output vs input tax by rate, **net GST payable**. PDF stock report and sales & profit report; **CSV exports** for stock, reorder list, sales and purchase registers, profit, GST, customers, suppliers and a product's stock ledger |
| **Authentication** | PBKDF2-HMAC-SHA256 password hashing; lockout after 5 failed attempts; temporary passwords that must be changed at first login; role permissions decide which menus each user sees |
| **Admin Panel** | Dashboard: today's and this month's sales, gross profit, stock value, low and out-of-stock alerts, receivables, payables, top sellers. Also user management (add, change role, activate, reset or unlock), an activity log and system statistics |
| **Backup & Restore** | Timestamped zip backups. Restore checks the file first and automatically backs up the current data so a restore can be undone |
| **JSON Database** | Nine JSON files with atomic writes (temporary file, then `os.replace`) and a clear error if a file is damaged |

### GST rules used
- **Rates:** 0, 5, 18 and 40 %, the slabs in force since **22 September 2025**, plus the special 0.25 % and 3 % rates. The old 12 % and 28 % slabs are rejected.
- **Split:** a supply within Kerala carries CGST + SGST (half each); a supply to another state carries IGST.
- **Category defaults:** the GST rate and HSN code set on each category are sample values. Every product can override them, so check the correct HSN and rate for real items before real use.

### Exception handling
All errors derive from `InventoryError` (`ValidationError`, `NotFoundError`,
`AuthenticationError`, `PermissionDenied`, `StockError`, `DatabaseError`, `BackupError`)
and are shown as friendly messages instead of crashing.

### Configuration
Business name, address, GSTIN and state, allowed GST rates, units, payment modes and role
permissions are set in `inventory/utils.py`. Default categories are in
`inventory/categories.py`. Environment variables `INV_DATA_DIR`, `INV_BACKUP_DIR` and
`INV_REPORT_DIR` override the storage folders.

---

## Technologies
Python 3.10+, JSON, OOP (including inheritance for suppliers and customers), `datetime`,
`hashlib`/`hmac`, `csv`, `shutil`/`zipfile`, ReportLab, pytest. IDE: Visual Studio Code.

## Future enhancements
SQLite/MySQL · Barcode/QR scanning and label printing · Tkinter GUI · Django web
application · Cloud database · Mobile inventory app · Purchase/sales returns with credit
notes · E-invoicing (IRN) integration
