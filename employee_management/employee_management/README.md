# Employee Management System

**Advanced Employee Record Management Using Python and JSON File Handling**

A menu-driven HR application with two portals:

- **Admin (HR) panel:** employees, departments and designations, attendance, leave
  approvals, payroll with payslips, reports, backups and user accounts.
- **Employee self-service portal:** check in and out, view attendance, apply for and
  cancel leave, see leave balances, download payslips.

All data is stored permanently in JSON files and loaded automatically at startup.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: 15 employees, ~6 weeks of attendance, leaves, last month's payroll
python main.py
```

| Login | Credentials |
|---|---|
| Admin | `admin` / `admin123` (created on first run) |
| Demo employees | `EMP1001` … `EMP1015` / `welcome1` |

New employees get a **temporary password** when they are added, and must change it at
first login. Run the tests with `python -m pytest -q` (29 tests).

---

## Project structure

```
employee_management/
├── main.py                 Entry point
├── seed_demo.py            Demo data loader
├── ems/
│   ├── employees.py        Employee Management + Department & Designation Management
│   ├── auth.py             Authentication (admin & employee logins, hashing, lockout)
│   ├── attendance.py       Attendance Management
│   ├── leaves.py           Leave Management
│   ├── payroll.py          Payroll + Salary Calculator
│   ├── reports.py          Reports (CSV / PDF, payslips)
│   ├── backup.py           Backup & Restore
│   ├── database.py         Database (JSON)
│   ├── utils.py            Utilities: settings, exceptions, validation, dates, amount in words
│   └── cli.py              Menu-driven interface (admin panel + employee portal)
├── tests/test_ems.py       Unit tests (pytest)
├── data/                   users, employees, departments, attendance, leaves, payroll (.json)
├── backups/                Backup zip files
└── reports/                Generated CSV / PDF files (payslips in reports/payslips/)
```

---

## Modules

| Module | What it does |
|---|---|
| **Employee Management** | Add, view, search, update and delete employees. IDs are generated automatically (EMP1001, EMP1002, …). Name, gender, DOB (age 18–60 at joining), phone, email, PAN, bank account and IFSC are validated, and phone, email and PAN must be unique. Salary revisions keep a history. *Exit* (resignation or termination) keeps records and disables the login; *rehire* reverses it; permanent delete takes a backup first |
| **Departments & Designations** | Five departments ready to use; add, rename (employees are updated) or delete departments; add or remove designations. A designation must belong to the employee's department, and departments or designations in use can't be deleted |
| **Authentication** | Separate admin and employee logins; PBKDF2-HMAC-SHA256 password hashing with a random salt; temporary passwords and a forced change at first login; account locks after 5 failed attempts until the admin resets it |
| **Attendance** | Admin marks the whole team in one step (everyone Present except the exceptions you list) or corrects one employee. Employees check in and out: after 09:30 counts as **late**, and under 4 hours is a **half day**. Sundays and company holidays are skipped. There is a daily register and monthly summaries |
| **Leave Management** | Casual 12, Sick 10 and Earned 15 days a year (prorated for employees who join mid-year), plus unlimited Loss of Pay. Requests check working days only, overlaps, balance, and days already worked. Admin approves or rejects; approval marks the attendance automatically. Employees can cancel leave that hasn't started yet |
| **Payroll** | **Salary calculator:** Basic, HRA 40 %, DA 10 %, conveyance ₹1,600 and medical ₹1,250; PF 12 % of basic (capped at ₹15,000), ESI 0.75 % if gross ≤ ₹21,000, Kerala professional tax slabs; annual CTC. **Monthly payroll:** loss of pay = absences + ½ half days + unpaid leave + days before joining or after exit, deducted proportionally. Payroll can be regenerated until it is marked paid. Also: **highest salary report**, department salary summary, and PDF payslips with the net pay in words (Indian lakh/crore format) |
| **Reports** | CSV: employees, highest salaries, monthly attendance, leaves, payroll register. PDF: employee directory with a department salary summary, payroll register, individual payslips. Plus an on-screen company summary |
| **Backup & Restore** | Timestamped zip backups. Restore checks the file first and automatically backs up the current data so a restore can be undone |
| **Database (JSON)** | Six JSON files with atomic writes (temporary file, then `os.replace`), so a crash can't corrupt data; a damaged file gives a clear error |

### Exception handling
All errors derive from `EMSError` (`ValidationError`, `NotFoundError`,
`AuthenticationError`, `PermissionDenied`, `DatabaseError`, `BackupError`) and are shown
as friendly messages instead of crashing.

### Configuration
Company name, departments, office start time, holidays, leave quotas and all salary
percentages and limits are set at the top of `ems/utils.py`. Environment variables
`EMS_DATA_DIR`, `EMS_BACKUP_DIR` and `EMS_REPORT_DIR` override the storage folders.

> The payroll rules are simplified for an academic project: income tax (TDS), the
> employer's ESI share and gratuity are not calculated.

---

## Technologies
Python 3.10+, JSON, OOP (dataclasses), `datetime`, `calendar`, `hashlib`/`hmac`, `csv`,
`shutil`/`zipfile`, ReportLab, pytest. IDE: Visual Studio Code.

## Future enhancements
SQLite/MySQL · Tkinter GUI · Django web version · Biometric login · Email notifications
(payslips, leave approvals) · Cloud database · TDS calculation
