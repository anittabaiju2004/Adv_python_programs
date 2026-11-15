# Quiz Application

**Advanced Online Quiz System Using Python and JSON File Handling**

A menu-driven online quiz system for *Ociuz Academy*. It has two portals:

- **Instructor/admin portal:** manage categories, a question bank (MCQ and True/False, three difficulty levels) and quizzes; view results, analysis, reports and users; backup.
- **Student portal:** take **timed exams** or **practice** with instant feedback, bookmark questions, review answers, see performance analysis and leaderboards, and download **PDF results and certificates**.

All data is stored permanently in JSON files.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: 62 questions, 6 quizzes, 10 students, ~50 attempts over 30 days
python main.py
```

| Login | Credentials |
|---|---|
| Admin | `admin` / `admin123` (created on first run) |
| Instructor | `instructor` / `teach123` |
| Students | `anitta`, `rahul`, `priya`, `arjun`, `fathima`, `akhil`, `sneha`, `nikhil`, `divya`, `vishnu` / `student123` |

The instructor and student logins exist only after running `seed_demo.py`. New students
can also register themselves from the main menu. Run the tests with
`python -m pytest -q` (14 tests).

---

## Project structure

```
quiz_application/
├── main.py                Entry point
├── seed_demo.py           Demo question bank, quizzes, students and attempts
├── quiz/
│   ├── engine.py          Quiz Engine (quiz definitions, random selection, timer, practice/exam, scoring)
│   ├── questions.py       Question Management (MCQ / True-False, CSV import/export, bookmarks, item analysis)
│   ├── categories.py      Category Management
│   ├── users.py           User Management (student registration, profiles)
│   ├── results.py         Result Management (attempt history, best attempt, certificate verification)
│   ├── leaderboard.py     Leaderboard (per quiz and overall; all time / week / month)
│   ├── analysis.py        Performance Analysis (strengths, weak areas, trends, matplotlib charts)
│   ├── auth.py            Authentication & staff accounts (hashing, roles, lockout, activity log)
│   ├── admin.py           Admin Panel (dashboard, activity log)
│   ├── reports.py         Reports (PDF result, PDF certificate, PDF performance & quiz reports, CSV)
│   ├── backup.py          Backup & Restore
│   ├── database.py        JSON Database
│   ├── utils.py           Quiz rules, grading scale, validation, helpers
│   └── cli.py             Student portal and staff portal
├── tests/test_quiz.py     Unit tests (pytest)
├── data/                  users, categories, questions, quizzes, results, bookmarks, activity (.json)
├── backups/               Backup zip files
└── reports/               results/, certificates/, charts/, reports and CSV files
```

---

## Modules and advanced features

| Module / feature | What it does |
|---|---|
| **Quiz Engine** | A quiz has a category (or Mixed), difficulty (or Mixed), number of questions, time limit, negative marking, pass mark and maximum exam attempts. It can be published only when enough matching active questions exist. Each attempt draws a fresh set (below), and **answer options are shuffled** |
| **Random question selection** | Random, but **prefers questions the student has seen least**. A **Mixed** quiz is balanced across difficulties: 40 % easy, 40 % medium, 20 % hard, filling any shortfall from the other levels |
| **Difficulty levels** | Easy, Medium and Hard, worth 1, 2 and 3 marks by default (each question can override) |
| **Timed quiz** | A countdown is shown with every question. When time runs out the attempt is **submitted automatically** and later answers aren't accepted. The timer uses an injectable clock, so it is unit-tested |
| **Practice & Exam modes** | **Practice:** untimed, unlimited, with the **correct answer and explanation shown immediately**; no negative marking, leaderboard entry or certificate. Quick practice by category or difficulty is also available. **Exam:** timed, negative marking, attempt limits, leaderboard entry, and a certificate on passing |
| **Bookmark questions** | Press `*` during any quiz. Students can review bookmarks with their answers and explanations, or run a **practice round of bookmarked questions** |
| **Question Management** | MCQ (2–6 options) or True/False. Validation rejects duplicate options, invalid answer keys and duplicate questions. Questions have explanations and can be enabled or disabled; a question used in results can't be deleted. **CSV import/export**, and **question analysis** listing the % correct and % skipped per question to flag questions that may be too hard or have a wrong answer key |
| **Result Management** | Each attempt stores a **snapshot of every question**, so editing a question later never changes old results. Stored per attempt: score, %, grade, correct/wrong/skipped, negative marks, time taken, and whether time ran out. Answer review, best attempt and attempt counts are available |
| **Grading** | A+ ≥ 90 · A ≥ 80 · B ≥ 70 · C ≥ 60 · D ≥ 50 · F, with remarks; pass mark set per quiz |
| **Leaderboard** | Per quiz: each student's best exam attempt, ranked by score, then faster time, then earlier submission, with standard competition ranking (1, 2, 2, 4). Overall: average best % across quizzes. Filters for all time, last week and last month; shows the student's own rank |
| **Performance analysis** | Attempts, average, best, accuracy, exam pass rate, accuracy **by category and difficulty**, **weak areas** (< 60 %) and strengths (≥ 80 %), improvement trend (last 3 vs first 3 attempts) and time per question. **Matplotlib charts:** score trend and category accuracy |
| **PDF result & certificate** | Result scorecard with a colour-coded answer review and explanations. A landscape **certificate** with an HMAC **verification code**; anyone can check a certificate from the main menu, and a tampered code is rejected |
| **Admin dashboard** | Students, questions by difficulty, quizzes, attempts (today, exam, practice), average score, pass rate, certificates, top students, recent attempts. Also the activity log, record counts, backup and restore |
| **Authentication** | PBKDF2-HMAC-SHA256 password hashing; lockout after 5 failed attempts; temporary passwords for staff that must be changed at first login; role-based menus (admin, instructor, student) |
| **Reports** | PDF quiz report (stats, grade-distribution chart, top 10, hardest questions) and PDF student performance report. CSV: results, leaderboards, question analysis, users |
| **Backup & Restore** | Timestamped zip backups. Restore checks the file first and automatically backs up the current data so a restore can be undone |
| **JSON Database** | Seven JSON files with atomic writes (temporary file, then `os.replace`) and a clear error if a file is damaged |

### Exception handling
All errors derive from `QuizError` (`ValidationError`, `NotFoundError`,
`AuthenticationError`, `PermissionDenied`, `QuizRuleError`, `DatabaseError`,
`BackupError`) and are shown as friendly messages instead of crashing.

### Configuration
Grade scale, default marks per difficulty, roles and permissions are set in
`quiz/utils.py`. Set the environment variable `QUIZ_CERT_SECRET` to your own secret
before real use, because it signs the certificate verification codes. Environment
variables `QUIZ_DATA_DIR`, `QUIZ_BACKUP_DIR` and `QUIZ_REPORT_DIR` override the storage
folders.

### A note on the timer
A console program can't interrupt someone in the middle of typing. The remaining time is
shown with every question and checked on every answer; once it reaches zero, nothing more
is accepted and the attempt is submitted with the answers given before the deadline.

---

## Technologies
Python 3.10+, JSON, OOP, `datetime`, `hashlib`/`hmac`, `random`, `csv`, ReportLab, matplotlib,
`shutil`/`zipfile`, pytest. IDE: Visual Studio Code.

## Future enhancements
SQLite/MySQL · Tkinter GUI · Django web portal · AI-based adaptive quiz (difficulty that
follows the student's accuracy) · Cloud database · Email result notifications
