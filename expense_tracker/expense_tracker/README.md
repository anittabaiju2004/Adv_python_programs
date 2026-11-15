# Advanced Personal Expense Tracker System

**Advanced Personal Expense Management Using Python and JSON File Handling**

A menu-driven Python application to record, organise and analyse personal finances:
expenses, income, budgets with alerts, savings goals, bill reminders, user/admin login
with hashed passwords, CSV/PDF reports, Matplotlib charts, and backup & restore. All
data is stored permanently in JSON files.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: loads a year of sample data
python main.py
```

| Account | Username | Password |
|---|---|---|
| Admin (created on first run) | `admin` | `admin123` |
| Demo user (after `seed_demo.py`) | `demo` | `demo123` |

Change the admin password after first login (Main Menu → Change Password).

Run the tests:

```bash
python -m pytest -q
```

---

## Project structure

```
expense_tracker/
├── main.py                 Entry point
├── seed_demo.py            Sample data generator
├── requirements.txt
├── tracker/
│   ├── config.py           Paths, categories, thresholds
│   ├── exceptions.py       Custom exception hierarchy
│   ├── validators.py       Input validation helpers
│   ├── models.py           OOP data models (User, Expense, Income, Budget, SavingsGoal, Bill)
│   ├── database.py         JSON database (atomic writes, thread lock)
│   ├── auth.py             Authentication + PBKDF2 password hashing
│   ├── transactions.py     Expense Management & Income Management
│   ├── budget.py           Budget Management & alerts
│   ├── savings.py          Savings Management
│   ├── bills.py            Bill Reminder (recurring bills)
│   ├── reports.py          Analytics, CSV, PDF (reportlab), charts (matplotlib)
│   ├── backup.py           Backup & Restore (zip snapshots)
│   ├── admin.py            Admin panel logic
│   └── cli.py              Menu-driven user interface
├── tests/test_tracker.py   18 unit tests (pytest)
├── data/                   JSON data files (created automatically)
├── backups/                Backup archives
└── reports/                Generated CSV / PDF / PNG files (one folder per user)
```

---

## Modules and features

| Module | What it does |
|---|---|
| **Expense Management** | Add, view, update, delete expenses; search by keyword, category and amount range; filter by date range; payment mode (Cash/UPI/Card/Net Banking) |
| **Income Management** | Same operations for income, grouped by source (Salary, Freelance, …) |
| **Budget Management** | Monthly limit overall or per category; warning at 80 %, alert when exceeded; alerts shown at login and after each new expense |
| **Savings Management** | Goals with target and optional deadline; deposits and withdrawals; progress bar; required monthly saving to meet the deadline |
| **Bill Reminder** | Bills with due dates; overdue and upcoming (next 7 days) reminders at login; marking paid can log an expense and schedules the next monthly/yearly bill |
| **Authentication** | Registration with username and password rules; PBKDF2-HMAC-SHA256 hashing with a random salt per user; change password |
| **Admin** | List users, system statistics, create users, activate or deactivate, change role, reset password, delete a user and all of their data |
| **Reports** | Monthly summary, yearly analytics, category-wise report, CSV export, PDF report with tables and charts, pie, monthly trend and budget charts |
| **Backup & Restore** | Timestamped zip snapshots; restore checks the archive first and automatically backs up current data so a restore can be undone |
| **Database (JSON)** | One JSON file per collection; atomic writes so a crash can't corrupt data; clear error if a file is damaged |

### Exception handling
All errors derive from `TrackerError` (`ValidationError`, `NotFoundError`,
`AuthenticationError`, `DatabaseError`, `BackupError`). The CLI catches these and shows
a friendly message instead of crashing; Ctrl+C cancels the current action.

### Data files
```
data/users.json     data/expenses.json   data/incomes.json
data/budgets.json   data/savings.json    data/bills.json
```
Each record carries the owning `username`, so users only ever see their own data.

### Configuration
Edit `tracker/config.py` to change the currency symbol, categories, budget warning
threshold or bill reminder window. Environment variables `ET_DATA_DIR`,
`ET_BACKUP_DIR` and `ET_REPORT_DIR` override the storage folders.

---

## Technologies
Python 3.10+, JSON, OOP (dataclasses, inheritance), `datetime`, `hashlib`, `hmac`,
`csv`, `shutil`, `zipfile`, **reportlab**, **matplotlib**, **pytest**.

## Future enhancements
SQLite/MySQL integration · Mobile app · Cloud synchronisation · AI expense prediction ·
UPI/Bank API integration · Email & SMS notifications
