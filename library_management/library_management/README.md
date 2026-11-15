# Library Management System

**Advanced Library Book Management Using Python and JSON File Handling**

A menu-driven library application for *Ociuz Central Library*. It manages the book
catalogue and physical copies, members, issue / return / renewal, reservation queues
with holds, fines, and the librarian's circulation desk. It produces **PDF issue slips
and member cards with QR codes**, CSV/PDF reports and backups.

There are two portals:

- **Staff portal:** admin, librarian and assistant.
- **Member portal:** search the catalogue, see due dates, renew, reserve, and view fines.

All data is stored permanently in JSON files.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: 31 titles, 20 members, 60 days of circulation (~3 s)
python main.py
```

| Login | Credentials | Portal |
|---|---|---|
| Admin | `admin` / `admin123` | Staff: everything, including statistics, staff accounts, activity log, backup |
| Librarian | `librarian` / `lib12345` | Staff: books, members, circulation, reservations, fines (incl. waivers), reports |
| Assistant | `assistant` / `asst1234` | Staff: issue/return, reservations, fine collection, look-ups |
| Members | `M0001` … `M0020` / `member123` | Member portal |

The demo logins exist only after running `seed_demo.py`; `admin` is always created on
first run. New members receive a temporary portal password that must be changed at first
login. Run the tests with `python -m pytest -q` (15 tests; the PNG-QR test runs when the
`qrcode` package is installed).

---

## Project structure

```
library_management/
├── main.py                 Entry point
├── seed_demo.py            Demo data loader
├── library/
│   ├── books.py            Book Management (titles, copies/accession numbers, search, availability)
│   ├── members.py          Member Management (registration, renewal, suspension, eligibility, QR card)
│   ├── circulation.py      Issue & Return (issue, return, renew, lost, overdue, QR issue slip)
│   ├── reservations.py     Reservation Management (queues, holds, expiry)
│   ├── fines.py            Fine Management (overdue/lost/damage, payments, waivers)
│   ├── librarian.py        Librarian (circulation desk dashboard, reminder notices)
│   ├── auth.py             Authentication & staff accounts (hashing, roles, lockout, activity log)
│   ├── admin.py            Admin Panel (statistics, activity log)
│   ├── reports.py          Reports (CSV & PDF)
│   ├── backup.py           Backup & Restore
│   ├── database.py         JSON Database
│   ├── qr.py               QR codes (ReportLab for PDFs; qrcode package for PNG)
│   ├── utils.py            Library rules, ISBN validation, helpers
│   └── cli.py              Staff portal and member portal
├── tests/test_library.py   Unit tests (pytest)
├── data/                   users, books, copies, members, loans, reservations, fines, activity (.json)
├── backups/                Backup zip files
└── reports/                Reports; slips/ (issue slips), cards/ (member cards)
```

---

## Borrowing rules (set in `library/utils.py`)

| Member type | Books | Loan period | Fine / overdue day | Membership fee |
|---|---|---|---|---|
| Student | 3 | 14 days | ₹2 | ₹200 / year |
| Faculty | 6 | 30 days | ₹1 | free |
| Staff | 4 | 21 days | ₹1 | free |
| Public | 2 | 14 days | ₹5 | ₹500 / year |

- **Renewals:** up to 2. Not allowed when the book is overdue or another member has reserved it; each renewal runs from the day it is made.
- **Due dates:** never later than the member's membership expiry.
- **Overdue fines:** capped at the book's price.
- **Lost books:** charged at book price + ₹100 processing, plus any overdue fine so far.
- **Blocks:** borrowing stops when there are overdue books, unpaid fines above ₹100, or the membership is expired or suspended.
- **Reservations:** up to 3 per member. A returned copy is held for the first member in the queue for 3 days; if it isn't collected, it passes to the next member.
- **Reference books:** can't be borrowed or reserved.

---

## Modules

| Module | What it does |
|---|---|
| **Book Management** | Titles with ISBN (**ISBN-10/13 check-digit validation**, ISBN-10 stored as ISBN-13), authors, publisher, year, category, language, shelf, price, keywords, reference-only flag. Each **copy has an accession number** (ACC00001…) and status: Available, Issued, On hold, Damaged, Lost or Withdrawn. Search by title, author, ISBN, keyword or category; per-title availability; add or withdraw copies; damaged/repaired; titles can be deleted only if they have no history |
| **Member Management** | Student, Faculty, Staff and Public members with roll or employee ID. Duplicate checks (phone, email, ID). A one-year membership with renewal, suspension or reactivation, and closure (only when all books are returned and dues cleared). **Borrowing eligibility** lists every blocking reason. A **member card PDF with QR code** |
| **Issue & Return** | Issue by accession number, book ID or ISBN; respects holds, the queue and all limits. Return calculates the **overdue fine** and supports damage fees; the copy goes to the next reservation automatically. **Renew**, **report lost**, overdue tracking, and an **A6 PDF issue slip with QR code** (loan, copy, member, due date) |
| **Reservation Management** | A first-come queue per title: a member can reserve only when no copy is on the shelf. Holds are placed automatically on return or when new copies are added; uncollected holds expire (run automatically at staff login) and pass on. Members see their queue position and can cancel |
| **Fine Management** | Overdue, lost and damage fines; part payments with receipt numbers (Cash/UPI/Card); "collect all dues"; **waivers** (librarian or admin, with a reason); outstanding balances; collection summaries |
| **Librarian** | Circulation desk dashboard: issued/returned today, due today and in the next 3 days, overdue list, holds ready, waiting reservations, fines collected, memberships expiring. **Reminder notices** (due soon, overdue, ready for pickup) with a CSV export for SMS/email |
| **Authentication** | PBKDF2-HMAC-SHA256 password hashing; lockout after 5 failed attempts; temporary passwords that must be changed at first login; role-based menus (admin, librarian, assistant, member) |
| **Admin Panel** | Library statistics (titles, copies by status, members by status and type, loans, fines, membership fees, collection value), staff accounts (add, change role, activate, reset or unlock), activity log, record counts, backup and restore |
| **Reports** | Available books, issued books (with days late), overdue books, most borrowed books, a circulation summary (issues, returns, renewals, on-time rate, by category and member type, fines) and member activity. **PDF:** available & issued books, overdue books, circulation report. **CSV:** catalogue, issued, overdue, members, fines, daily circulation, reminders |
| **Backup & Restore** | Timestamped zip backups. Restore checks the file first and automatically backs up the current data so a restore can be undone |
| **JSON Database** | Eight JSON files with atomic writes (temporary file, then `os.replace`) and a clear error if a file is damaged |

### QR codes
- **PDFs:** issue slips and member cards draw their QR codes with ReportLab's built-in generator, so no extra package is needed.
- **PNG images:** saving a member's QR code as a PNG uses the `qrcode` package from `requirements.txt`. Without it, the app shows how to install it.
- **Scanning:** at the issue desk, the member search accepts a scanned card code (`LIB-MEMBER:M0001`).

### Exception handling
All errors derive from `LibraryError` (`ValidationError`, `NotFoundError`,
`AuthenticationError`, `PermissionDenied`, `CirculationError`, `DatabaseError`,
`BackupError`) and are shown as friendly messages instead of crashing.

### Configuration
Library name and address, borrowing rules, fine rates, hold period, reservation limit,
categories, languages and role permissions are set in `library/utils.py`. Environment
variables `LIB_DATA_DIR`, `LIB_BACKUP_DIR` and `LIB_REPORT_DIR` override the storage
folders. The ISBNs in the demo data are synthetic (valid check digits, not the real
books' ISBNs).

---

## Technologies
Python 3.10+, JSON, OOP, `datetime`, `hashlib`/`hmac`, `csv`, `shutil`/`zipfile`,
ReportLab (PDFs and QR codes), qrcode (PNG QR codes), pytest. IDE: Visual Studio Code.

## Future enhancements
SQLite/MySQL · Tkinter GUI · Django web portal (online catalogue/OPAC) · Barcode/QR
scanner integration · Email/SMS notifications · Cloud database · E-book lending
