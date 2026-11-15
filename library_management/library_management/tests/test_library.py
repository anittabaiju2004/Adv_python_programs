"""Unit tests — run with:  python -m pytest -q"""
import json
from datetime import date, timedelta

import pytest

from library.admin import AdminPanel
from library.auth import AuthManager, UserManager, can, require
from library.backup import BackupManager
from library.books import BookManager
from library.circulation import CirculationManager
from library.database import JSONDatabase
from library.fines import FineManager
from library.librarian import LibrarianDesk
from library.members import MemberManager
from library.qr import qrcode_available, save_qr_png
from library.reports import ReportGenerator
from library.reservations import ReservationManager
from library.utils import (AuthenticationError, BackupError, CirculationError, DatabaseError, LibraryError,
                           NotFoundError, PermissionDenied, ValidationError, validate_isbn)

T = date.today()


def d(n: int) -> date:
    return T + timedelta(days=n)


@pytest.fixture
def db(tmp_path):
    x = JSONDatabase(tmp_path / "data")
    AuthManager(x)
    return x


@pytest.fixture
def bm(db):
    return BookManager(db, "lib")


@pytest.fixture
def mm(db):
    return MemberManager(db, "lib")


@pytest.fixture
def circ(db):
    return CirculationManager(db, "lib")


@pytest.fixture
def python_book(bm):          # 2 copies, price 600
    return bm.add("Python Crash Course", "Eric Matthes", "Computer Science", 600, copies=2,
                  isbn="978-1-59327-603-4", publisher="No Starch", year=2019, shelf="cs-12")


@pytest.fixture
def anitta(mm):               # Student: 3 books, 14 days, Rs 2/day
    return mm.add("Anitta Joseph", "Student", "9847012345", "anitta@x.com", id_number="CS21001", on=d(-60))[0]


@pytest.fixture
def rahul(mm):                # Faculty: 6 books, 30 days, Rs 1/day
    return mm.add("Rahul Menon", "Faculty", "9895098765", id_number="EMP204", on=d(-60))[0]


# ================================================================ utilities
def test_isbn_validation():
    assert validate_isbn("0-306-40615-2") == "9780306406157"          # ISBN-10 -> ISBN-13
    assert validate_isbn("978-0-306-40615-7") == "9780306406157"
    assert validate_isbn("080442957X") == "9780804429573"
    for bad in ("0306406153", "9780306406158", "12345"):
        with pytest.raises(ValidationError):
            validate_isbn(bad)


# ============================================================ auth / roles
def test_staff_and_member_logins(db, mm):
    um = UserManager(db, "admin")
    _, temp = um.add("asst", "Divya", "assistant")
    auth = AuthManager(db)
    u = auth.login("asst", temp)
    assert can(u, "circulation") and not can(u, "books.manage")
    with pytest.raises(PermissionDenied):
        require(u, "fines.waive")
    m, mtemp = mm.add("Arjun Das", "Public", "9000000001")
    mu = auth.login(m["member_id"].lower(), mtemp)
    assert mu["role"] == "member" and mu["must_change_password"] and can(mu, "portal") and not can(mu, "circulation")
    assert [u["username"] for u in um.list()] == ["admin", "asst"]       # members not listed as staff
    mm.suspend(m["member_id"], "Misconduct")
    with pytest.raises(AuthenticationError, match="disabled"):
        auth.login(m["member_id"], mtemp)


# =================================================================== books
def test_books_and_copies(bm, python_book):
    assert python_book["book_id"] == "B0001" and python_book["shelf"] == "CS-12"
    assert [c["accession"] for c in bm.copies("B0001")] == ["ACC00001", "ACC00002"]
    with pytest.raises(ValidationError, match="already catalogued"):
        bm.add("Dup", "X", "Fiction", 100, isbn="9781593276034")
    with pytest.raises(ValidationError, match="already exists"):
        bm.add("python crash course", "eric matthes", "Computer Science", 600)
    assert bm.get("9781593276034")["book_id"] == "B0001" and bm.get("ACC00002")["book_id"] == "B0001"
    bm.add_copies("B0001", 1)
    assert bm.availability("B0001")["available"] == 3
    bm.withdraw_copy("ACC00003", "Torn pages")
    assert bm.availability("B0001")["total"] == 2
    assert [b["book_id"] for b in bm.search("matthes")] == ["B0001"]
    assert [b["book_id"] for b in bm.search("978-1-59327-603-4")] == ["B0001"]


# ================================================================= members
def test_members(mm, anitta):
    assert anitta["expires_on"] == (d(-60) + timedelta(days=365)).isoformat()
    with pytest.raises(ValidationError, match="Already registered"):
        mm.add("Someone", "Student", "98470 12345", id_number="CS99")
    with pytest.raises(ValidationError, match="roll number"):
        mm.add("Bob Roy", "Student", "9000000002")
    e = mm.eligibility(anitta["member_id"])
    assert e["can_borrow"] and e["limit"] == 3
    old = mm.add("Old Member", "Public", "9000000003", on=d(-400))[0]
    assert mm.effective_status(old) == "EXPIRED" and not mm.eligibility(old["member_id"])["can_borrow"]
    assert mm.renew(old["member_id"])["expires_on"] == (T + timedelta(days=365)).isoformat()


# ============================================================ circulation
def test_issue_return_on_time(db, circ, python_book, anitta, tmp_path):
    loan = circ.issue(anitta["member_id"], "B0001", on=d(-5))
    assert loan["accession"] == "ACC00001" and loan["due_on"] == (d(-5) + timedelta(days=14)).isoformat()
    assert BookManager(db).get_copy("ACC00001")["status"] == "ISSUED"
    with pytest.raises(CirculationError, match="already has a copy"):
        circ.issue(anitta["member_id"], "ACC00002")
    slip = circ.issue_slip_pdf(loan["loan_id"], tmp_path)
    assert slip.read_bytes()[:4] == b"%PDF"
    r = circ.return_book("ACC00001")
    assert r["fine"] == 0 and r["hold_for"] is None
    assert BookManager(db).get_copy("ACC00001")["status"] == "AVAILABLE"


def test_overdue_fine_capped_and_blocking(db, circ, bm, mm, anitta):
    cheap = bm.add("Short Stories", "Various", "Fiction", 50)
    loan = circ.issue(anitta["member_id"], cheap["book_id"], on=d(-20))      # due d(-6)
    days, fine = circ.overdue_fine(loan)
    assert days == 6 and fine == 12                                          # 6 days x Rs 2
    assert not mm.eligibility(anitta["member_id"])["can_borrow"]             # overdue blocks borrowing
    with pytest.raises(CirculationError, match="cannot be renewed"):
        circ.renew(loan["loan_id"])
    r = circ.return_book(loan["loan_id"], on=d(30))                          # 36 days late -> 72, capped at 50
    assert r["days_late"] == 36 and r["fine"] == 50
    fm = FineManager(db, "lib")
    assert fm.outstanding(anitta["member_id"]) == 50
    f = fm.list(anitta["member_id"])[0]
    fm.pay(f["fine_id"], 20, "Cash")
    assert fm.get(f["fine_id"])["status"] == "PARTIAL"
    with pytest.raises(PermissionDenied):
        require({"role": "assistant"}, "fines.waive")
    fm.waive(f["fine_id"], "First offence")
    assert fm.get(f["fine_id"])["status"] == "PAID" and fm.outstanding(anitta["member_id"]) == 0


def test_borrow_limit_and_fine_limit(db, circ, bm, mm, anitta):
    for i in range(3):
        b = bm.add(f"Book {chr(65 + i)}", "Author", "Fiction", 300)
        circ.issue(anitta["member_id"], b["book_id"])
    extra = bm.add("Book Z", "Author", "Fiction", 300)
    with pytest.raises(CirculationError, match="borrowing limit"):
        circ.issue(anitta["member_id"], extra["book_id"])
    other = mm.add("Fine Holder", "Public", "9000000009")[0]
    FineManager(db).create(other["member_id"], "DAMAGE", 150)
    with pytest.raises(CirculationError, match="unpaid fines"):
        circ.issue(other["member_id"], extra["book_id"])


def test_renewal_rules(db, circ, python_book, anitta, rahul):
    loan = circ.issue(anitta["member_id"], "B0001", on=d(-3))
    loan = circ.renew(loan["loan_id"], on=d(-1))
    with pytest.raises(CirculationError, match="already runs"):
        circ.renew(loan["loan_id"], on=d(-1))                    # same-day renewal changes nothing
    loan = circ.renew(loan["loan_id"])
    assert loan["renewals"] == 2 and loan["due_on"] == (T + timedelta(days=14)).isoformat()
    with pytest.raises(CirculationError, match="Maximum"):
        circ.renew(loan["loan_id"])
    with pytest.raises(PermissionDenied):
        circ.renew(loan["loan_id"], by_member=rahul["member_id"])


def test_reservation_queue_and_holds(db, circ, python_book, mm, anitta, rahul):
    res = ReservationManager(db, "lib")
    third = mm.add("Meera Pillai", "Staff", "9000000004", id_number="ST7")[0]
    with pytest.raises(CirculationError, match="borrow it directly"):
        res.reserve(rahul["member_id"], "B0001")
    circ.issue(anitta["member_id"], "B0001")
    circ.issue(third["member_id"], "B0001")                                   # both copies out
    r1 = res.reserve(rahul["member_id"], "B0001")
    assert r1["status"] == "WAITING" and res.position(r1["res_id"]) == 1
    with pytest.raises(CirculationError, match="already reserved"):
        res.reserve(rahul["member_id"], "B0001")
    with pytest.raises(CirculationError, match="reserved this book"):
        circ.renew("ACC00001")                                                # queue blocks renewal
    out = circ.return_book("ACC00001")
    assert out["hold_for"]["member_id"] == rahul["member_id"]
    copy = BookManager(db).get_copy("ACC00001")
    assert copy["status"] == "ON_HOLD" and copy["hold_for"] == rahul["member_id"]
    with pytest.raises(CirculationError, match="held for another"):
        circ.issue(anitta["member_id"], "ACC00001")
    loan = circ.issue(rahul["member_id"], "B0001")                            # picks the held copy
    assert loan["accession"] == "ACC00001" and res.get(r1["res_id"])["status"] == "FULFILLED"


def test_hold_expiry_passes_to_next(db, circ, python_book, mm, anitta, rahul):
    res = ReservationManager(db, "lib")
    m3 = mm.add("Meera Pillai", "Staff", "9000000004", id_number="ST7")[0]
    m4 = mm.add("Vishnu Varma", "Public", "9000000005")[0]
    circ.issue(anitta["member_id"], "B0001")
    circ.issue(m3["member_id"], "B0001")
    r1 = res.reserve(rahul["member_id"], "B0001")
    r2 = res.reserve(m4["member_id"], "B0001")
    circ.return_book("ACC00002")
    assert res.get(r1["res_id"])["status"] == "READY"
    res.expire_holds(on=d(5))                                                 # hold of 3 days lapsed
    assert res.get(r1["res_id"])["status"] == "EXPIRED"
    assert res.get(r2["res_id"])["status"] == "READY"
    res.cancel(r2["res_id"], by_member=m4["member_id"])
    assert BookManager(db).get_copy("ACC00002")["status"] == "AVAILABLE"


def test_lost_and_damaged(db, circ, python_book, anitta, rahul):
    loan = circ.issue(anitta["member_id"], "B0001")
    lost = circ.mark_lost(loan["loan_id"])
    assert lost["status"] == "LOST" and lost["fine"] == 700                   # 600 + 100 processing
    assert BookManager(db).get_copy(loan["accession"])["status"] == "LOST"
    l2 = circ.issue(rahul["member_id"], "B0001")
    r = circ.return_book(l2["loan_id"], damaged=True, damage_fee=150, note="Water damage")
    assert r["fine"] == 150 and BookManager(db).get_copy(l2["accession"])["status"] == "DAMAGED"
    assert BookManager(db).availability("B0001")["available"] == 0


def test_member_close_rules(db, circ, mm, python_book, anitta):
    circ.issue(anitta["member_id"], "B0001")
    with pytest.raises(LibraryError, match="on loan"):
        mm.close(anitta["member_id"])
    circ.return_book("ACC00001")
    mm.close(anitta["member_id"])
    assert mm.get(anitta["member_id"])["status"] == "CLOSED"


# ============================================================ reports etc.
def test_desk_reports_and_pdfs(db, circ, bm, mm, python_book, anitta, rahul, tmp_path):
    late = circ.issue(anitta["member_id"], "B0001", on=d(-20))
    circ.issue(rahul["member_id"], "B0001")
    ReservationManager(db).reserve(mm.add("Meera Pillai", "Staff", "9000000004", id_number="ST7")[0]["member_id"], "B0001")
    desk = LibrarianDesk(db).dashboard()
    assert desk["on_loan"] == 2 and len(desk["overdue"]) == 1 and desk["waiting"] == 1
    kinds = {r["kind"] for r in LibrarianDesk(db).reminders()}
    assert "OVERDUE" in kinds
    rg = ReportGenerator(db, tmp_path)
    circ.return_book(late["loan_id"])
    s = rg.circulation_summary(d(-30), T)
    assert s["issued"] == 2 and s["returned"] == 1 and s["returned_late"] == 1 and s["on_time_rate"] == 0
    assert rg.popular_books(d(-30), T)[0]["issues"] == 2
    for p in (rg.catalogue_csv(), rg.issued_csv(), rg.overdue_csv(), rg.members_csv(), rg.fines_csv(),
              rg.circulation_csv(d(-30), T), rg.reminders_csv(), rg.availability_pdf(), rg.overdue_pdf(),
              rg.circulation_pdf(d(-30), T), mm.card_pdf(anitta["member_id"], tmp_path)):
        assert p.exists() and p.stat().st_size > 50
    st = AdminPanel(db).statistics()
    assert st["titles"] == 1 and st["loans_active"] == 1 and st["fines_outstanding"] == 12


@pytest.mark.skipif(not qrcode_available(), reason="qrcode package not installed")
def test_qr_png(tmp_path):
    assert save_qr_png("LIB-MEMBER:M0001", tmp_path / "q.png").exists()


def test_qr_png_without_package(tmp_path):
    if qrcode_available():
        pytest.skip("qrcode installed")
    with pytest.raises(LibraryError, match="pip install qrcode"):
        save_qr_png("x", tmp_path / "q.png")


# =========================================================== backup & db
def test_backup_and_persistence(db, bm, python_book, tmp_path):
    bk = BackupManager(db.data_dir, tmp_path / "b")
    archive = bk.create_backup()
    bm.add("New Book", "Someone", "Fiction", 100)
    bk.restore(archive)
    assert len(BookManager(JSONDatabase(db.data_dir)).list()) == 1
    assert json.loads((db.data_dir / "copies.json").read_text())[0]["accession"] == "ACC00001"
    (db.data_dir / "loans.json").write_text("{x")
    with pytest.raises(DatabaseError):
        CirculationManager(db).loans()
    bad = tmp_path / "b" / "library_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bk.restore(bad)
    with pytest.raises(NotFoundError):
        bm.get("B9999")
