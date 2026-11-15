# Advanced Student Management System (Python + JSON)

A menu-driven Python 3 console application for managing a college's students, marks, grades, attendance and results. All data is stored in JSON files. It has two login portals: a **staff portal** for the admin and teachers, and a **student portal** where students log in with their roll number.

## Quick start

```bash
pip install -r requirements.txt     # reportlab (PDF reports) + pytest
python seed_demo.py                 # optional: load demo data (use --force to replace existing data)
python main.py
```

| Login | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` (created automatically on first run) |
| Teacher (demo) | `anitha`, `rajesh` | `teach123` |
| Student (demo) | roll number, e.g. `BCA24001`, `BSC25002` | `stud123` |

New staff and students get a **temporary password** and must change it at their first login.

Run the tests with `python -m pytest`.

## Modules

| Synopsis module | Where | What it does |
|---|---|---|
| Student Management | `sms/students.py` | Classes (code, course, academic year, semester, class teacher). Student add/view/update/delete/search, with auto roll numbers (`BCA-2024` → `BCA24001`…). Validates phone, email and age, rejects duplicate phone/email, and handles status changes (ACTIVE / LEFT / GRADUATED). |
| Marks & Grade Management | `sms/marks.py` | Python, Java and DBMS marks out of 100 for Internal Test 1, Internal Test 2 and the Semester Exam. Half marks and `AB` (absent) are allowed. Marks can be entered per student or one subject for a whole class. Shows missing marks. Publishing results locks the marks. |
| Attendance Management | `sms/attendance.py` | Take class attendance by entering only the absentees (everyone else is marked present) and the students on leave. Corrections, day view, class summary, monthly register and a list of unmarked days. Sundays, holidays and future dates are rejected. |
| Result Processing | `sms/results.py` | Total, average, percentage, grade, GPA, pass/fail and division. Rank list with ties sharing a rank (1, 1, 3), class topper and subject toppers. Subject analysis and grade distribution. Progress across exams. Semester exam eligibility requires 75% attendance. |
| Authentication | `sms/auth.py` | Salted PBKDF2-SHA256 password hashing (hashlib). Account locks after 5 wrong attempts. Temporary passwords, roles and permissions. |
| Admin Panel | `sms/admin.py`, `sms/cli.py` | Dashboard (today's attendance, shortages, pass %, toppers, pending marks), staff user management, activity log, record counts. |
| Reports | `sms/reports.py` | PDF (ReportLab): report card, mark list with subject analysis, rank list, attendance report. CSV: mark list, rank list, monthly attendance register, student list. |
| Backup & Restore | `sms/backup.py` | Zip backups with integrity checks. A safety backup is taken automatically before every restore and before a permanent delete. |
| JSON Database | `sms/database.py` | One JSON file per collection. Atomic writes (temp file + replace), thread lock, clear error on a corrupted file. |

## Grading scheme (edit in `sms/utils.py`)

| % | Grade | Points |
|---|---|---|
| ≥ 90 | O (Outstanding) | 10 |
| ≥ 80 | A+ | 9 |
| ≥ 70 | A | 8 |
| ≥ 60 | B+ | 7 |
| ≥ 50 | B | 6 |
| ≥ 40 | C | 5 |
| < 40 or absent | F | 0 |

- **Pass rule:** at least 40 in **every** subject. A student who is absent or fails in any subject fails overall, gets grade F and is not ranked.
- **Divisions:** First Class with Distinction (≥ 75%), First Class (≥ 60%), Second Class (≥ 50%), Pass Class.
- **Attendance:** minimum 75%. Below that, the student is flagged as *not eligible* for the Semester Exam result.

You can change the institution name, subjects, exams, pass mark, holidays and grade bands in `sms/utils.py`.

## Roles

| Role | Can do |
|---|---|
| admin | Everything, including classes, staff users, publishing results, backup and restore |
| teacher | Students, attendance, marks, results, reports |
| student | Own profile, published results and report card PDF, attendance (and how many days are needed to reach 75%), progress, change password |

## Project structure

```
student_management/
├── main.py              entry point
├── seed_demo.py         demo data: 2 classes, 2 teachers, 30 students, ~2 months attendance, 2 exams
├── sms/
│   ├── utils.py         settings, grading, validation, hashing, exceptions
│   ├── database.py      JSON database
│   ├── auth.py          login, users, permissions, activity log
│   ├── students.py      classes and students
│   ├── marks.py         marks entry and publishing
│   ├── attendance.py    attendance
│   ├── results.py       result processing, ranks, toppers
│   ├── reports.py       PDF and CSV reports
│   ├── admin.py         dashboard and activity
│   ├── backup.py        backup and restore
│   └── cli.py           menus (staff and student portals)
├── tests/test_sms.py    pytest suite
├── data/  backups/  reports/
```

The folders can be redirected with the `SMS_DATA_DIR`, `SMS_BACKUP_DIR` and `SMS_REPORT_DIR` environment variables.

## Future enhancements

SQLite/MySQL storage (only `database.py` needs to change), a Tkinter GUI or Django web portal (the managers in `sms/` have no `input()`/`print()` calls, so they can be reused as-is), a parent portal, SMS/email alerts for absence and results, and a cloud database.
