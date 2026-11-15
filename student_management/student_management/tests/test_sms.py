from datetime import date, timedelta

import pytest

from sms import utils
from sms.admin import AdminPanel
from sms.attendance import AttendanceManager
from sms.auth import AuthManager, UserManager, can, require
from sms.backup import BackupManager
from sms.database import JSONDatabase
from sms.marks import MarksManager, parse_mark
from sms.reports import ReportGenerator
from sms.results import ResultProcessor
from sms.students import ClassManager, StudentManager
from sms.utils import (AuthenticationError, DatabaseError, NotFoundError, PermissionDenied, SMSError, ValidationError,
                       grade_for)


def recent_working_days(n):
    d, out = date.today() - timedelta(days=1), []
    while len(out) < n:
        if utils.is_working_day(d):
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return sorted(out)


@pytest.fixture
def db(tmp_path):
    return JSONDatabase(tmp_path / "data")


@pytest.fixture
def school(db):
    AuthManager(db)
    ClassManager(db).add("BCA-2024", "BCA Batch", "BCA", "2026-27", 5)
    sm = StudentManager(db)
    rolls = []
    for i, (name, g) in enumerate([("Anu Mathew", "Female"), ("Binu Raj", "Male"), ("Cyril Das", "Male")]):
        s, temp = sm.add(name, g, "2006-05-10", f"98470000{i}1", "BCA-2024", admission_date="2024-08-01")
        rolls.append(s["roll_no"])
    return db, rolls


def enter(db, roll, exam, p, j, d):
    MarksManager(db).enter(roll, exam, {"Python": p, "Java": j, "DBMS": d})


# ------------------------------------------------------------------ utils
def test_grade_boundaries():
    assert grade_for(90)[0] == "O" and grade_for(89.99)[0] == "A+"
    assert grade_for(40)[0] == "C" and grade_for(39.5)[0] == "F"


def test_parse_mark():
    assert parse_mark("78.5") == 78.5 and parse_mark("ab") == "AB" and parse_mark("80") == 80
    for bad in ("101", "-1", "78.3", "x"):
        with pytest.raises(ValidationError):
            parse_mark(bad)


def test_password_hashing_is_salted():
    h1, s1 = utils.hash_password("secret1")
    h2, s2 = utils.hash_password("secret1")
    assert h1 != h2 and utils.verify_password("secret1", h1, s1) and not utils.verify_password("wrong1", h1, s1)


# ---------------------------------------------------------------- database
def test_database_crud_and_corruption(db):
    db.insert("classes", {"code": "X"})
    assert db.find_one("classes", code="X")
    db.update("classes", "code", "X", {"name": "Y"})
    assert db.find_one("classes", code="X")["name"] == "Y"
    assert db.delete("classes", "code", "X") and not db.all("classes")
    (db.data_dir / "classes.json").write_text("{broken")
    with pytest.raises(DatabaseError):
        db.all("classes")


# ---------------------------------------------------------------- students
def test_roll_numbers_and_student_login(school):
    db, rolls = school
    assert rolls == ["BCA24001", "BCA24002", "BCA24003"]
    u = db.find_one("users", username="bca24001")
    assert u["role"] == "student" and u["roll_no"] == "BCA24001" and u["must_change_password"]


def test_student_validation(school):
    db, _ = school
    sm = StudentManager(db)
    with pytest.raises(ValidationError):
        sm.add("Dup Phone", "Male", "2006-01-01", "9847000001", "BCA-2024")      # phone already used
    with pytest.raises(ValidationError):
        sm.add("Too Young", "Male", date.today().isoformat(), "9847111111", "BCA-2024")
    with pytest.raises(NotFoundError):
        sm.add("No Class", "Male", "2006-01-01", "9847222222", "MCA-2030")


def test_search_status_and_delete_rules(school):
    db, rolls = school
    sm = StudentManager(db)
    assert [s["roll_no"] for s in sm.search("binu")] == ["BCA24002"]
    sm.set_status("BCA24003", "LEFT")
    assert len(sm.list("BCA-2024")) == 2
    assert not db.find_one("users", username="bca24003")["active"]
    enter(db, "BCA24002", "Internal Test 1", 50, 50, 50)
    with pytest.raises(SMSError):
        sm.delete("BCA24002")                                   # has marks
    sm.delete("BCA24002", purge=True)
    assert not db.find("marks", roll_no="BCA24002") and not db.find_one("users", username="bca24002")
    with pytest.raises(SMSError):
        ClassManager(db).delete("BCA-2024")                     # still has students


# ------------------------------------------------------------------ marks
def test_results_total_grade_rank_and_topper(school):
    db, (a, b, c) = school
    exam = "Internal Test 1"
    enter(db, a, exam, 90, 85, 90)     # 265
    enter(db, b, exam, 95, 80, 90)     # 265  (tie)
    enter(db, c, exam, 60, "AB", 50)   # absent -> fail
    rp = ResultProcessor(db)
    r = rp.student_result(a, exam)
    assert r["total"] == 265 and r["average"] == pytest.approx(88.33) and r["grade"] == "A+" and r["passed"]
    assert r["division"].startswith("First Class with Distinction")
    rc = rp.student_result(c, exam)
    assert rc["result"] == "FAIL" and rc["failed_subjects"] == ["Java"] and rc["grade"] == "F"
    res = rp.class_result("BCA-2024", exam)
    assert [x["rank"] for x in res["rows"]] == [1, 1, None]
    assert {t["roll_no"] for t in res["toppers"]} == {a, b}
    assert res["pass_percent"] == pytest.approx(66.7, abs=.05)
    assert res["subject_stats"]["Python"]["toppers"] == ["Binu Raj"]


def test_publish_locks_marks(school):
    db, rolls = school
    mm = MarksManager(db)
    with pytest.raises(SMSError):
        mm.publish("BCA-2024", "Internal Test 1")                # marks incomplete
    for r in rolls:
        enter(db, r, "Internal Test 1", 70, 70, 70)
    mm.publish("BCA-2024", "Internal Test 1")
    with pytest.raises(SMSError):
        enter(db, rolls[0], "Internal Test 1", 80, 80, 80)
    mm.unpublish("BCA-2024", "Internal Test 1")
    enter(db, rolls[0], "Internal Test 1", 80, 80, 80)
    assert mm.get(rolls[0], "Internal Test 1")["subjects"]["Java"] == 80


def test_bulk_subject_entry_and_missing(school):
    db, rolls = school
    mm = MarksManager(db)
    assert mm.enter_subject_for_class("BCA-2024", "Internal Test 2", "Python", {r: 60 for r in rolls}) == 3
    miss = mm.missing("BCA-2024", "Internal Test 2")
    assert len(miss) == 3 and miss[0]["subjects"] == ["Java", "DBMS"]


# ------------------------------------------------------------- attendance
def test_attendance_percentages_and_shortage(school):
    db, (a, b, c) = school
    am = AttendanceManager(db)
    days = recent_working_days(4)
    for i, d in enumerate(days):
        am.mark_class("BCA-2024", d, absent=[b] if i < 2 else [], leave=[c] if i == 0 else [])
    sa, sb = am.student_summary(a), am.student_summary(b)
    assert sa["percent"] == 100 and sb["percent"] == 50 and sb["shortage"]
    am.correct(b, days[0], "P")
    assert am.student_summary(b)["percent"] == 75 and not am.student_summary(b)["shortage"]
    assert am.class_summary("BCA-2024")["days_marked"] == 4


def test_attendance_rejects_holidays_and_future(school):
    db, _ = school
    am = AttendanceManager(db)
    sunday = date.today() - timedelta(days=(date.today().weekday() + 1) % 7 or 7)
    with pytest.raises(ValidationError):
        am.mark_class("BCA-2024", sunday)
    with pytest.raises(ValidationError):
        am.mark_class("BCA-2024", date.today() + timedelta(days=1))
    with pytest.raises(ValidationError):
        am.mark_class("BCA-2024", recent_working_days(1)[0], absent=["XYZ99001"])


def test_semester_exam_eligibility_needs_attendance(school):
    db, (a, b, c) = school
    am = AttendanceManager(db)
    for d in recent_working_days(4):
        am.mark_class("BCA-2024", d, absent=[b])
    enter(db, b, "Semester Exam", 70, 70, 70)
    enter(db, b, "Internal Test 1", 70, 70, 70)
    rp = ResultProcessor(db)
    assert not rp.student_result(b, "Semester Exam")["eligible"]
    assert rp.student_result(b, "Internal Test 1")["eligible"]


# ------------------------------------------------------------------- auth
def test_login_lockout_and_temp_password(db):
    am = AuthManager(db)
    assert am.login("admin", "admin123")["role"] == "admin"
    um = UserManager(db, "admin")
    u, temp = um.add("anitha", "Anitha K", "teacher")
    assert am.login("anitha", temp)["must_change_password"]
    am.change_password("anitha", temp, "newpass1", "newpass1")
    assert not am.login("anitha", "newpass1")["must_change_password"]
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            am.login("anitha", "wrong1")
    with pytest.raises(AuthenticationError):
        am.login("anitha", "newpass1")                          # locked
    new = am.reset_password("anitha", "admin")
    assert am.login("anitha", new)


def test_permissions():
    admin, teacher, student = {"role": "admin"}, {"role": "teacher"}, {"role": "student"}
    assert can(admin, "backup") and can(teacher, "marks") and not can(teacher, "admin")
    assert can(student, "self") and not can(student, "marks")
    with pytest.raises(PermissionDenied):
        require(teacher, "users")


def test_cannot_remove_last_admin(db):
    AuthManager(db)
    with pytest.raises(SMSError):
        UserManager(db, "admin").set_role("admin", "teacher")


# ------------------------------------------------- reports, admin, backup
def test_reports_and_dashboard(school, tmp_path):
    db, rolls = school
    for d in recent_working_days(3):
        AttendanceManager(db).mark_class("BCA-2024", d)
    for r, m in zip(rolls, (90, 70, 45)):
        enter(db, r, "Internal Test 1", m, m, m)
    rg = ReportGenerator(db, tmp_path / "reports")
    pdfs = [rg.report_card_pdf(rolls[0], "Internal Test 1"), rg.mark_list_pdf("BCA-2024", "Internal Test 1"),
            rg.rank_list_pdf("BCA-2024", "Internal Test 1"), rg.attendance_pdf("BCA-2024")]
    assert all(p.read_bytes()[:4] == b"%PDF" for p in pdfs)
    csv = rg.rank_list_csv("BCA-2024", "Internal Test 1").read_text()
    assert "BCA24001" in csv.splitlines()[1]
    assert rg.students_csv().read_text().count("\n") == 4
    d = AdminPanel(db).dashboard()
    assert d["students"] == 3 and d["per_class"][0]["attendance_avg"] == 100


def test_backup_and_restore(school, tmp_path):
    db, rolls = school
    bm = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bm.create_backup()
    StudentManager(db).delete(rolls[2])
    assert len(db.all("students")) == 2
    safety = bm.restore(archive)
    assert safety.exists() and len(JSONDatabase(db.data_dir).all("students")) == 3
    assert len(bm.list_backups()) == 2
