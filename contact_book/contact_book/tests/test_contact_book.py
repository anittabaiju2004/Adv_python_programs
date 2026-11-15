"""Unit tests — run with:  python -m pytest -q"""
import csv
import json
from datetime import date, timedelta

import pytest

from contactbook.admin import AdminManager
from contactbook.auth import AuthManager
from contactbook.backup import BackupManager
from contactbook.contacts import ContactManager
from contactbook.database import JSONDatabase
from contactbook.reports import ReportGenerator, export_users_report
from contactbook.utils import (AuthenticationError, BackupError, ContactBookError, DatabaseError,
                               DuplicateError, NotFoundError, ValidationError, age_on_next_birthday,
                               days_until_birthday, format_phone, hash_password, validate_email,
                               validate_phone, verify_password)


@pytest.fixture
def db(tmp_path):
    return JSONDatabase(tmp_path / "data")


@pytest.fixture
def auth(db):
    a = AuthManager(db)
    a.register("alice", "secret1", "secret1", "Alice")
    return a


@pytest.fixture
def cm(db, auth):
    return ContactManager(db, "alice")


def add(cm, first="Ravi", phone="9876543210", **kw):
    return cm.add(first_name=first, phone=phone, **kw)


# ================================================================ utilities
@pytest.mark.parametrize("raw,expected", [
    ("9876543210", "+919876543210"), ("98765 43210", "+919876543210"), ("+91-98765-43210", "+919876543210"),
    ("098765 43210", "+919876543210"), ("0091 9876543210", "+919876543210"),
    ("+1 (415) 555-2671", "+14155552671"), ("0471 2345678", "04712345678"),
])
def test_phone_normalisation(raw, expected):
    assert validate_phone(raw) == expected


@pytest.mark.parametrize("bad", ["12345", "abcdefghij", "5876543210", "+0 123"])
def test_phone_invalid(bad):
    with pytest.raises(ValidationError):
        validate_phone(bad)


def test_email_and_helpers():
    assert validate_email(" Ravi.K@Mail.CO.in ") == "ravi.k@mail.co.in"
    assert validate_email("") == ""
    for bad in ("ravi@", "ravi@mail", "@mail.com", "ra vi@mail.com"):
        with pytest.raises(ValidationError):
            validate_email(bad)
    assert format_phone("+919876543210") == "+91 98765 43210"
    h, s = hash_password("abc123")
    assert verify_password("abc123", h, s) and not verify_password("abc124", h, s)


def test_birthday_helpers():
    today = date(2026, 11, 14)
    assert days_until_birthday("1990-11-20", today) == 6
    assert days_until_birthday("1990-11-14", today) == 0
    assert days_until_birthday("1990-01-05", today) == 52
    assert age_on_next_birthday("1990-01-05", today) == 37
    assert days_until_birthday("2000-02-29", date(2027, 2, 1)) == 27      # 28 Feb in non-leap year


# ===================================================================== auth
def test_auth(db, auth):
    assert auth.login("ALICE", "secret1").username == "alice"
    assert auth.login("admin", "admin123").is_admin
    with pytest.raises(AuthenticationError):
        auth.login("alice", "wrong1")
    with pytest.raises(ValidationError):
        auth.register("alice", "secret1", "secret1")       # taken
    with pytest.raises(ValidationError):
        auth.register("bob", "abc", "abc")                  # weak
    with pytest.raises(ValidationError):
        auth.register("bob", "secret1", "secret2")          # mismatch
    auth.change_password("alice", "secret1", "newpass9", "newpass9")
    auth.login("alice", "newpass9")


def test_login_attempt_limit(db, auth):
    for _ in range(5):
        with pytest.raises(AuthenticationError, match="Invalid"):
            auth.login("alice", "nope111")
    with pytest.raises(AuthenticationError, match="Too many"):
        auth.login("alice", "secret1")


# ================================================================= contacts
def test_add_and_get(cm):
    c = add(cm, "  ravi ", "98765 43210", last_name="Kumar", email="RAVI@x.com", category="work",
            birthday="1990-05-01", favorite="yes")
    assert (c.first_name, c.phone, c.email, c.category, c.favorite) == ("ravi", "+919876543210", "ravi@x.com", "Work", True)
    assert cm.get(c.id).full_name == "ravi Kumar"


@pytest.mark.parametrize("data", [
    {"first_name": "", "phone": "9876543210"},
    {"first_name": "Ravi", "phone": ""},
    {"first_name": "123", "phone": "9876543210"},
    {"first_name": "Ravi", "phone": "9876543210", "email": "bad"},
    {"first_name": "Ravi", "phone": "9876543210", "category": "Nope"},
    {"first_name": "Ravi", "phone": "9876543210", "birthday": "2999-01-01"},
    {"first_name": "Ravi", "phone": "9876543210", "alt_phone": "98765 43210"},
    {"first_name": "Ravi", "phone": "9876543210", "colour": "red"},
])
def test_add_validation(cm, data):
    with pytest.raises((ValidationError, ContactBookError)):
        cm.add(**data)


def test_duplicates(cm):
    a = add(cm, email="r@x.com")
    cm.update(a.id, phone="9876543210", first_name="Ravi K")   # own number is not a duplicate
    with pytest.raises(DuplicateError, match="Ravi"):
        add(cm, "Other", "+91 98765 43210")                 # same number, different format
    with pytest.raises(DuplicateError):
        add(cm, "Other", "9123456789", email="R@X.com")
    with pytest.raises(DuplicateError):
        add(cm, "Other", "9123456789", alt_phone="9876543210")
    add(cm, "Other", "9876543210", allow_duplicate=True)
    b = add(cm, "Meera", "9123456789")
    with pytest.raises(DuplicateError):
        cm.update(b.id, phone="9876543210")


def test_update(cm):
    c = add(cm, email="r@x.com", company="Acme")
    u = cm.update(c.id, email="", company="Globex", last_name="Nair")
    assert (u.email, u.company, u.last_name) == ("", "Globex", "Nair")
    assert u.updated_at >= c.updated_at
    with pytest.raises(ValidationError):
        cm.update(c.id)
    with pytest.raises(NotFoundError):
        cm.update("nope", company="X")


def test_users_cannot_see_each_others_contacts(db, auth, cm):
    auth.register("bob", "secret2", "secret2")
    c = add(cm)
    bob = ContactManager(db, "bob")
    assert bob.list() == []
    with pytest.raises(NotFoundError):
        bob.get(c.id)
    add(bob)                                                # same number is fine for another user


def test_search_sort_and_group(cm):
    add(cm, "Zara", "9000000001", company="Infosys", notes="met at conference")
    add(cm, "anil", "9000000002", email="anil@tcs.com", category="Work", favorite=True)
    add(cm, "Bina", "+44 20 7946 0958", category="Family")
    assert [c.first_name for c in cm.list()] == ["anil", "Bina", "Zara"]
    assert [c.first_name for c in cm.search("infos")] == ["Zara"]
    assert [c.first_name for c in cm.search("conference")] == ["Zara"]
    assert [c.first_name for c in cm.search("0002")] == ["anil"]     # phone digits
    assert [c.first_name for c in cm.search("tcs")] == ["anil"]
    assert [c.first_name for c in cm.search("", favorites_only=True)] == ["anil"]
    assert [c.first_name for c in cm.list(category="family")] == ["Bina"]
    assert list(cm.by_letter()) == ["A", "B", "Z"]
    assert cm.list(sort_by="recent")[0].first_name == "Bina"
    with pytest.raises(ValidationError):
        cm.list(sort_by="age")


def test_favourite_toggle(cm):
    c = add(cm)
    assert cm.toggle_favorite(c.id).favorite
    assert not cm.toggle_favorite(c.id).favorite


def test_recycle_bin(cm):
    a = add(cm)
    b = add(cm, "Meera", "9123456789")
    cm.delete(a.id)
    assert [c.id for c in cm.list()] == [b.id] and [c.id for c in cm.trash()] == [a.id]
    with pytest.raises(NotFoundError):
        cm.get(a.id)
    add(cm, "New", "9876543210")                            # number free again while in the bin
    with pytest.raises(DuplicateError):
        cm.restore(a.id)                                    # ...so restoring would duplicate
    cm.delete(cm.search("New")[0].id)
    cm.restore(a.id)
    assert cm.get(a.id).first_name == "Ravi"
    with pytest.raises(ContactBookError):
        cm.purge(a.id)                                      # must be in the bin first
    assert cm.empty_trash() == 1 and cm.trash() == []


def test_categories(cm):
    assert "Other" in cm.categories()
    cm.add_category("gym buddies")
    c = add(cm, category="Gym Buddies")
    with pytest.raises(ValidationError):
        cm.add_category("GYM BUDDIES")
    assert cm.rename_category("gym buddies", "Fitness") == 1
    assert cm.get(c.id).category == "Fitness"
    assert cm.delete_category("Fitness") == 1
    assert cm.get(c.id).category == "Other" and "Fitness" not in cm.categories()
    with pytest.raises(ValidationError):
        cm.delete_category("Other")


def test_birthdays_and_stats(cm):
    in3 = date.today() + timedelta(days=3)
    soon = in3.replace(year=in3.year - 30, day=min(in3.day, 28) if in3.month == 2 else in3.day).isoformat()
    add(cm, "Ravi", birthday=soon, favorite=True, email="r@x.com", company="Acme")
    add(cm, "Meera", "9123456789", birthday="1985-01-01" if date.today().month < 11 else "1985-06-01")
    upcoming = cm.upcoming_birthdays(7)
    assert [u["contact"].first_name for u in upcoming] == ["Ravi"]
    s = cm.stats()
    assert s["total"] == 2 and s["favorites"] == 1 and s["with_email"] == 1 and s["top_companies"] == [("Acme", 1)]


# =========================================================== import/export
def test_csv_round_trip_and_vcard(db, auth, cm, tmp_path):
    add(cm, "Ravi", last_name="Kumar", email="r@x.com", company="Johnson & Johnson", category="Work",
        favorite=True, notes="Line one; two, three", birthday="1990-05-01")
    add(cm, "Meera", "9123456789", category="Family")
    rg = ReportGenerator(db, "alice", tmp_path / "reports")
    csv_path = rg.export_csv()
    vcf = rg.export_vcard().read_text()
    assert vcf.count("BEGIN:VCARD") == 2 and "ORG:Johnson & Johnson" in vcf
    assert "NOTE:Line one\\; two\\, three" in vcf and "CATEGORIES:Work,Favorites" in vcf
    pdf = rg.export_pdf(group_by="category")
    assert pdf.read_bytes()[:4] == b"%PDF"
    assert rg.export_pdf(favorites_only=True).exists()
    # import the export into a fresh user
    auth.register("bob", "secret2", "secret2")
    r = ContactManager(db, "bob").import_csv(csv_path)
    assert r == {"imported": 2, "skipped": []}
    ravi = ContactManager(db, "bob").search("Kumar")[0]
    assert ravi.favorite and ravi.company == "Johnson & Johnson" and ravi.birthday == "1990-05-01"
    with pytest.raises(ContactBookError):
        rg.export_csv(category="Business")                  # nothing to export


def test_import_reports_bad_rows_and_creates_categories(cm, tmp_path):
    path = tmp_path / "in.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["First Name", "Phone", "Email", "Category"])
        w.writerows([["Asha", "9000000011", "", "Cricket Club"], ["", "9000000012", "", ""],
                     ["Biju", "12", "", ""], ["Asha Dup", "9000000011", "", ""], ["Chitra", "9000000013", "c@x.com", ""]])
    r = cm.import_csv(path)
    assert r["imported"] == 2 and len(r["skipped"]) == 3
    assert r["skipped"][0].startswith("Row 3") and "Cricket Club" in cm.categories()
    bad = tmp_path / "bad.csv"
    bad.write_text("Name,Mobile\nX,1\n")
    with pytest.raises(ContactBookError, match="First Name"):
        cm.import_csv(bad)


# ==================================================================== admin
def test_admin(db, auth, cm, tmp_path):
    add(cm)
    add(cm, "Meera", "9123456789", favorite=True)
    admin = auth.login("admin", "admin123")
    am = AdminManager(db, admin)
    assert {u["username"]: u["contact_count"] for u in am.list_users()} == {"admin": 0, "alice": 2}
    s = am.system_stats()
    assert s["total_contacts"] == 2 and s["favourite_contacts"] == 1 and s["top_users"] == [("alice", 2)]
    am.set_active("alice", False)
    with pytest.raises(AuthenticationError, match="deactivated"):
        auth.login("alice", "secret1")
    am.set_active("alice", True)
    am.reset_password("alice", "reset99")
    auth.login("alice", "reset99")
    report = export_users_report(db, tmp_path / "r").read_text()
    assert "alice" in report and "9876543210" not in report     # no private data in admin report
    with pytest.raises(ValidationError):
        am.delete_user("admin")
    assert am.delete_user("alice") == 2 and db.all("contacts") == []
    with pytest.raises(AuthenticationError):
        AdminManager(db, auth.register("bob", "secret2", "secret2"))


# ========================================================= backup & database
def test_backup_restore(db, cm, tmp_path):
    add(cm)
    bm = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bm.create_backup()
    add(cm, "Meera", "9123456789")
    safety = bm.restore(archive)
    assert len(cm.list()) == 1 and safety.exists()
    bad = tmp_path / "backups" / "contacts_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bm.restore(bad)


def test_database_persistence_and_corruption(db, cm):
    c = add(cm)
    assert json.loads((db.data_dir / "contacts.json").read_text())[0]["id"] == c.id
    assert ContactManager(JSONDatabase(db.data_dir), "alice").get(c.id).phone == "+919876543210"
    (db.data_dir / "contacts.json").write_text("[{broken")
    with pytest.raises(DatabaseError):
        cm.list()
