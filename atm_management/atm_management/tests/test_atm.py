"""Unit tests — run with:  python -m pytest -q"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from account import AccountManager, FixedDepositManager, LoanManager, fd_rate_for  # noqa: E402
from admin import AdminManager  # noqa: E402
from auth import AuthManager  # noqa: E402
from backup import BackupManager  # noqa: E402
from database import JSONDatabase  # noqa: E402
from report import ReportGenerator  # noqa: E402
from transaction import TransactionManager  # noqa: E402
from utils import (ATMError, AccountFrozenError, AccountNotFoundError, AuthenticationError,  # noqa: E402
                   BackupError, DatabaseError, InsufficientFundsError, LimitExceededError,
                   ValidationError, hash_secret, simple_interest, validate_email, validate_phone,
                   verify_secret)

PIN = "2580"


@pytest.fixture
def db(tmp_path):
    return JSONDatabase(tmp_path / "data")


@pytest.fixture
def svc(db):
    auth = AuthManager(db)
    return {"db": db, "auth": auth, "acc": AccountManager(db, auth), "txn": TransactionManager(db, auth),
            "fd": FixedDepositManager(db, auth), "loan": LoanManager(db, auth)}


@pytest.fixture
def alice(svc):
    return svc["acc"].register("alice sharma", "9876543210", "alice@mail.com", PIN, PIN, "Savings", 10000)


@pytest.fixture
def bob(svc):
    return svc["acc"].register("Bob Roy", "8765432109", "bob@mail.com", "7391", "7391", "Current", 5000)


# ---------------------------------------------------------- registration
def test_register_creates_account(svc, alice):
    assert alice["name"] == "Alice Sharma"
    assert len(alice["account_no"]) == 12 and alice["account_no"].startswith("5001")
    assert alice["balance"] == 10000
    assert "pin" not in alice and alice["pin_hash"] != PIN
    assert svc["txn"].history(alice["account_no"])[0]["type"] == "OPENING_DEPOSIT"


def test_duplicate_prevention(svc, alice):
    with pytest.raises(ValidationError, match="phone"):
        svc["acc"].register("X Y", "9876543210", "other@mail.com", PIN, PIN)
    with pytest.raises(ValidationError, match="email"):
        svc["acc"].register("X Y", "9123456780", "ALICE@mail.com", PIN, PIN)


@pytest.mark.parametrize("phone,email,pin,confirm,deposit", [
    ("12345", "a@b.com", PIN, PIN, 1000),          # bad phone
    ("9123456780", "not-an-email", PIN, PIN, 1000),
    ("9123456780", "a@b.com", "12a4", "12a4", 1000),
    ("9123456780", "a@b.com", "1111", "1111", 1000),  # weak PIN
    ("9123456780", "a@b.com", PIN, "9999", 1000),     # mismatch
    ("9123456780", "a@b.com", PIN, PIN, 100),         # below minimum deposit
])
def test_registration_validation(svc, phone, email, pin, confirm, deposit):
    with pytest.raises(ValidationError):
        svc["acc"].register("Test User", phone, email, pin, confirm, "Savings", deposit)


def test_validators():
    assert validate_phone("+91 98765-43210") == "9876543210"
    assert validate_email(" A.B@Mail.COM ") == "a.b@mail.com"
    h, s = hash_secret("4826")
    assert verify_secret("4826", h, s) and not verify_secret("4827", h, s)


# ----------------------------------------------------------------- auth
def test_login_and_lockout(svc, alice):
    no = alice["account_no"]
    assert svc["auth"].login(no, PIN)["account_no"] == no
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            svc["auth"].login(no, "0000")
    with pytest.raises(AccountFrozenError):
        svc["auth"].login(no, "0000")
    with pytest.raises(AccountFrozenError):          # even the right PIN fails now
        svc["auth"].login(no, PIN)
    with pytest.raises(AccountNotFoundError):
        svc["auth"].login("500100000000", PIN)


def test_successful_login_resets_attempts(svc, alice):
    no = alice["account_no"]
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            svc["auth"].login(no, "0000")
    svc["auth"].login(no, PIN)
    with pytest.raises(AuthenticationError):        # counter restarted: not frozen
        svc["auth"].login(no, "0000")


def test_change_pin(svc, alice):
    no = alice["account_no"]
    with pytest.raises(ValidationError):
        svc["auth"].change_pin(no, PIN, "4826", "4827")
    svc["auth"].change_pin(no, PIN, "4826", "4826")
    svc["auth"].login(no, "4826")


# ---------------------------------------------------------- transactions
def test_deposit_and_withdraw(svc, alice):
    no = alice["account_no"]
    t = svc["txn"].deposit(no, 2500)
    assert t["balance_after"] == 12500
    t = svc["txn"].withdraw(no, PIN, 2000)
    assert t["balance_after"] == 10500
    with pytest.raises(ValidationError):
        svc["txn"].withdraw(no, PIN, 150)            # not a multiple of 100
    with pytest.raises(InsufficientFundsError):
        svc["txn"].withdraw(no, PIN, 10100)          # would break min balance (500)
    with pytest.raises(AuthenticationError):
        svc["txn"].withdraw(no, "0000", 100)
    with pytest.raises(ValidationError):
        svc["txn"].deposit(no, -5)


def test_withdrawal_limits(svc, alice):
    no = alice["account_no"]
    svc["txn"].deposit(no, 100000)
    with pytest.raises(LimitExceededError):
        svc["txn"].withdraw(no, PIN, 25000)          # per-transaction cap
    for _ in range(2):
        svc["txn"].withdraw(no, PIN, 20000)
    svc["txn"].withdraw(no, PIN, 10000)
    with pytest.raises(LimitExceededError):
        svc["txn"].withdraw(no, PIN, 100)            # daily cap 50,000 reached


def test_transfer(svc, alice, bob):
    a, b = alice["account_no"], bob["account_no"]
    out, inc = svc["txn"].transfer(a, PIN, b, 3000, "rent")
    assert out["balance_after"] == 7000 and inc["balance_after"] == 8000
    assert svc["acc"].get(b)["balance"] == 8000
    with pytest.raises(InsufficientFundsError):
        svc["txn"].transfer(a, PIN, b, 6600)
    with pytest.raises(ValidationError):
        svc["txn"].transfer(a, PIN, a, 10)
    with pytest.raises(AccountNotFoundError):
        svc["txn"].transfer(a, PIN, "500199999999", 10)
    AdminManager(svc["db"], "admin").freeze(b)
    with pytest.raises(AccountFrozenError):
        svc["txn"].transfer(a, PIN, b, 10)
    assert svc["acc"].get(a)["balance"] == 7000      # failed transfers changed nothing


def test_balance_history_and_mini_statement(svc, alice, bob):
    a = alice["account_no"]
    for amt in (100, 200, 300, 400, 500, 600):
        svc["txn"].deposit(a, amt)
    svc["txn"].transfer(a, PIN, bob["account_no"], 1000)
    bal = svc["txn"].balance_inquiry(a, PIN)
    assert bal["balance"] == 11100 and bal["available"] == 10600
    ms = svc["txn"].mini_statement(a)
    assert len(ms["transactions"]) == 5 and ms["transactions"][0]["type"] == "TRANSFER_OUT"
    assert len(svc["txn"].history(a, "deposit")) == 6
    assert len(svc["txn"].history(a, "transfer")) == 1
    assert "TRANSACTION RECEIPT" in svc["txn"].receipt(ms["transactions"][0])


# ----------------------------------------------------- interest & FDs
def test_simple_interest():
    assert simple_interest(10000, 7, 2) == (1400.0, 11400.0)
    assert AccountManager.interest_calculator(5000, 6, 0.5)["interest"] == 150
    with pytest.raises(ValidationError):
        simple_interest(1000, 0, 1)


def test_fixed_deposit_lifecycle(svc, alice):
    a = alice["account_no"]
    assert fd_rate_for(12) == 6.5
    with pytest.raises(ValidationError):
        fd_rate_for(3)
    start = date.today()
    fd = svc["fd"].create(a, PIN, 5000, 12, on=start)
    assert fd["maturity_amount"] == 5325 and svc["acc"].get(a)["balance"] == 5000
    quote = svc["fd"].closure_quote(a, fd["fd_id"], on=start + timedelta(days=73))
    assert quote["premature"] and quote["rate"] == 5.5 and quote["interest"] == 55
    done = svc["fd"].close(a, PIN, fd["fd_id"], on=start + timedelta(days=400))
    assert not done["premature"] and svc["acc"].get(a)["balance"] == 10325
    with pytest.raises(ATMError):
        svc["fd"].close(a, PIN, fd["fd_id"])
    with pytest.raises(InsufficientFundsError):
        svc["fd"].create(a, PIN, 10000, 12)          # min balance must remain


# --------------------------------------------------------------- loans
def test_loan_lifecycle(svc, alice):
    a = alice["account_no"]
    q = LoanManager.quote("Personal", 12000, 12)
    assert q["interest"] == 1320 and q["emi"] == 1110
    loan = svc["loan"].apply(a, PIN, "personal", 12000, 12)
    assert svc["acc"].get(a)["balance"] == 22000
    with pytest.raises(ValidationError):
        svc["loan"].repay(a, PIN, loan["loan_id"], 99999)
    l = svc["loan"].repay(a, PIN, loan["loan_id"], 1110)
    assert l["outstanding"] == 12210 and LoanManager.emis_paid(l) == 1
    l = svc["loan"].repay(a, PIN, loan["loan_id"], 12210)
    assert l["status"] == "CLOSED" and l["outstanding"] == 0
    svc["loan"].apply(a, PIN, "Home", 10000, 24)
    svc["loan"].apply(a, PIN, "Vehicle", 10000, 24)
    with pytest.raises(LimitExceededError):
        svc["loan"].apply(a, PIN, "Education", 10000, 24)
    with pytest.raises(ValidationError):
        LoanManager.quote("Personal", 5000, 12)       # below minimum


# --------------------------------------------------------------- admin
def test_admin(svc, alice, bob):
    auth = svc["auth"]
    auth.admin_login("admin", "admin123")
    with pytest.raises(AuthenticationError):
        auth.admin_login("admin", "wrong")
    am = AdminManager(svc["db"], "admin")
    assert len(am.view_customers()) == 2
    assert [c["name"] for c in am.search_customers("ali")] == ["Alice Sharma"]
    assert am.search_customers(bob["phone"])[0]["account_no"] == bob["account_no"]
    am.freeze(alice["account_no"], "test")
    with pytest.raises(AccountFrozenError):
        svc["txn"].deposit(alice["account_no"], 100)
    am.unfreeze(alice["account_no"])
    svc["txn"].deposit(alice["account_no"], 100)
    loan = svc["loan"].apply(bob["account_no"], "7391", "Personal", 10000, 6)
    with pytest.raises(ATMError, match="active loan"):
        am.delete_account(bob["account_no"])
    svc["loan"].repay(bob["account_no"], "7391", loan["loan_id"], loan["total_payable"])
    r = am.delete_account(bob["account_no"])
    assert r["balance_to_refund"] == bob["balance"] + 10000 - loan["total_payable"]
    assert r["removed"]["transactions"] >= 3 and len(am.view_customers()) == 1
    auth.change_admin_password("admin", "admin123", "newpass1")
    auth.admin_login("admin", "newpass1")


# -------------------------------------------------------- reports & backup
def test_reports(svc, alice, bob, tmp_path):
    svc["txn"].transfer(alice["account_no"], PIN, bob["account_no"], 1000)
    svc["fd"].create(alice["account_no"], PIN, 2000, 24)
    svc["loan"].apply(alice["account_no"], PIN, "Education", 50000, 36)
    rg = ReportGenerator(svc["db"], tmp_path / "reports")
    pdf = rg.account_statement_pdf(alice["account_no"])
    assert pdf.read_bytes()[:4] == b"%PDF" and pdf.stat().st_size > 2000
    assert "Alice Sharma" in rg.export_customers_csv().read_text()
    tx = rg.export_transactions_csv(alice["account_no"]).read_text().splitlines()
    assert len(tx) == 1 + 4                          # header + opening, transfer, FD, loan
    s = rg.system_summary()
    assert s["total_customers"] == 2 and s["active_loans"] == 1 and s["active_fds"] == 1


def test_backup_restore(svc, alice, tmp_path):
    db = svc["db"]
    bm = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bm.create_backup()
    assert set(bm.verify(archive)) == {"customers.json", "transactions.json", "loans.json",
                                       "fixed_deposits.json", "admins.json"}
    svc["txn"].deposit(alice["account_no"], 5000)
    safety = bm.restore(archive)
    assert svc["acc"].get(alice["account_no"])["balance"] == 10000 and safety.exists()
    assert len(bm.list_backups()) == 2
    bad = tmp_path / "backups" / "atm_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bm.restore(bad)


def test_corrupted_database(db):
    (db.data_dir / "customers.json").write_text("{oops")
    with pytest.raises(DatabaseError):
        db.all("customers")


def test_data_persists_across_instances(tmp_path, svc, alice):
    again = AccountManager(JSONDatabase(svc["db"].data_dir))
    assert again.get(alice["account_no"])["balance"] == 10000
    raw = json.loads((svc["db"].data_dir / "customers.json").read_text())
    assert raw[0]["account_no"] == alice["account_no"]
