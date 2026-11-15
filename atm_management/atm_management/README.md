# ATM Management System

**Advanced ATM Management Using Python, JSON File Handling, and Modular Programming**

A console application that simulates real ATM banking: account registration,
PIN login, deposits, withdrawals, fund transfers, balance inquiry, mini
statements, transaction history, fixed deposits, loans, an interest
calculator, PDF statements, and an administrator panel with reports and
backup & restore. All data is stored permanently in JSON files.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py     # optional: 4 demo customers with 3 months of history
python atm.py
```

| Login | Credentials |
|---|---|
| Admin | `admin` / `admin123` (created on first run; change it in the admin panel) |
| Demo customers | account numbers are printed by `seed_demo.py`; every demo PIN is `2580` |

Run the tests: `python -m pytest -q` (24 tests).

---

## Project structure

```
atm_management/
├── atm.py            Main program: menus, customer and admin screens
├── account.py        Registration, interest calculator, fixed deposits, loans
├── auth.py           Customer PIN login, admin login, change PIN, lockout
├── transaction.py    Deposit, withdrawal, transfer, balance, history, mini statement, receipt
├── admin.py          View, search, freeze, unfreeze, delete customers
├── database.py       JSON database (automatic load/save, atomic writes)
├── utils.py          Settings, exceptions, validation, PIN hashing, helpers
├── report.py         PDF statement, customer CSV, transaction CSV, system summary
├── backup.py         Backup, list and restore the JSON database
├── seed_demo.py      Demo data loader
├── tests/test_atm.py Unit tests (pytest)
├── data/             customers.json · transactions.json · loans.json · fixed_deposits.json · admins.json
├── backups/          Backup zip files
└── reports/          Generated PDF and CSV reports
```

---

## System flow

1. The program starts, and `database.py` loads (or creates) the JSON files.
2. The main menu offers **Customer Login · Open New Account · Admin Login · Interest Calculator**.
3. After authentication the customer or admin menu opens.
4. Every change is saved to JSON immediately.
5. Reports and backups can be generated from the admin panel.
6. The user logs out or exits.

---

## Modules

| # | Module | Implementation |
|---|---|---|
| 4.1 | Customer Registration | Name, phone (10-digit Indian mobile), email validation; unique 12-digit account number; 4-digit PIN (weak PINs such as 1111/1234 rejected); minimum opening deposit; duplicate phone/email prevention |
| 4.2 | Login Authentication | Account number + PIN; account status check; **3 wrong PINs freeze the account** until an admin unfreezes it |
| 4.3 | Deposit | Amount validation, per-transaction cap, balance update, transaction saved, optional receipt |
| 4.4 | Withdrawal | PIN re-verified; multiples of ₹100; ₹20,000 per transaction, ₹50,000 per day; minimum balance kept; quick-cash buttons |
| 4.5 | Fund Transfer | Receiver verified and name shown before confirming; PIN check; daily limit ₹1,00,000; both balances updated in **one atomic save** |
| 4.6 | Balance Inquiry | PIN-protected; ledger balance, available balance, amount withdrawn today |
| 4.7 | Transaction History | All / deposits / withdrawals / transfers, with optional date range |
| 4.8 | Mini Statement | Last 5 transactions, with credit/debit totals |
| 4.9 | Change PIN | Old PIN verified, new PIN confirmed, stored as a salted hash |
| 4.10 | Interest Calculator | SI = P × R × T / 100; shows interest and maturity amount |
| 4.11 | Fixed Deposit | Tenure-based rates (6–120 months); FD ID; maturity date and amount; closing early pays 1 % less interest |
| 4.12 | Loan Management | Personal, Education, Home and Vehicle loans; EMI quote before applying; repay from balance; auto-close when fully repaid; max 2 active loans |
| 4.13 | Report Generation | PDF account statement (ReportLab), customer report CSV, transaction report CSV, system summary |
| 4.14 | Backup | Timestamped zip of the 5 JSON files; list backups; restore checks the file first and saves current data automatically so a restore can be undone |
| 4.15 | Admin | Admin login, view and search customers, customer details, freeze/unfreeze, delete account (blocked while loans or FDs are active; automatic backup first), reports, backup/restore, change admin password |

### Security features
- **PIN hashing:** PBKDF2-HMAC-SHA256 with a random salt per customer. PINs are never stored in plain text.
- **Lockout:** the account is frozen after 3 wrong PIN attempts.
- **Re-verification:** the PIN is asked again for withdrawals, transfers, balance inquiry, FDs and loans.
- **Masked numbers:** account numbers are masked on screen and on receipts (`XXXXXX1698`).
- **Input checks:** every input is validated, and duplicate accounts are prevented.
- **Clear errors:** custom exceptions such as `InsufficientFundsError`, `AccountFrozenError` and `LimitExceededError` are shown as friendly messages.

### Database features
- One JSON file per collection, loaded and saved automatically.
- Writes are atomic (temporary file, then `os.replace`), so a crash cannot corrupt data.
- A corrupted file is reported clearly, with a prompt to restore a backup.

---

## Configuration
Limits, interest rates, minimum balances and the bank name are set at the top of
`utils.py`. Environment variables `ATM_DATA_DIR`, `ATM_BACKUP_DIR` and
`ATM_REPORT_DIR` override the storage folders.

## Technologies
Python 3.10+, JSON, OOP, `hashlib`/`hmac`, `datetime`, `csv`, `shutil`/`zipfile`,
ReportLab, pytest. IDE: Visual Studio Code.

## Future enhancements
SQLite/MySQL · Tkinter/CustomTkinter GUI · Django web version · Mobile app · OTP ·
Email/SMS alerts · QR payments · ATM card generation · Internet banking · AI fraud
detection · Biometric login · Multi-branch support · Cloud database
