"""Menu-driven interface: staff portal (admin / teacher) and student portal."""
from __future__ import annotations

import getpass
import sys
from datetime import date, timedelta

from . import utils
from .admin import AdminPanel
from .attendance import AttendanceManager
from .auth import AuthManager, UserManager, can
from .backup import BackupManager
from .database import JSONDatabase
from .marks import MarksManager, parse_mark
from .reports import ReportGenerator
from .results import ResultProcessor
from .students import ClassManager, StudentManager
from .utils import (ABSENT, EXAMS, GENDERS, INSTITUTION, MIN_ATTENDANCE, PASS_MARK, ROLES, STUDENT_STATUSES, SUBJECTS,
                    SMSError)

W = 84


# ======================================================================= ui
def line(ch: str = "-") -> None:
    print(ch * W)


def header(title: str) -> None:
    print()
    line("=")
    print(f"{title:^{W}}")
    line("=")


def ask(prompt: str, default: str | None = None) -> str:
    v = input(f"  {prompt}{f' [{default}]' if default else ''}: ").strip()
    return v if v else (default or "")


def confirm(prompt: str) -> bool:
    return ask(f"{prompt} (y/n)").lower() in ("y", "yes")


def pause() -> None:
    input("\n  Press Enter to continue...")


def menu(title: str, options: list[str], back: str = "Back") -> str:
    header(title)
    for i, o in enumerate(options, 1):
        print(f"  {i:>2}. {o}")
    print(f"   0. {back}")
    return ask("Choose an option")


def choose(prompt: str, options: list, allow_blank: bool = False) -> str:
    options = [str(o) for o in options]
    for i, o in enumerate(options, 1):
        print(f"     {i}. {o}")
    while True:
        v = ask(prompt)
        if allow_blank and not v:
            return ""
        if v.isdigit() and 1 <= int(v) <= len(options):
            return options[int(v) - 1]
        for o in options:
            if o.lower() == v.lower():
                return o
        print("  Invalid choice.")


def last_working_day() -> str:
    d = date.today()
    while not utils.is_working_day(d):
        d -= timedelta(days=1)
    return d.isoformat()


def print_students(ss: list[dict]) -> None:
    if not ss:
        print("  No students.")
        return
    print(f"  {'Roll No':<11}{'Name':<24}{'Gender':<8}{'Class':<11}{'Phone':<12}Status")
    line()
    for s in ss:
        print(f"  {s['roll_no']:<11}{s['name'][:23]:<24}{s['gender']:<8}{s['class_code']:<11}{s['phone']:<12}{s['status']}")
    line()
    print(f"  {len(ss)} student(s)")


def print_result(r: dict, rank=None) -> None:
    header(f"{r['name']} ({r['roll_no']}) — {r['exam']}")
    print(f"  {'Subject':<12}{'Marks':>8}{'Grade':>8}  Result")
    line()
    for x in r["subjects"]:
        print(f"  {x['subject']:<12}{str(x['marks']):>8}{x['grade']:>8}  {x['result']}")
    line()
    print(f"  {'Total':<12}{r['total']:>8g} / {r['max_total']}")
    print(f"  Average {r['average']:g} · Percentage {r['percent']:.2f}% · Grade {r['grade']} ({r['remark']}) · GPA {r['gpa']:.2f}")
    print(f"  Result: {r['result']} — {r['division']}" + (f" · Rank {rank}" if rank else ""))
    if r["failed_subjects"]:
        print(f"  ⚠ Failed / absent: {', '.join(r['failed_subjects'])}")
    print(f"  Attendance {r['attendance']:.1f}%" + ("  ⚠ below " + f"{MIN_ATTENDANCE:g}%" if r["attendance_shortage"] else ""))
    if not r["eligible"]:
        print("  ⚠ Not eligible for the semester exam result until the attendance shortage is condoned.")


def print_class_result(res: dict) -> None:
    header(f"{res['class_code']} — {res['exam']} — {'PUBLISHED' if res['published'] else 'provisional'}")
    print(f"  {'Rank':<6}{'Roll No':<11}{'Name':<22}" + "".join(f"{s:>8}" for s in SUBJECTS) + f"{'Total':>8}{'%':>8}{'Grade':>7}  Result")
    line()
    for r in res["rows"]:
        marks = "".join(f"{str(next(x['marks'] for x in r['subjects'] if x['subject'] == s)):>8}" for s in SUBJECTS)
        print(f"  {str(r['rank'] or '-'):<6}{r['roll_no']:<11}{r['name'][:21]:<22}{marks}{r['total']:>8g}"
              f"{r['percent']:>8.1f}{r['grade']:>7}  {r['result']}")
    line()
    print(f"  Appeared {res['appeared']} · passed {res['passed']} · failed {res['failed']} · pass % {res['pass_percent']} · "
          f"class average {res['class_average']}% · distinctions {res['distinctions']}")
    tops = ", ".join(f"{t['name']} ({t['percent']:.1f}%)" for t in res["toppers"]) or "-"
    print(f"  🏆 Class topper: {tops}")
    for s, v in res["subject_stats"].items():
        print(f"     {s:<8} avg {v['average']:>5} · high {v['highest']} · pass {v['pass_percent']}% · topper {', '.join(v['toppers']) or '-'}")
    if res["incomplete"]:
        print(f"  (Incomplete marks, not included: {', '.join(res['incomplete'])})")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)                 # loaded automatically at start-up
        self.auth = AuthManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.report_dir = report_dir or utils.REPORT_DIR
        self.user: dict | None = None

    @property
    def actor(self) -> str:
        return self.user["username"] if self.user else "system"

    def classes(self):
        return ClassManager(self.db, self.actor)

    def students(self):
        return StudentManager(self.db, self.actor)

    def marks(self):
        return MarksManager(self.db, self.actor)

    def att(self):
        return AttendanceManager(self.db, self.actor)

    def results(self):
        return ResultProcessor(self.db)

    def reports(self):
        return ReportGenerator(self.db, self.report_dir)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(f"STUDENT MANAGEMENT SYSTEM — {INSTITUTION}", ["Login (staff or student)"], "Exit")
            try:
                if choice == "1":
                    self.login()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except SMSError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def login(self) -> None:
        header("LOGIN")
        print("  Staff: your username.  Students: your roll number (e.g. BCA24001).")
        self.user = self.auth.login(ask("Username / roll number"), getpass.getpass("  Password: "))
        if self.user["must_change_password"]:
            print("\n  You are using a temporary password. Please set a new one.")
            while True:
                try:
                    self.change_password()
                    break
                except SMSError as exc:
                    print(f"  ✖ {exc}")
        print(f"\n  Welcome, {self.user['name']}!")
        if self.user["role"] == "student":
            self.student_portal()
        else:
            self.dashboard()
            self.loop(f"STAFF PORTAL — {self.user['name']} ({self.user['role']})", [
                ("Dashboard", self.dashboard, None, False), ("Classes", self.class_menu, "classes", True),
                ("Students", self.student_menu, "students", True), ("Attendance", self.attendance_menu, "attendance", True),
                ("Marks & grades", self.marks_menu, "marks", True), ("Results, rank list & toppers", self.result_menu, "results", True),
                ("Reports (PDF / CSV)", self.report_menu, "reports", True), ("Users", self.user_menu, "users", True),
                ("Admin panel (activity log, backup)", self.admin_menu, "admin", True),
                ("Change password", self.change_password, None, False)])

    def loop(self, title: str, items: list[tuple]) -> None:
        items = [i for i in items if i[2] is None or can(self.user, i[2])]
        while self.user:
            choice = menu(title, [i[0] for i in items], "Logout")
            if choice == "0":
                print("  Logged out.")
                self.user = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(items)):
                continue
            _, handler, _, sub = items[int(choice) - 1]
            try:
                handler()
            except SMSError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            if not sub:
                pause()

    def submenu(self, title: str, options: list[tuple]) -> None:
        options = [o for o in options if len(o) < 3 or can(self.user, o[2])]
        while self.user:
            choice = menu(title, [o[0] for o in options])
            if choice == "0":
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(options)):
                continue
            try:
                options[int(choice) - 1][1]()
            except SMSError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def change_password(self) -> None:
        self.auth.change_password(self.actor, getpass.getpass("  Current password: "),
                                  getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
        print("  ✔ Password changed.")

    # ------------------------------------------------------------ pickers
    def pick_class(self) -> str:
        codes = self.classes().codes()
        if not codes:
            raise SMSError("No classes yet. Add a class first.")
        return codes[0] if len(codes) == 1 else choose("Class", codes)

    def pick_exam(self) -> str:
        return choose("Exam", EXAMS)

    def pick_student(self) -> dict:
        q = ask("Roll number or name")
        try:
            return self.students().get(q)
        except SMSError:
            pass
        matches = self.students().search(q)
        if not matches:
            raise SMSError(f"No student matches '{q}'.")
        if len(matches) == 1:
            return matches[0]
        for i, s in enumerate(matches[:15], 1):
            print(f"   {i:>2}. {s['roll_no']}  {s['name']:<24}{s['class_code']}")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= min(len(matches), 15)):
            raise SMSError("Invalid selection.")
        return matches[int(n) - 1]

    # ----------------------------------------------------------- dashboard
    def dashboard(self) -> None:
        d = AdminPanel(self.db).dashboard()
        header("DASHBOARD")
        print(f"  Classes {d['classes']} · active students {d['students']} "
              f"({', '.join(f'{k} {v}' for k, v in d['by_gender'].items() if v)}) · staff {d['staff']}")
        for c in d["per_class"]:
            cl = c["class"]
            today = f"{c['today']['present']}/{c['today']['total']} present today" if c["today"] else "attendance not taken today"
            print(f"\n  {cl['code']} — {cl['name']} (Sem {cl['semester']}, {cl['academic_year']}) · {c['students']} students")
            print(f"    {today} · average attendance {c['attendance_avg']}% · below {d['min_attendance']:g}%: {c['shortage']}"
                  + (f" · {c['unmarked_last_7']} day(s) unmarked this week" if c["unmarked_last_7"] else ""))
            if c["latest_exam"]:
                print(f"    {c['latest_exam']}: pass {c['pass_percent']}% · topper {', '.join(c['toppers']) or '-'}")
            pending = {e: n for e, n in c["marks_pending"].items() if n}
            if pending:
                print("    Marks pending: " + ", ".join(f"{e} ({n})" for e, n in pending.items()))

    # -------------------------------------------------------------- classes
    def class_menu(self) -> None:
        cm = self.classes()

        def listing():
            for c in cm.list():
                n = len(self.students().list(c["code"]))
                print(f"  {c['code']:<11}{c['name'][:28]:<29}{c['course'][:26]:<27}Sem {c['semester']}  {c['academic_year']}  "
                      f"{n} students  teacher {c['class_teacher'] or '-'}  published: {', '.join(c.get('published_exams', [])) or '-'}")

        def add():
            c = cm.add(ask("Class code (e.g. BCA-2024)"), ask("Class name"), ask("Course"), ask("Academic year (e.g. 2025-26)"),
                       ask("Semester", "1"), ask("Class teacher username (optional)"))
            print(f"  ✔ Class {c['code']} added.")

        def edit():
            c = cm.get(self.pick_class())
            cm.update(c["code"], name=ask("Name", c["name"]), semester=ask("Semester", str(c["semester"])),
                      academic_year=ask("Academic year", c["academic_year"]),
                      class_teacher=ask("Class teacher", c["class_teacher"] or None))
            print("  ✔ Updated.")
        self.submenu("CLASSES", [("List classes", listing), ("Add class", add), ("Edit class", edit),
                                 ("Delete class (no students only)", lambda: (cm.delete(self.pick_class()), print("  ✔ Deleted.")))])

    # ------------------------------------------------------------- students
    def student_menu(self) -> None:
        self.submenu("STUDENTS", [
            ("Add student", self.add_student),
            ("List students", lambda: print_students(self.students().list(
                self.pick_class(), status=choose("Status", ["ACTIVE", "LEFT", "GRADUATED", "ALL"]).replace("ALL", "") or None,
                sort_by=choose("Sort by", ["roll", "name"])))),
            ("Search students", lambda: print_students(self.students().search(ask("Name, roll no, phone, email or guardian")))),
            ("Student profile", self.student_profile), ("Update student", self.update_student),
            ("Change status (left / graduated / active)", lambda: (lambda s: (self.students().set_status(
                s["roll_no"], choose("New status", STUDENT_STATUSES)), print("  ✔ Status changed.")))(self.pick_student())),
            ("Delete student", self.delete_student),
            ("Reset student portal password", lambda: print(
                f"  ✔ Temporary password: {self.auth.reset_password(self.pick_student()['roll_no'], self.actor)}"))])

    def add_student(self) -> None:
        header("ADD STUDENT")
        cls = self.pick_class()
        s, temp = self.students().add(ask("Full name"), choose("Gender", GENDERS), ask("Date of birth (YYYY-MM-DD)"),
                                      ask("Mobile number"), cls, ask("Email (optional)"), ask("Guardian name"),
                                      ask("Guardian mobile (optional)"), ask("Address"),
                                      ask("Admission date", date.today().isoformat()))
        print(f"  ✔ Added {s['name']} as {s['roll_no']}.")
        print(f"    Student portal login: {s['roll_no']}   Temporary password: {temp}")

    def student_profile(self) -> None:
        s = self.pick_student()
        header(f"{s['roll_no']} — {s['name']}")
        for label, key in [("Class", "class_code"), ("Gender", "gender"), ("Date of birth", "dob"), ("Phone", "phone"),
                           ("Email", "email"), ("Guardian", "guardian_name"), ("Guardian phone", "guardian_phone"),
                           ("Address", "address"), ("Admitted", "admission_date"), ("Status", "status")]:
            print(f"  {label:<15}: {s.get(key) or '-'}")
        a = self.att().student_summary(s["roll_no"])
        print(f"\n  Attendance: {a['present']}/{a['days']} days = {a['percent']}%" + ("  ⚠ SHORTAGE" if a["shortage"] else "")
              if a["days"] else "\n  Attendance: no days recorded yet.")
        prog = self.results().progress(s["roll_no"])
        if prog:
            print("\n  Results:")
            for r in prog:
                print(f"    {r['exam']:<17}{r['total']:>6g}/{r['max_total']}  {r['percent']:>6.2f}%  {r['grade']:<3}{r['result']:<5}"
                      f"rank {r['rank'] or '-'}")

    def update_student(self) -> None:
        s = self.pick_student()
        print("  Leave blank to keep the current value.")
        changes = {k: ask(label, s.get(k) or None) for k, label in
                   [("name", "Name"), ("phone", "Phone"), ("email", "Email"), ("guardian_name", "Guardian"),
                    ("guardian_phone", "Guardian phone"), ("address", "Address")]}
        changes = {k: v for k, v in changes.items() if v != (s.get(k) or "")}
        if not changes:
            print("  No changes.")
            return
        self.students().update(s["roll_no"], **changes)
        print(f"  ✔ Updated: {', '.join(changes)}.")

    def delete_student(self) -> None:
        s = self.pick_student()
        try:
            if confirm(f"Delete {s['roll_no']} {s['name']}?"):
                self.students().delete(s["roll_no"])
                print("  ✔ Deleted.")
        except SMSError as exc:
            print(f"  {exc}")
            if can(self.user, "admin") and confirm("Delete permanently together with all marks and attendance?"):
                self.backup.create_backup("pre_delete")
                c = self.students().delete(s["roll_no"], purge=True)
                print(f"  ✔ Deleted with {c['marks']} mark record(s); attendance entries removed. Backup taken first.")

    # ----------------------------------------------------------- attendance
    def attendance_menu(self) -> None:
        def mark():
            cls = self.pick_class()
            day = ask("Date (YYYY-MM-DD)", last_working_day())
            existing = self.att().get_day(cls, day)
            if existing and not confirm("Attendance for this day exists. Replace it?"):
                return
            print("  Everyone is marked PRESENT except the roll numbers you enter.")
            absent = [x for x in ask("Absent roll numbers (comma separated, blank = none)").replace(" ", "").split(",") if x]
            leave = [x for x in ask("On approved leave (comma separated, blank = none)").replace(" ", "").split(",") if x]
            rec = self.att().mark_class(cls, day, absent, leave)
            v = list(rec["records"].values())
            print(f"  ✔ {rec['date']}: present {v.count('P')}, absent {v.count('A')}, leave {v.count('L')}.")

        def view_day():
            rec = self.att().get_day(self.pick_class(), ask("Date", last_working_day()))
            if not rec:
                print("  Attendance not taken for that day.")
                return
            names = {s["roll_no"]: s["name"] for s in self.students().list(status=None)}
            for r, st in rec["records"].items():
                print(f"  {r:<11}{names.get(r, '')[:26]:<27}{ {'P': 'Present', 'A': 'ABSENT', 'L': 'Leave'}[st]}")

        def summary():
            cs = self.att().class_summary(self.pick_class(), ask("From (blank = all)") or None, ask("To (blank = today)") or None)
            header(f"ATTENDANCE — {cs['class_code']} ({cs['days_marked']} days marked, average {cs['average']}%)")
            for r in cs["students"]:
                bar = "█" * int(r["percent"] / 5)
                print(f"  {r['roll_no']:<11}{r['name'][:22]:<23}{r['present']:>4}/{r['days']:<4}{r['percent']:>6.1f}%  {bar:<20}"
                      + ("  SHORTAGE" if r["shortage"] else ""))

        def register():
            reg = self.att().monthly_register(self.pick_class(), ask("Month (YYYY-MM)", date.today().strftime("%Y-%m")))
            print(f"  {'Roll No':<11}" + "".join(d[8:10] for d in reg["dates"]) + "    %")
            for r in reg["rows"]:
                print(f"  {r['roll_no']:<11}" + "".join(f"{m:>2}" for m in r["marks"])
                      + f"  {r['percent'] if r['percent'] is not None else '-'}")
            print("  P present · A absent · L leave · ? not taken · - not on roll")

        def unmarked():
            cls = self.pick_class()
            days = self.att().unmarked_days(cls, ask("From", (date.today() - timedelta(days=30)).isoformat()), date.today())
            print("  " + (", ".join(days) if days else "Attendance is complete for this period."))
        self.submenu("ATTENDANCE", [
            ("Take attendance for a class", mark),
            ("Correct one student's attendance", lambda: (lambda s: (self.att().correct(
                s["roll_no"], ask("Date", last_working_day()), choose("Status", ["P", "A", "L"])),
                print("  ✔ Corrected.")))(self.pick_student())),
            ("View attendance for a day", view_day), ("Class attendance summary", summary),
            ("Shortage list (below 75%)", lambda: [print(f"  {r['roll_no']:<11}{r['name']:<24}{r['percent']:.1f}%")
                                                    for r in self.att().class_summary(self.pick_class())["shortage"]]
             or print("  No shortage.")),
            ("Monthly register", register), ("Days not yet marked", unmarked)])

    # ---------------------------------------------------------------- marks
    def marks_menu(self) -> None:
        def one():
            s = self.pick_student()
            exam = self.pick_exam()
            try:
                cur = self.marks().get(s["roll_no"], exam)["subjects"]
            except SMSError:
                cur = {}
            print(f"  Enter marks out of {utils.SUBJECT_MAX} ({ABSENT} = absent). Blank keeps the current value.")
            entered = {}
            for sub in SUBJECTS:
                while True:
                    v = ask(sub, str(cur[sub]) if sub in cur else None)
                    try:
                        if v:
                            parse_mark(v)
                            entered[sub] = v
                        break
                    except SMSError as exc:
                        print(f"    ✖ {exc}")
            rec = self.marks().enter(s["roll_no"], exam, entered)
            print(f"  ✔ Saved {s['roll_no']} {exam}: {rec['subjects']}")
            if len(rec["subjects"]) == len(SUBJECTS):
                r = self.results().student_result(s["roll_no"], exam)
                print(f"    Total {r['total']:g} · {r['percent']:.2f}% · grade {r['grade']} · {r['result']}")

        def bulk():
            cls, exam = self.pick_class(), self.pick_exam()
            sub = choose("Subject", SUBJECTS)
            print(f"  {sub} marks for {cls} — {exam}. Enter 0-{utils.SUBJECT_MAX} or {ABSENT}; blank skips a student.")
            entries = {}
            for s in self.students().list(cls):
                try:
                    cur = self.marks().get(s["roll_no"], exam)["subjects"].get(sub)
                except SMSError:
                    cur = None
                while True:
                    v = ask(f"{s['roll_no']} {s['name'][:22]:<22}", str(cur) if cur is not None else None)
                    if not v:
                        break
                    try:
                        parse_mark(v)
                        entries[s["roll_no"]] = v
                        break
                    except SMSError as exc:
                        print(f"    ✖ {exc}")
            if entries:
                n = self.marks().enter_subject_for_class(cls, exam, sub, entries)
                print(f"  ✔ Saved {sub} marks for {n} student(s).")

        def view():
            cls, exam = self.pick_class(), self.pick_exam()
            recs = {m["roll_no"]: m["subjects"] for m in self.marks().class_marks(cls, exam)}
            print(f"  {'Roll No':<11}{'Name':<24}" + "".join(f"{s:>8}" for s in SUBJECTS))
            for s in self.students().list(cls):
                m = recs.get(s["roll_no"], {})
                print(f"  {s['roll_no']:<11}{s['name'][:23]:<24}" + "".join(f"{str(m.get(x, '·')):>8}" for x in SUBJECTS))
            print(f"\n  {'Published (locked)' if self.marks().is_published(cls, exam) else 'Not published'}")

        def missing():
            cls, exam = self.pick_class(), self.pick_exam()
            miss = self.marks().missing(cls, exam)
            for m in miss:
                print(f"  {m['roll_no']:<11}{m['name']:<24}missing {', '.join(m['subjects'])}")
            print(f"  {len(miss)} student(s) with incomplete marks." if miss else "  All marks entered.")

        def publish():
            cls, exam = self.pick_class(), self.pick_exam()
            if self.marks().is_published(cls, exam):
                if confirm(f"{exam} is published. Unpublish to allow corrections?"):
                    self.marks().unpublish(cls, exam)
                    print("  ✔ Unpublished — marks can be edited again.")
            elif confirm(f"Publish {exam} results for {cls}? Marks will be locked and visible to students"):
                self.marks().publish(cls, exam)
                print("  ✔ Published.")
        self.submenu("MARKS & GRADES", [
            ("Enter / edit marks for a student", one), ("Enter one subject for the whole class", bulk),
            ("View class marks", view), ("Students with missing marks", missing),
            ("Publish / unpublish results (admin)", publish, "admin"),
            ("Delete a student's exam marks", lambda: (self.marks().delete(self.pick_student()["roll_no"], self.pick_exam()),
                                                       print("  ✔ Deleted.")))])

    # -------------------------------------------------------------- results
    def result_menu(self) -> None:
        def student():
            s = self.pick_student()
            exam = self.pick_exam()
            print_result(self.results().student_result(s["roll_no"], exam), self.results().rank_of(s["roll_no"], exam))

        def toppers():
            cls = self.pick_class()
            for exam in EXAMS:
                try:
                    res = self.results().class_result(cls, exam)
                except SMSError:
                    continue
                if res["rows"]:
                    tops = ", ".join(f"{t['name']} ({t['percent']:.1f}%)" for t in res["toppers"]) or "-"
                    print(f"  {exam:<17} 🏆 {tops}")
                    for sub, v in res["subject_stats"].items():
                        print(f"  {'':<17}    {sub:<8} {v['highest']}/100 — {', '.join(v['toppers']) or '-'}")

        def progress():
            s = self.pick_student()
            prog = self.results().progress(s["roll_no"])
            if not prog:
                print("  No complete results yet.")
            for r in prog:
                print(f"  {r['exam']:<17}{r['percent']:>6.2f}% {'█' * int(r['percent'] / 4):<25}{r['grade']:<3}rank {r['rank'] or '-'}")
        self.submenu("RESULTS, RANK LIST & TOPPERS", [
            ("Student result", student),
            ("Class result & rank list", lambda: print_class_result(self.results().class_result(self.pick_class(), self.pick_exam()))),
            ("Class & subject toppers", toppers), ("Student progress across exams", progress),
            ("Attendance shortage (exam eligibility)", lambda: [print(f"  {r['roll_no']:<11}{r['name']:<24}{r['percent']:.1f}%")
                                                                 for r in self.results().shortage_students(self.pick_class())]
             or print("  Everyone meets the attendance requirement."))])

    # -------------------------------------------------------------- reports
    def report_menu(self) -> None:
        rg = self.reports()
        saved = lambda p: print(f"  ✔ Saved: {p}")  # noqa: E731

        def class_cards():
            cls, exam = self.pick_class(), self.pick_exam()
            n = 0
            for m in self.marks().class_marks(cls, exam):
                try:
                    rg.report_card_pdf(m["roll_no"], exam)
                    n += 1
                except SMSError:
                    continue
            print(f"  ✔ {n} report card(s) saved in {rg.report_dir / 'report_cards'}")
        self.submenu("REPORTS", [
            ("Report card (PDF)", lambda: saved(rg.report_card_pdf(self.pick_student()["roll_no"], self.pick_exam()))),
            ("Report cards for a whole class (PDF)", class_cards),
            ("Mark list (PDF)", lambda: saved(rg.mark_list_pdf(self.pick_class(), self.pick_exam()))),
            ("Rank list (PDF)", lambda: saved(rg.rank_list_pdf(self.pick_class(), self.pick_exam()))),
            ("Attendance report (PDF)", lambda: saved(rg.attendance_pdf(self.pick_class(), ask("From (blank = all)") or None,
                                                                        ask("To (blank = today)") or None))),
            ("Mark list (CSV)", lambda: saved(rg.mark_list_csv(self.pick_class(), self.pick_exam()))),
            ("Rank list (CSV)", lambda: saved(rg.rank_list_csv(self.pick_class(), self.pick_exam()))),
            ("Monthly attendance register (CSV)", lambda: saved(rg.attendance_csv(self.pick_class(),
                                                                                  ask("Month (YYYY-MM)", date.today().strftime("%Y-%m"))))),
            ("Student list (CSV)", lambda: saved(rg.students_csv(ask("Class code (blank = all)") or None)))])

    # ---------------------------------------------------------------- users
    def user_menu(self) -> None:
        um = UserManager(self.db, self.actor)

        def listing():
            for u in um.list():
                state = "LOCKED" if u["failed_attempts"] >= 5 else ("active" if u["active"] else "inactive")
                print(f"  {u['username']:<14}{u['name'][:22]:<23}{u['role']:<9}{state:<9}"
                      f"last login {(u['last_login'] or '-').replace('T', ' ')[:16]}")

        def add():
            u, temp = um.add(ask("Username"), ask("Full name"), choose("Role", ROLES), ask("Phone (optional)"), ask("Email (optional)"))
            print(f"  ✔ {u['username']} created. Temporary password: {temp}")
        self.submenu("USERS (STAFF)", [
            ("List staff", listing), ("Add staff user", add),
            ("Change role", lambda: (um.set_role(ask("Username"), choose("Role", ROLES)), print("  ✔ Updated."))),
            ("Activate / deactivate", lambda: (lambda u: (um.set_active(u["username"], not u["active"]),
                                                          print("  ✔ Done.")))(um.get(ask("Username")))),
            ("Reset password / unlock", lambda: print(f"  ✔ Temporary password: {self.auth.reset_password(ask('Username'), self.actor)}"))])

    # ---------------------------------------------------------------- admin
    def admin_menu(self) -> None:
        panel = AdminPanel(self.db)

        def restore():
            backups = self.backup.list_backups()
            for i, b in enumerate(backups, 1):
                print(f"  {i:>2}. {b.name}")
            n = ask("Backup number to restore")
            if n.isdigit() and 1 <= int(n) <= len(backups) and confirm("Replace ALL current data?"):
                safety = self.backup.restore(backups[int(n) - 1])
                print(f"  ✔ Restored. Previous data saved as {safety.name}. Please log in again.")
                self.user = None
        self.submenu("ADMIN PANEL", [
            ("Activity log", lambda: [print(f"  {a['at'].replace('T', ' ')}  {a['user']:<12}{a['action']:<20}{a['details']}")
                                      for a in panel.activity(40, ask("Filter by user (blank = all)") or None)]),
            ("Record counts", lambda: [print(f"  {k:<12}{v:>7}") for k, v in panel.record_counts().items()]),
            ("Create backup", lambda: print(f"  ✔ Backup created: {self.backup.create_backup().name}")),
            ("List backups", lambda: print("\n".join(f"  {b.name}" for b in self.backup.list_backups()) or "  None.")),
            ("Restore backup", restore)])

    # ======================================================= student portal
    def student_portal(self) -> None:
        roll = self.user["roll_no"]

        def published_exams() -> list[str]:
            s = self.students().get(roll)
            return [e for e in EXAMS if self.marks().is_published(s["class_code"], e)]

        def my_results():
            exams = published_exams()
            if not exams:
                print("  No results have been published yet.")
                return
            exam = choose("Exam", exams)
            print_result(self.results().student_result(roll, exam), self.results().rank_of(roll, exam))
            if confirm("\n  Download your report card (PDF)?"):
                print(f"  ✔ Saved: {self.reports().report_card_pdf(roll, exam)}")

        def my_attendance():
            a = self.att().student_summary(roll)
            if not a["days"]:
                print("  No attendance recorded yet.")
                return
            print(f"  Present {a['present']} of {a['days']} working days — {a['percent']}% (minimum {MIN_ATTENDANCE:g}%)")
            if a["shortage"]:
                need = 0
                while (a["present"] + need) / (a["days"] + need) * 100 < MIN_ATTENDANCE:
                    need += 1
                print(f"  ⚠ Shortage — attend the next {need} working day(s) without a break to reach {MIN_ATTENDANCE:g}%.")
            if a["absent_dates"]:
                print(f"  Absent / leave on: {', '.join(a['absent_dates'][-15:])}")

        def my_progress():
            exams = set(published_exams())
            for r in self.results().progress(roll):
                if r["exam"] in exams:
                    print(f"  {r['exam']:<17}{r['percent']:>6.2f}%  {r['grade']:<3}{r['result']:<5} rank {r['rank'] or '-'}")

        def profile():
            s = self.students().get(roll)
            print(f"  {s['name']} ({s['roll_no']}) · {s['class_code']} · {s['phone']} · {s['email'] or '-'} · "
                  f"guardian {s['guardian_name'] or '-'}")
        self.loop(f"STUDENT PORTAL — {self.user['name']} ({roll})", [
            ("My results & report card", my_results, None, False), ("My attendance", my_attendance, None, False),
            ("My progress across exams", my_progress, None, False), ("My profile", profile, None, False),
            ("Change password", self.change_password, None, False)])


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except SMSError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
