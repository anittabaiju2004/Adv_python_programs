# Contact Book Management System

**Advanced Contact Book Management Using Python and JSON File Handling**

A menu-driven Python application for managing personal and professional contacts.
Each user has a private contact book with add / view / search / update / delete,
favourites, categories, phone and email validation, duplicate detection, a recycle
bin, birthday reminders, CSV import, and CSV / PDF / vCard export. An admin manages
users, and all data is stored permanently in JSON files with backup and restore.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: demo user with ~30 sample contacts
python main.py
```

| Account | Username | Password |
|---|---|---|
| Admin (created on first run) | `admin` | `admin123` |
| Demo user (after `seed_demo.py`) | `demo` | `demo123` |

Run the tests: `python -m pytest -q` (37 tests).

---

## Project structure

```
contact_book/
├── main.py                     Entry point
├── seed_demo.py                Sample data loader
├── requirements.txt
├── contactbook/
│   ├── contacts.py             Contact Management module
│   ├── auth.py                 Authentication module
│   ├── admin.py                Admin module
│   ├── database.py             Database (JSON) module
│   ├── reports.py              Reports module (CSV / PDF / vCard)
│   ├── backup.py               Backup & Restore module
│   ├── utils.py                Utilities: settings, exceptions, validation, hashing, helpers
│   ├── models.py               OOP data models (User, Contact)
│   └── cli.py                  Menu-driven user interface
├── tests/test_contact_book.py  Unit tests (pytest)
├── data/                       users.json, contacts.json (created automatically)
├── backups/                    Backup zip files
└── reports/                    Exported files, one folder per user
```

---

## Modules

| Module | What it does |
|---|---|
| **Contact Management** | Add, view (A–Z grouped or sorted by recent / company / category), search, view details, update, delete. Search matches name, phone digits, email, company, address and notes. Contacts can be picked by typing a name or number; no need to remember IDs |
| **Favourites** | Mark or unmark contacts as favourites; filter any list, search or export to favourites only |
| **Categories** | Default categories Family, Friends, Work, Business, Emergency and Other; add, rename or delete your own categories (contacts in a deleted category move to *Other*) |
| **Validation** | Phone numbers are normalised, so `98765 43210`, `098765-43210` and `+91 9876543210` all become `+919876543210`. Indian landlines with STD code and international `+<country code>` numbers are accepted. Email, name, birthday (no future dates) and field lengths are also checked |
| **Duplicate detection** | Warns when a phone (main or alternate) or email already belongs to another contact, even if typed in a different format; you can still save anyway |
| **Recycle bin** | Deleted contacts can be restored or deleted permanently; you can also empty the bin |
| **Birthdays** | Reminder of this week's birthdays at login, and a list of birthdays in the next *N* days with the age each person turns (29 February is handled) |
| **Authentication** | Registration, login, change password; PBKDF2-HMAC-SHA256 password hashing with a random salt; login attempt limit; deactivated accounts blocked |
| **Admin** | List users with contact counts, system statistics, create users, activate or deactivate, change role, reset password, delete a user and their contacts (backup taken first), users report CSV. The admin sees counts, never other users' contact details |
| **Reports** | **CSV** export (opens correctly in Excel and can be imported back), **PDF** contact directory grouped A–Z or by category, and **vCard (.vcf)** export for phones, Gmail and Outlook. Exports can be filtered by category or favourites; there is also a statistics screen |
| **Import** | Import contacts from a CSV file (same format as the export). Invalid rows and duplicates are skipped with row-by-row reasons, and new categories are created automatically |
| **Backup & Restore** | Timestamped zip snapshots of the data. Restore (admin only) checks the file first and backs up the current data automatically so a restore can be undone |
| **Database (JSON)** | `users.json` and `contacts.json`; atomic writes (temporary file, then `os.replace`) so a crash can't corrupt data; clear error if a file is damaged |

### Exception handling
All errors derive from `ContactBookError` (`ValidationError`, `NotFoundError`,
`DuplicateError`, `AuthenticationError`, `DatabaseError`, `BackupError`). The menu
shows them as friendly messages instead of crashing, and Ctrl+C cancels the current
action.

### Configuration
Default categories, the birthday window and the admin account are set in
`contactbook/utils.py`. Environment variables `CB_DATA_DIR`, `CB_BACKUP_DIR` and
`CB_REPORT_DIR` override the storage folders.

---

## Technologies
Python 3.10+, JSON, OOP (dataclasses), `datetime`, `hashlib`/`hmac`, `csv`, `re`,
`shutil`/`zipfile`, ReportLab, pytest.

## Future enhancements
GUI (Tkinter / CustomTkinter) · SQLite / MySQL · Google Contacts sync · Contact photos ·
QR-code contact cards · Email / SMS birthday greetings · Web version (Django / Flask)
