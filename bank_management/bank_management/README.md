# Bank Management System

**Advanced Banking Management Using Python, JSON File Handling, and Modular Programming**

A console banking application for *Python National Bank*. Customers open accounts with
KYC details at a branch, log in with a PIN, and deposit (cash or cheque), withdraw,
transfer by IMPS/NEFT/RTGS, check balances, view history and mini statements, open
fixed deposits, apply for loans and download PDF statements. Administrators manage
accounts, approve or reject loans, post monthly savings interest, monitor transactions,
generate reports and back up the JSON database.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py     # optional: 5 demo customers across 4 branches, 3 months of history
python bank.py
```

| Login | Credentials |
|---|---|
| Admin | `admin` / `admin123` (created on first run; change it in the admin panel) |
| Demo customers | account numbers are printed by `seed_demo.py`; every demo PIN is `2580` |

The demo data leaves one loan application pending, so the approval workflow can be
shown straight away. Run the tests with `python -m pytest -q` (28 tests).

---

## Project structure

```
bank_management/
├── bank.py           Main program: menus for customers and administrators
├── account.py        Registration (KYC), profile, interest calculator, fixed deposits, loans
├── auth.py           Customer PIN login, admin login, change PIN, lockout
├── transaction.py    Deposit, withdrawal, IMPS/NEFT/RTGS transfer, balance, history, mini statement, receipt
├── admin.py          Customers, freeze/unfreeze/delete, loan approval, savings interest, transaction monitor
├── database.py       JSON database (automatic load/save, atomic writes)
├── utils.py          Bank settings, branches, exceptions, validation, PIN hashing, EMI and interest formulas
├── report.py         PDF account statement, customer/transaction/loan CSV reports, bank summary
├── backup.py         Backup, list and restore the JSON database
├── seed_demo.py      Demo data loader
├── tests/test_bank.py Unit tests (pytest)
├── data/             customers.json · transactions.json · loans.json · fixed_deposits.json · admins.json
├── backups/          Backup zip files
└── reports/          Generated PDF and CSV reports
```

---

## System flow

1. The user starts the application, and the database is initialised (missing JSON files are created).
2. The main menu offers **Customer Login · Open New Account · Admin Login · Interest Calculator · Branch Directory**.
3. Customers perform banking operations, and administrators manage accounts.
4. Every transaction is saved to the JSON files immediately.
5. Reports and backups are generated from the admin panel.
6. The user exits safely.

---

## Modules

| # | Module | Implementation |
|---|---|---|
| 4.1 | Customer Registration | Name, date of birth (18+), PAN (`ABCDE1234F`), phone, email, address, nominee; branch selection; account types Savings / Current / Salary with minimum opening deposit; 11-digit account number = 3-digit branch code + 8 digits; IFSC assigned; duplicate PAN/phone/email prevented |
| 4.2 | Customer Login | Account number + PIN; account status check; **3 wrong PINs freeze the account** until an admin unfreezes it |
| 4.3 | Deposit | Cash or cheque (6-digit cheque number); amount validation; balance update; transaction saved; receipt |
| 4.4 | Withdrawal | PIN verified; minimum balance kept (Savings ₹1,000 · Current ₹5,000 · Salary ₹0); ₹1 lakh per transaction, ₹2 lakh per day; receipt |
| 4.5 | Fund Transfer | Beneficiary verified and shown (name, branch, IFSC) before confirming; PIN check; **IMPS / NEFT / RTGS** with per-mode limits (RTGS minimum ₹2 lakh); both transactions saved in one atomic update |
| 4.6 | Balance Inquiry | PIN-protected; ledger and available balance |
| 4.7 | Transaction History | All / deposits / withdrawals / transfers, with optional date range |
| 4.8 | Mini Statement | Last 5 transactions with credit/debit summary |
| 4.9 | Change PIN | Old PIN verified, new PIN confirmed, stored as a salted hash |
| 4.10 | Interest Calculator | SI = P × R × T / 100; interest and maturity amount |
| 4.11 | Loan Management | Personal, Education, Home, Vehicle and Gold loans, each with its own rate, maximum amount and tenure; **EMI on reducing balance**; application → **admin approval** → disbursal; repay EMIs; cancel pending applications; close completed loans; max 2 open loans |
| 4.12 | Fixed Deposit | Tenure-based rates (6–120 months), **+0.5 % for senior citizens (60+)**; FD ID; maturity date and amount; closing early pays 1 % less interest |
| 4.13 | PDF Statement | Account details, branch/IFSC, nominee, totals, all transactions, active FDs and loans; saved to `reports/` |
| 4.14 | Admin | Admin login; view and search customers (name, account no, phone, email, PAN); customer details; freeze/unfreeze; delete (blocked while loans or FDs are open; automatic backup first); loan applications; monthly savings interest (3 % p.a., never credited twice for a month); transaction monitor; reports |
| 4.15 | Backup | Timestamped zip of the 5 JSON files; list backups; restore checks the file first and backs up current data automatically so a restore can be undone |

### Reports
- **PDF account statement:** for any customer, available to both the customer and the admin.
- **Customer report (CSV):** PAN is masked as `ABXXXXX34F`.
- **Transaction report (CSV):** all accounts or one account, with an optional date range.
- **Loan report (CSV):** filter by status (Pending, Active, Closed or Rejected).
- **Bank summary:** customers, frozen accounts, deposits held, accounts per branch, FDs, loans and transactions by type.

### Security features
- **PIN hashing:** PBKDF2-HMAC-SHA256 with a random salt per customer. The admin password is hashed the same way.
- **Lockout:** the account is frozen after 3 wrong PIN attempts.
- **Re-verification:** the PIN is asked again for withdrawals, transfers, balance inquiry, FDs and loans.
- **Masked numbers:** account numbers and PAN are masked on screen, on receipts and in CSV exports.
- **KYC checks:** PAN, phone, email and age are validated, and one account per PAN/phone/email prevents duplicate accounts.
- **Clear errors:** custom exceptions such as `InsufficientFundsError`, `AccountFrozenError` and `LimitExceededError` are shown as friendly messages.

---

## Configuration
Branches and IFSC codes, minimum balances, limits, transfer modes, FD and loan rates, and
the savings interest rate are all set at the top of `utils.py`. Environment variables
`BANK_DATA_DIR`, `BANK_BACKUP_DIR` and `BANK_REPORT_DIR` override the storage folders.

## Technologies
Python 3.10+, JSON, OOP, `hashlib`/`hmac`, `datetime`, `csv`, `shutil`/`zipfile`,
ReportLab, pytest. IDE: Visual Studio Code.

## Future enhancements
MySQL/PostgreSQL · Tkinter/CustomTkinter GUI · Django web app · Mobile banking · OTP ·
Email/SMS alerts · ATM card management · QR/UPI payments · Online banking portal ·
AI fraud detection · Multi-branch dashboards · Internet banking
