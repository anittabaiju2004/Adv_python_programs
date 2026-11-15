"""Unit tests — run with:  python -m pytest -q"""
import json
from datetime import date, datetime, timedelta

import pytest

from ems.attendance import AttendanceManager
from ems.auth import AuthManager
from ems.backup import BackupManager
from ems.database import JSONDatabase
from ems.employees import DepartmentManager, EmployeeManager
from ems.leaves import LeaveManager
from ems.payroll import PayrollManager, calculate_salary, professional_tax
from ems.reports import ReportGenerator
from ems.utils import (AuthenticationError, BackupError, DatabaseError, EMSError, NotFoundError,
                       PermissionDenied, ValidationError, is_working_day, rupees_in_words,
                       working_days_in_month)

TODAY = date.today()
LAST_MONTH = (TODAY.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
LM_DAYS = [d.isoformat() for d in working_days_in_month(LAST_MONTH)]
JOINED = (TODAY.replace(day=1) - timedelta(days=400)).isoformat()


def next_working_days(n, start_offset=7):
    out, d = [], TODAY + timedelta(days=start_offset)
    while len(out) < n:
        if is_working_day(d):
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


@pytest.fixture
def db(tmp_path):
    return JSONDatabase(tmp_path / "data")


@pytest.fixture
def em(db):
    return EmployeeManager(db)


def new_emp(em, name="Anitta Joseph", phone="9847012345", email="anitta@x.com", basic=30000, **kw):
    data = dict(name=name, gender="Female", dob="1996-04-12", phone=phone, email=email,
                department="Engineering", designation="Software Engineer", join_date=JOINED, basic_salary=basic)
    data.update(kw)
    return em.add(**data)


@pytest.fixture
def anitta(em):
    return new_emp(em)[0]


@pytest.fixture
def rahul(em):
    return new_emp(em, "Rahul Menon", "9895098765", "rahul@x.com", 12000, gender="Male",
                   department="Finance", designation="Accountant")[0]


# ================================================================= utilities
def test_rupees_in_words():
    assert rupees_in_words(45842) == "Forty Five Thousand Eight Hundred Forty Two Rupees Only"
    assert rupees_in_words(123456.75).startswith("One Lakh Twenty Three Thousand")
    assert rupees_in_words(10000000) == "One Crore Rupees Only"


# ===================================================================== auth
def test_admin_and_employee_login(db, em, anitta):
    auth = AuthManager(db)
    assert auth.login("admin", "admin123")["role"] == "admin"
    emp = em.get(anitta.emp_id)
    temp = auth.reset_password(emp.emp_id)
    u = auth.login(emp.emp_id.lower(), temp)
    assert u["role"] == "employee" and u["must_change_password"]
    auth.change_password(emp.emp_id, temp, "mypass12", "mypass12")
    assert not auth.login(emp.emp_id, "mypass12")["must_change_password"]


def test_lockout_and_reset(db, em, anitta):
    auth = AuthManager(db)
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            auth.login(anitta.emp_id, "wrong")
    with pytest.raises(AuthenticationError, match="locked"):
        auth.login(anitta.emp_id, "anything")
    temp = auth.reset_password(anitta.emp_id)
    auth.login(anitta.emp_id, temp)


# ================================================================ employees
def test_add_employee(em):
    emp, temp = new_emp(em, name="anitta JOSEPH", phone="+91 98470-12345", pan="abcde1234f",
                        designation="software engineer", bank_account="1234 5678 9012", ifsc="sbin0001234")
    assert emp.emp_id == "EMP1001" and emp.name == "Anitta Joseph" and emp.phone == "9847012345"
    assert emp.designation == "Software Engineer" and emp.pan == "ABCDE1234F" and emp.bank_account == "123456789012"
    assert len(temp) >= 9 and emp.salary_history[0]["reason"] == "Joining"
    assert new_emp(em, phone="9000000001", email="b@x.com")[0].emp_id == "EMP1002"


@pytest.mark.parametrize("bad", [
    {"phone": "12345"}, {"email": "nope"}, {"dob": "2015-01-01"}, {"dob": "1950-01-01"},
    {"basic": 100}, {"designation": "Accountant"}, {"department": "Space"}, {"gender": "X"},
    {"join_date": (TODAY + timedelta(days=200)).isoformat()}, {"pan": "12345"}, {"ifsc": "SBIN1234"},
])
def test_add_validation(em, bad):
    with pytest.raises((ValidationError, NotFoundError)):
        new_emp(em, **bad)


def test_unique_fields(em, anitta):
    with pytest.raises(ValidationError, match="Email"):
        new_emp(em, phone="9000000001")
    with pytest.raises(ValidationError, match="Phone"):
        new_emp(em, email="other@x.com")


def test_search_update_and_salary_revision(em, anitta, rahul):
    assert [e.emp_id for e in em.search("finance")] == [rahul.emp_id]
    assert [e.emp_id for e in em.search("anitta")] == [anitta.emp_id]
    assert [e.emp_id for e in em.list(sort_by="salary")] == [anitta.emp_id, rahul.emp_id]
    e = em.update(anitta.emp_id, designation="Tech Lead", address="Kochi")
    assert e.designation == "Tech Lead" and e.department == "Engineering"
    with pytest.raises(ValidationError):
        em.update(anitta.emp_id, designation="Accountant")          # not in Engineering
    e = em.update(anitta.emp_id, department="Finance", designation="Finance Manager")
    assert e.department == "Finance"
    with pytest.raises(ValidationError, match="salary revision"):
        em.update(anitta.emp_id, basic_salary=1)
    e = em.revise_salary(anitta.emp_id, 36000, "Promotion")
    assert e.basic_salary == 36000 and e.salary_history[-1]["old"] == 30000


def test_exit_rehire_and_delete(db, em, anitta):
    auth = AuthManager(db)
    e = em.exit_employee(anitta.emp_id, TODAY.isoformat(), "Higher studies")
    assert e.status == "EXITED" and em.list() == [] and len(em.list("EXITED")) == 1
    temp = auth.reset_password(anitta.emp_id)
    with pytest.raises(AuthenticationError, match="disabled"):
        auth.login(anitta.emp_id, temp)
    em.rehire(anitta.emp_id)
    auth.login(anitta.emp_id, temp)
    AttendanceManager(db).mark(anitta.emp_id, LM_DAYS[0], "PRESENT")
    assert em.delete(anitta.emp_id)["attendance"] == 1
    assert auth.get(anitta.emp_id) is None
    with pytest.raises(NotFoundError):
        em.get(anitta.emp_id)


def test_departments(db, em, anitta):
    dm = DepartmentManager(db)
    dm.add("Research & Development")
    dm.add_designation("research & development", "Research Scientist")
    with pytest.raises(ValidationError):
        dm.add("research & development")
    assert dm.headcount()["Engineering"] == 1
    with pytest.raises(EMSError):
        dm.delete("Engineering")
    with pytest.raises(EMSError):
        dm.remove_designation("Engineering", "Software Engineer")
    assert dm.rename("Engineering", "Technology") == 1
    assert em.get(anitta.emp_id).department == "Technology"
    dm.delete("Research & Development")


# =============================================================== attendance
def test_mark_and_summary(db, anitta, rahul):
    am = AttendanceManager(db)
    res = am.mark_all(LM_DAYS[0])
    assert res["marked"] == 2
    am.mark(anitta.emp_id, LM_DAYS[1], "ABSENT")
    am.mark(anitta.emp_id, LM_DAYS[2], "HALF_DAY")
    am.mark(anitta.emp_id, LM_DAYS[2], "half_day")                   # re-marking updates, not duplicates
    s = am.monthly_summary(anitta.emp_id, LAST_MONTH)
    assert (s["present"], s["absent"], s["half_day"], s["lop_days"]) == (1, 1, 1, 1.5)
    assert s["unmarked"] == len(LM_DAYS) - 3
    assert am.monthly_summary(anitta.emp_id, LAST_MONTH, unmarked_as_absent=True)["lop_days"] == 1.5 + len(LM_DAYS) - 3
    with pytest.raises(ValidationError):
        am.mark(anitta.emp_id, (TODAY + timedelta(days=3)).isoformat(), "PRESENT")
    sunday = next(d for d in (date.fromisoformat(LM_DAYS[0]) + timedelta(days=i) for i in range(7)) if d.weekday() == 6)
    with pytest.raises(ValidationError, match="not a working day"):
        am.mark(anitta.emp_id, sunday.isoformat(), "PRESENT")
    with pytest.raises(ValidationError):
        am.mark(anitta.emp_id, LM_DAYS[3], "LEAVE")                  # leave only via approval


def test_check_in_out(db, anitta):
    am = AttendanceManager(db)
    d = date.fromisoformat(LM_DAYS[4])
    r = am.check_in(anitta.emp_id, datetime.combine(d, datetime.min.time()).replace(hour=9, minute=45))
    assert r["late"] and r["status"] == "PRESENT"
    with pytest.raises(EMSError, match="Already checked in"):
        am.check_in(anitta.emp_id, datetime.combine(d, datetime.min.time()).replace(hour=10))
    r = am.check_out(anitta.emp_id, datetime.combine(d, datetime.min.time()).replace(hour=12, minute=45))
    assert r["status"] == "HALF_DAY" and r["hours"] == 3.0
    d2 = date.fromisoformat(LM_DAYS[5])
    am.check_in(anitta.emp_id, datetime.combine(d2, datetime.min.time()).replace(hour=9, minute=10))
    r = am.check_out(anitta.emp_id, datetime.combine(d2, datetime.min.time()).replace(hour=18))
    assert r["status"] == "PRESENT" and not r["late"]
    assert am.mark_all(LM_DAYS[5])["skipped"] == 1                   # self check-in not overwritten


# ==================================================================== leave
def test_leave_workflow(db, anitta):
    lm = LeaveManager(db)
    days = next_working_days(3)
    l = lm.apply(anitta.emp_id, "casual", days[0], days[-1], "Family function")
    assert l["status"] == "PENDING" and l["days"] == len([d for d in days])
    assert lm.balance(anitta.emp_id, int(days[0][:4]))["Casual"]["pending"] == 3
    with pytest.raises(ValidationError, match="Overlaps"):
        lm.apply(anitta.emp_id, "Sick", days[1], days[1], "x")
    lm.approve(l["leave_id"])
    recs = [r for r in db.all("attendance") if r["leave_id"] == l["leave_id"]]
    assert len(recs) == 3 and all(r["status"] == "LEAVE" for r in recs)
    lm.cancel(l["leave_id"], by_emp=anitta.emp_id)                    # not started yet -> allowed
    assert not [r for r in db.all("attendance") if r["leave_id"] == l["leave_id"]]
    l2 = lm.apply(anitta.emp_id, "Sick", days[0], days[0], "Fever")
    lm.reject(l2["leave_id"], remarks="Submit certificate")
    assert lm.get(l2["leave_id"])["status"] == "REJECTED"


def test_leave_rules(db, em, anitta):
    lm = LeaveManager(db)
    days = next_working_days(14)
    with pytest.raises(ValidationError, match="Insufficient Casual"):
        lm.apply(anitta.emp_id, "Casual", days[0], days[-1], "Long trip")     # 14 > 12
    lm.apply(anitta.emp_id, "Loss of Pay", days[0], days[-1], "Long trip")   # unlimited
    with pytest.raises(ValidationError, match="no working days"):
        sun = next(d for d in (TODAY + timedelta(days=i) for i in range(30, 40)) if d.weekday() == 6)
        lm.apply(anitta.emp_id, "Casual", sun.isoformat(), sun.isoformat(), "x")
    other = new_emp(em, "Bob Roy", "9000000002", "bob@x.com", join_date=f"{TODAY.year}-07-01")[0]
    assert LeaveManager(db).entitlement(other.emp_id, TODAY.year)["Casual"] == 6.0    # 6 of 12 months
    with pytest.raises(PermissionDenied):
        lm.cancel(lm.list(anitta.emp_id)[0]["leave_id"], by_emp=other.emp_id)


# ================================================================== payroll
def test_salary_calculator():
    c = calculate_salary(30000)
    assert (c["gross"], c["pf"], c["esi"], c["professional_tax"], c["net"]) == (47850, 1800, 0, 208, 45842)
    low = calculate_salary(12000)
    assert low["gross"] == 20850 and low["esi"] == 156.38               # ESI applies at or below 21,000
    lop = calculate_salary(30000, working_days=25, lop_days=5)
    assert lop["gross"] == 38280 and lop["lop_deduction"] == 9570 and lop["pf"] == 1800
    assert professional_tax(11000) == 0 and professional_tax(15000) == 120
    with pytest.raises(ValidationError):
        calculate_salary(30000, 25, 30)


def test_payroll_generation(db, em, anitta, rahul):
    am, pm = AttendanceManager(db), PayrollManager(db)
    am.mark(anitta.emp_id, LM_DAYS[0], "ABSENT")
    am.mark(anitta.emp_id, LM_DAYS[1], "HALF_DAY")
    am.apply_leave(anitta.emp_id, [LM_DAYS[2]], "LVTEST", "Loss of Pay")
    am.apply_leave(anitta.emp_id, [LM_DAYS[3]], "LVTEST2", "Casual")      # paid leave: no LOP
    r = pm.generate(LAST_MONTH)
    assert r["generated"] == 2
    p = pm.get(anitta.emp_id, LAST_MONTH)
    assert p["lop_days"] == 2.5 and p["working_days"] == len(LM_DAYS)
    assert p["net"] == calculate_salary(30000, len(LM_DAYS), 2.5)["net"]
    assert pm.get(rahul.emp_id, LAST_MONTH)["lop_days"] == 0
    assert pm.mark_paid(LAST_MONTH, [anitta.emp_id]) == 1
    am.mark(rahul.emp_id, LM_DAYS[0], "ABSENT")
    r = pm.generate(LAST_MONTH)                                         # regenerate: paid slip untouched
    assert r == {"generated": 1, "skipped_paid": 1, "total_net": pm.get(rahul.emp_id, LAST_MONTH)["net"],
                 "month": LAST_MONTH}
    assert pm.get(rahul.emp_id, LAST_MONTH)["lop_days"] == 1
    with pytest.raises(ValidationError):
        pm.generate((TODAY + timedelta(days=40)).strftime("%Y-%m"))
    top = pm.highest_salaries(5)
    assert [t["employee"].emp_id for t in top] == [anitta.emp_id, rahul.emp_id]


def test_mid_month_joiner_prorated(db, em):
    emp = new_emp(em, join_date=LM_DAYS[10])[0]
    PayrollManager(db).generate(LAST_MONTH)
    p = PayrollManager(db).get(emp.emp_id, LAST_MONTH)
    assert p["not_employed_days"] == 10 and p["lop_days"] == 10


# ================================================================== reports
def test_reports(db, em, anitta, rahul, tmp_path):
    AttendanceManager(db).mark_all(LM_DAYS[0])
    PayrollManager(db).generate(LAST_MONTH)
    rg = ReportGenerator(db, tmp_path / "reports")
    for path in (rg.employees_csv(), rg.highest_salary_csv(), rg.attendance_csv(LAST_MONTH), rg.leaves_csv(),
                 rg.payroll_csv(LAST_MONTH)):
        assert path.exists() and path.read_text(encoding="utf-8-sig").count("\n") >= 1
    for path in (rg.employees_pdf(), rg.payroll_register_pdf(LAST_MONTH), rg.payslip_pdf(anitta.emp_id, LAST_MONTH)):
        assert path.read_bytes()[:4] == b"%PDF"
    with pytest.raises(NotFoundError):
        rg.payslip_pdf(anitta.emp_id, "2020-01")


# =========================================================== backup & db
def test_backup_restore(db, em, anitta, tmp_path):
    bm = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bm.create_backup()
    new_emp(em, "Bob Roy", "9000000002", "bob@x.com")
    safety = bm.restore(archive)
    assert len(em.list()) == 1 and safety.exists()
    bad = tmp_path / "backups" / "ems_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bm.restore(bad)


def test_persistence_and_corruption(db, em, anitta):
    assert EmployeeManager(JSONDatabase(db.data_dir)).get(anitta.emp_id).name == "Anitta Joseph"
    assert json.loads((db.data_dir / "employees.json").read_text())[0]["emp_id"] == anitta.emp_id
    (db.data_dir / "employees.json").write_text("{bad")
    with pytest.raises(DatabaseError):
        em.list()
