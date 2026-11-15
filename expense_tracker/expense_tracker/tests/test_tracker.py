"""Unit tests — run with:  python -m pytest -q"""
import json
from datetime import date, timedelta

import pytest

from tracker.admin import AdminManager
from tracker.auth import AuthManager, hash_password, verify_password
from tracker.backup import BackupManager
from tracker.bills import BillManager
from tracker.budget import BudgetManager
from tracker.database import JSONDatabase
from tracker.exceptions import (AuthenticationError, BackupError, DatabaseError,
                                NotFoundError, ValidationError)
from tracker.reports import ReportGenerator
from tracker.savings import SavingsManager
from tracker.transactions import ExpenseManager, IncomeManager

TODAY = date.today()
MONTH = TODAY.strftime("%Y-%m")


@pytest.fixture
def db(tmp_path):
    return JSONDatabase(tmp_path / "data")


@pytest.fixture
def auth(db):
    a = AuthManager(db)
    a.register("alice", "secret1", "Alice")
    return a


# ------------------------------------------------------------------ auth
def test_password_hashing_is_salted():
    h1, s1 = hash_password("abc123")
    h2, s2 = hash_password("abc123")
    assert h1 != h2 and s1 != s2
    assert verify_password("abc123", h1, s1)
    assert not verify_password("wrong1", h1, s1)


def test_default_admin_created(db):
    AuthManager(db)
    assert AuthManager(db).login("admin", "admin123").is_admin


def test_register_and_login(auth):
    user = auth.login("ALICE", "secret1")
    assert user.username == "alice" and user.last_login
    with pytest.raises(AuthenticationError):
        auth.login("alice", "nope123")


def test_register_validation(auth):
    with pytest.raises(ValidationError):
        auth.register("alice", "secret1")
    with pytest.raises(ValidationError):
        auth.register("bob", "short")
    with pytest.raises(ValidationError):
        auth.register("bob", "lettersonly")


def test_change_password(auth):
    auth.change_password("alice", "secret1", "newpass9")
    auth.login("alice", "newpass9")
    with pytest.raises(AuthenticationError):
        auth.change_password("alice", "secret1", "x1x1x1x1")


# --------------------------------------------------------------- expenses
def test_expense_crud_and_search(db):
    em = ExpenseManager(db, "alice")
    e = em.add(250, "food", "2026-01-10", "Pizza night", "upi")
    assert e.category == "Food" and e.payment_mode == "UPI"
    em.add(1200, "Shopping", "2026-01-15", "Shoes")
    em.update(e.id, amount="300", description="Pizza & drinks")
    assert em.get(e.id).amount == 300
    assert [t.id for t in em.search("pizza")] == [e.id]
    assert len(em.search(min_amount=500)) == 1
    assert len(em.list(start="2026-01-12")) == 1
    em.delete(e.id)
    with pytest.raises(NotFoundError):
        em.get(e.id)


def test_expense_validation(db):
    em = ExpenseManager(db, "alice")
    for bad in [dict(amount=-5, category="Food"), dict(amount="abc", category="Food"),
                dict(amount=10, category="Nope"), dict(amount=10, category="Food", date="2026-13-01")]:
        with pytest.raises(ValidationError):
            em.add(**bad)


def test_users_are_isolated(db):
    ExpenseManager(db, "alice").add(100, "Food")
    e = ExpenseManager(db, "bob").add(200, "Food")
    assert len(ExpenseManager(db, "alice").list()) == 1
    with pytest.raises(NotFoundError):
        ExpenseManager(db, "alice").delete(e.id)


def test_totals_and_grouping(db):
    em = ExpenseManager(db, "alice")
    em.add(100, "Food", "2026-03-01")
    em.add(50, "Food", "2026-03-05")
    em.add(300, "Rent", "2026-03-02")
    em.add(40, "Food", "2026-04-01")
    assert em.total(month="2026-03") == 450
    assert em.by_category(month="2026-03") == {"Rent": 300, "Food": 150}
    assert em.by_month("2026")["2026-04"] == 40
    assert IncomeManager(db, "alice").add(5000, "salary").category == "Salary"


# ----------------------------------------------------------------- budget
def test_budget_alerts(db):
    bm = BudgetManager(db, "alice")
    bm.set_budget(MONTH, 1000)
    bm.set_budget(MONTH, 200, "Food")
    bm.set_budget(MONTH, 300, "Food")          # replaces, not duplicates
    assert len(bm.list_budgets(MONTH)) == 2
    em = ExpenseManager(db, "alice")
    em.add(350, "Food")
    em.add(500, "Travel")
    levels = {s.budget.category: s.level for s in bm.status(MONTH)}
    assert levels == {"Overall": "WARNING", "Food": "EXCEEDED"}
    assert len(bm.alerts(MONTH)) == 2


# ---------------------------------------------------------------- savings
def test_savings_goal(db):
    sm = SavingsManager(db, "alice")
    g = sm.create_goal("Bike", 1000, (TODAY + timedelta(days=90)).isoformat())
    sm.deposit(g.id, 600)
    assert sm.get(g.id).progress == 60
    assert sm.monthly_required(sm.get(g.id)) > 0
    with pytest.raises(ValidationError):
        sm.withdraw(g.id, 700)
    sm.deposit(g.id, 500)
    assert sm.get(g.id).completed
    with pytest.raises(ValidationError):
        sm.create_goal("Past", 100, "2000-01-01")


# ------------------------------------------------------------------ bills
def test_bills_reminders_and_recurring(db):
    bm = BillManager(db, "alice")
    soon = bm.add_bill("Power", 900, (TODAY + timedelta(days=2)).isoformat(), "monthly")
    bm.add_bill("Old", 100, (TODAY - timedelta(days=1)).isoformat())
    bm.add_bill("Later", 100, (TODAY + timedelta(days=40)).isoformat())
    assert [b.name for b in bm.upcoming()] == ["Power"]
    assert [b.name for b in bm.overdue()] == ["Old"]
    nxt = bm.mark_paid(soon.id)
    assert nxt and nxt.due_date > soon.due_date and not nxt.paid
    assert ExpenseManager(db, "alice").list()[0].category == "Bills"


def test_add_months_clamps_day():
    from tracker.bills import _add_months
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert _add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


# ---------------------------------------------------------------- reports
def test_reports(db, tmp_path):
    em, im = ExpenseManager(db, "alice"), IncomeManager(db, "alice")
    im.add(10000, "Salary", f"{MONTH}-01")
    em.add(2000, "Food", f"{MONTH}-01")
    em.add(3000, "Rent", f"{MONTH}-01")
    BudgetManager(db, "alice").set_budget(MONTH, 4000)
    rg = ReportGenerator(db, "alice", tmp_path / "reports")
    s = rg.monthly_summary(MONTH)
    assert s["net"] == 5000 and s["savings_rate"] == 50.0
    y = rg.yearly_summary(MONTH[:4])
    assert y["expense"] == 5000
    csv_text = rg.export_csv().read_text()
    assert "Rent" in csv_text and "Salary" in csv_text
    for path in (rg.chart_category_pie(month=MONTH), rg.chart_monthly_trend(MONTH[:4]),
                 rg.chart_budget(MONTH), rg.export_pdf(month=MONTH), rg.export_pdf(year=MONTH[:4])):
        assert path.exists() and path.stat().st_size > 1000


# ------------------------------------------------------------ backup & db
def test_backup_and_restore(db, tmp_path):
    em = ExpenseManager(db, "alice")
    em.add(100, "Food")
    bk = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bk.create_backup()
    em.add(999, "Food")
    safety = bk.restore(archive)
    assert len(em.list()) == 1 and safety.exists()
    assert len(bk.list_backups()) == 2
    bad = tmp_path / "backups" / "backup_bad.zip"
    bad.write_text("not a zip")
    with pytest.raises(BackupError):
        bk.restore(bad)


def test_corrupted_file_raises(db):
    (db.data_dir / "expenses.json").write_text("{broken")
    with pytest.raises(DatabaseError):
        ExpenseManager(db, "alice").list()


def test_json_persistence(db):
    ExpenseManager(db, "alice").add(42, "Food")
    data = json.loads((db.data_dir / "expenses.json").read_text())
    assert data[0]["amount"] == 42.0


# ------------------------------------------------------------------ admin
def test_admin(db, auth):
    admin = auth.login("admin", "admin123")
    am = AdminManager(db, admin)
    ExpenseManager(db, "alice").add(10, "Food")
    assert am.system_stats()["total_users"] == 2
    am.set_active("alice", False)
    with pytest.raises(AuthenticationError):
        auth.login("alice", "secret1")
    am.set_active("alice", True)
    am.reset_password("alice", "reset99")
    auth.login("alice", "reset99")
    with pytest.raises(ValidationError):
        am.delete_user("admin")
    assert am.delete_user("alice")["expenses"] == 1
    assert auth.get_user("alice") is None
    with pytest.raises(AuthenticationError):
        AdminManager(db, auth.register("bob", "bobpass1"))
