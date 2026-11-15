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
from utils import (AccountFrozenError, AccountNotFoundError, AuthenticationError, BackupError,  # noqa: E402
                   BankError, DatabaseError, InsufficientFundsError, LimitExceededError,
                   ValidationError, emi, hash_secret, simple_interest, validate_dob, validate_pan,
                   validate_phone, verify_secret)

PIN = "2580"
ADULT = "1995-06-15"
SENIOR = (date.today().replace(year=date.today().year - 65) - timedelta(days=1)).isoformat()


@pytest.fixture
def db(tmp_path):
    return JSONDatabase(tmp_path / "data")


@pytest.fixture
def svc(db):
    auth = AuthManager(db)
    return {"db": db, "auth": auth, "acc": AccountManager(db, auth), "txn": TransactionManager(db, auth),
            "fd": FixedDepositManager(db, auth), "loan": LoanManager(db, auth),
            "admin": AdminManager(db, "admin")}


@pytest.fixture
def alice(svc):
    return svc["acc"].register("alice sharma", ADULT, "9876543210", "alice@mail.com", "ABCDE1234F",
                               PIN, PIN, "Savings", 20000, "102", nominee="Ravi Sharma")


@pytest.fixture
def bob(svc):
    return svc["acc"].register("Bob Roy", SENIOR, "8765432109", "bob@mail.com", "PQRST6789K",
                               "7391", "7391", "Current", 10000, "101")


# ---------------------------------------------------------- registration
def test_register_creates_account(svc, alice):
    assert alice["name"] == "Alice Sharma" and alice["nominee"] == "Ravi Sharma"
    assert len(alice["account_no"]) == 11 and alice["account_no"].startswith("102")
    assert alice["ifsc"] == "PYNB0000102" and alice["branch"] == "Kochi MG Road"
    assert alice["balance"] == 20000 and alice["pin_hash"] != PIN
    assert svc["txn"].history(alice["account_no"])[0]["type"] == "OPENING_DEPOSIT"


def test_salary_account_zero_balance(svc):
    c = svc["acc"].register("Sal Ary", ADULT, "9000000001", "s@x.com", "AAAAA1111A", PIN, PIN, "Salary", 0)
    assert c["balance"] == 0
    assert svc["txn"].history(c["account_no"]) == []


def test_duplicate_prevention(svc, alice):
    for phone, email, pan, word in [("9876543210", "o@x.com", "ZZZZZ9999Z", "phone"),
                                    ("9123456780", "ALICE@mail.com", "ZZZZZ9999Z", "email"),
                                    ("9123456780", "o@x.com", "abcde1234f", "PAN")]:
        with pytest.raises(ValidationError, match=word):
            svc["acc"].register("X Y", ADULT, phone, email, pan, PIN, PIN, "Savings", 5000)


@pytest.mark.parametrize("dob,phone,email,pan,pin,confirm,deposit,branch", [
    (ADULT, "12345", "a@b.com", "ABCDE1234F", PIN, PIN, 5000, "101"),
    (ADULT, "9123456780", "bad-email", "ABCDE1234F", PIN, PIN, 5000, "101"),
    (ADULT, "9123456780", "a@b.com", "ABC1234", PIN, PIN, 5000, "101"),
    ("2015-01-01", "9123456780", "a@b.com", "ABCDE1234F", PIN, PIN, 5000, "101"),   # minor
    (ADULT, "9123456780", "a@b.com", "ABCDE1234F", "1111", "1111", 5000, "101"),
    (ADULT, "9123456780", "a@b.com", "ABCDE1234F", PIN, "9999", 5000, "101"),
    (ADULT, "9123456780", "a@b.com", "ABCDE1234F", PIN, PIN, 500, "101"),           # below min
    (ADULT, "9123456780", "a@b.com", "ABCDE1234F", PIN, PIN, 5000, "999"),          # bad branch
])
def test_registration_validation(svc, dob, phone, email, pan, pin, confirm, deposit, branch):
    with pytest.raises(ValidationError):
        svc["acc"].register("Test User", dob, phone, email, pan, pin, confirm, "Savings", deposit, branch)


def test_validators():
    assert validate_phone("+91 98765-43210") == "9876543210"
    assert validate_pan(" abcde1234f ") == "ABCDE1234F"
    with pytest.raises(ValidationError):
        validate_dob("15-06-1995")
    h, s = hash_secret("4826")
    assert verify_secret("4826", h, s) and not verify_secret("4827", h, s)


# ----------------------------------------------------------------- auth
def test_login_lockout_and_unfreeze(svc, alice):
    no = alice["account_no"]
    assert svc["auth"].login(no, PIN)["account_no"] == no
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            svc["auth"].login(no, "0000")
    with pytest.raises(AccountFrozenError):
        svc["auth"].login(no, "0000")
    with pytest.raises(AccountFrozenError):
        svc["auth"].login(no, PIN)
    svc["admin"].unfreeze(no)
    svc["auth"].login(no, PIN)
    with pytest.raises(AccountNotFoundError):
        svc["auth"].login("10100000000", PIN)


def test_change_pin(svc, alice):
    no = alice["account_no"]
    with pytest.raises(ValidationError):
        svc["auth"].change_pin(no, PIN, "4826", "4827")
    svc["auth"].change_pin(no, PIN, "4826", "4826")
    svc["auth"].login(no, "4826")


# ---------------------------------------------------------- transactions
def test_deposit_cash_and_cheque(svc, alice):
    no = alice["account_no"]
    assert svc["txn"].deposit(no, 2500)["balance_after"] == 22500
    t = svc["txn"].deposit(no, 1000, "cheque", "123456")
    assert "Chq 123456" in t["description"]
    with pytest.raises(ValidationError):
        svc["txn"].deposit(no, 1000, "Cheque", "12")
    with pytest.raises(ValidationError):
        svc["txn"].deposit(no, -5)


def test_withdrawal(svc, alice):
    no = alice["account_no"]
    assert svc["txn"].withdraw(no, PIN, 1234.50)["balance_after"] == 18765.50   # any amount at the counter
    with pytest.raises(InsufficientFundsError):
        svc["txn"].withdraw(no, PIN, 18000)            # must keep ₹1,000 minimum
    with pytest.raises(AuthenticationError):
        svc["txn"].withdraw(no, "0000", 100)
    svc["txn"].deposit(no, 300000)
    with pytest.raises(LimitExceededError):
        svc["txn"].withdraw(no, PIN, 150000)           # per-transaction cap


def test_transfer_modes(svc, alice, bob):
    a, b = alice["account_no"], bob["account_no"]
    out, inc = svc["txn"].transfer(a, PIN, b, 3000, "rent", "NEFT")
    assert out["balance_after"] == 17000 and inc["balance_after"] == 13000
    assert out["description"].startswith("NEFT to Bob Roy")
    with pytest.raises(LimitExceededError):
        svc["txn"].transfer(a, PIN, b, 5000, mode="RTGS")          # RTGS minimum ₹2 lakh
    with pytest.raises(InsufficientFundsError):
        svc["txn"].transfer(a, PIN, b, 16500)
    with pytest.raises(ValidationError):
        svc["txn"].transfer(a, PIN, a, 10)
    with pytest.raises(AccountNotFoundError):
        svc["txn"].transfer(a, PIN, "10199999999", 10)
    svc["admin"].freeze(b)
    with pytest.raises(AccountFrozenError):
        svc["txn"].transfer(a, PIN, b, 10)
    assert svc["acc"].get(a)["balance"] == 17000


def test_balance_history_and_mini_statement(svc, alice, bob):
    a = alice["account_no"]
    for amt in (100, 200, 300, 400, 500, 600):
        svc["txn"].deposit(a, amt)
    svc["txn"].transfer(a, PIN, bob["account_no"], 1000)
    bal = svc["txn"].balance_inquiry(a, PIN)
    assert bal["balance"] == 21100 and bal["available"] == 20100
    ms = svc["txn"].mini_statement(a)
    assert len(ms["transactions"]) == 5 and ms["transactions"][0]["type"] == "TRANSFER_OUT"
    assert len(svc["txn"].history(a, "deposit")) == 6
    assert len(svc["txn"].history(a, "transfer")) == 1
    assert "TRANSACTION RECEIPT" in svc["txn"].receipt(ms["transactions"][0])


# ------------------------------------------------------- interest & FDs
def test_interest_formulas():
    assert simple_interest(10000, 7, 2) == (1400.0, 11400.0)
    assert AccountManager.interest_calculator(5000, 6, 0.5)["interest"] == 150
    assert emi(500000, 8.5, 60) == 10258.27
    assert emi(12000, 0, 12) == 1000


def test_fixed_deposit_and_senior_rate(svc, alice, bob):
    a = alice["account_no"]
    assert fd_rate_for(12) == 6.8 and fd_rate_for(12, senior=True) == 7.3
    start = date.today()
    fd = svc["fd"].create(a, PIN, 10000, 12, on=start)
    assert fd["rate"] == 6.8 and fd["maturity_amount"] == 10680
    assert svc["fd"].create(bob["account_no"], "7391", 5000, 12)["rate"] == 7.3   # senior citizen
    q = svc["fd"].closure_quote(a, fd["fd_id"], on=start + timedelta(days=73))
    assert q["premature"] and q["rate"] == 5.8 and q["interest"] == 116
    svc["fd"].close(a, PIN, fd["fd_id"], on=start + timedelta(days=400))
    assert svc["acc"].get(a)["balance"] == 20680
    with pytest.raises(BankError):
        svc["fd"].close(a, PIN, fd["fd_id"])
    with pytest.raises(ValidationError):
        svc["fd"].create(a, PIN, 1000, 12)           # below FD minimum


# --------------------------------------------------------------- loans
def test_loan_approval_workflow(svc, alice):
    a = alice["account_no"]
    q = LoanManager.quote("Personal", 100000, 12)
    assert q["emi"] == emi(100000, 10.75, 12) and q["total_payable"] == round(q["emi"] * 12, 2)
    loan = svc["loan"].apply(a, PIN, "personal", 100000, 12, "Wedding")
    assert loan["status"] == "PENDING" and svc["acc"].get(a)["balance"] == 20000   # not disbursed yet
    with pytest.raises(BankError):
        svc["loan"].repay(a, PIN, loan["loan_id"], 100)                            # pending can't be repaid
    assert [l["loan_id"] for l in svc["admin"].pending_loans()] == [loan["loan_id"]]
    svc["admin"].approve_loan(loan["loan_id"])
    assert svc["acc"].get(a)["balance"] == 120000
    with pytest.raises(BankError):
        svc["admin"].approve_loan(loan["loan_id"])                                 # already decided
    l = svc["loan"].repay(a, PIN, loan["loan_id"], q["emi"])
    assert LoanManager.emis_paid(l) == 1
    l = svc["loan"].repay(a, PIN, loan["loan_id"], l["outstanding"])
    assert l["status"] == "CLOSED" and l["outstanding"] == 0


def test_loan_reject_cancel_and_limits(svc, alice):
    a = alice["account_no"]
    l1 = svc["loan"].apply(a, PIN, "Gold", 50000, 12)
    svc["admin"].reject_loan(l1["loan_id"], "Insufficient collateral")
    assert svc["loan"].list(a, "REJECTED")[0]["remarks"] == "Insufficient collateral"
    svc["loan"].apply(a, PIN, "Home", 2000000, 240)
    l3 = svc["loan"].apply(a, PIN, "Vehicle", 300000, 60)
    with pytest.raises(LimitExceededError):
        svc["loan"].apply(a, PIN, "Education", 100000, 24)          # 2 open applications max
    svc["loan"].cancel(a, l3["loan_id"])
    svc["loan"].apply(a, PIN, "Education", 100000, 24)
    with pytest.raises(ValidationError):
        LoanManager.quote("Gold", 600000, 12)                       # above Gold maximum
    with pytest.raises(ValidationError):
        LoanManager.quote("Vehicle", 100000, 120)                   # tenure above 84 months


# --------------------------------------------------------------- admin
def test_savings_interest_posting(svc, alice, bob):
    r = svc["admin"].apply_savings_interest("2026-01")
    assert r["accounts"] == 1 and r["total"] == 50.0                 # 20000 * 3% / 12; Current skipped
    assert svc["acc"].get(alice["account_no"])["balance"] == 20050
    assert svc["admin"].apply_savings_interest("2026-01")["accounts"] == 0   # not credited twice
    assert svc["admin"].apply_savings_interest("2026-02")["accounts"] == 1


def test_admin_operations(svc, alice, bob):
    am, auth = svc["admin"], svc["auth"]
    auth.admin_login("admin", "admin123")
    with pytest.raises(AuthenticationError):
        auth.admin_login("admin", "wrong")
    assert len(am.view_customers()) == 2
    assert [c["name"] for c in am.search_customers("pqrst")] == ["Bob Roy"]            # by PAN
    am.freeze(alice["account_no"], "KYC review")
    with pytest.raises(AccountFrozenError):
        svc["txn"].deposit(alice["account_no"], 100)
    am.unfreeze(alice["account_no"])
    loan = svc["loan"].apply(bob["account_no"], "7391", "Personal", 10000, 6)
    with pytest.raises(BankError, match="pending loan"):
        am.delete_account(bob["account_no"])
    am.approve_loan(loan["loan_id"])
    svc["loan"].repay(bob["account_no"], "7391", loan["loan_id"], loan["total_payable"])
    assert len(am.all_transactions(txn_type="LOAN_CREDIT")) == 1
    r = am.delete_account(bob["account_no"])
    assert r["balance_to_refund"] == round(10000 + 10000 - loan["total_payable"], 2)
    assert len(am.view_customers()) == 1
    auth.change_admin_password("admin", "admin123", "newpass1")
    auth.admin_login("admin", "newpass1")


# -------------------------------------------------------- reports & backup
def test_reports(svc, alice, bob, tmp_path):
    svc["txn"].transfer(alice["account_no"], PIN, bob["account_no"], 1000)
    svc["fd"].create(alice["account_no"], PIN, 5000, 24)
    loan = svc["loan"].apply(alice["account_no"], PIN, "Education", 50000, 36)
    svc["admin"].approve_loan(loan["loan_id"])
    svc["loan"].apply(bob["account_no"], "7391", "Gold", 20000, 12)
    rg = ReportGenerator(svc["db"], tmp_path / "reports")
    pdf = rg.account_statement_pdf(alice["account_no"])
    assert pdf.read_bytes()[:4] == b"%PDF" and pdf.stat().st_size > 2000
    cust_csv = rg.export_customers_csv().read_text()
    assert "Alice Sharma" in cust_csv and "ABXXXXX34F" in cust_csv and "ABCDE1234F" not in cust_csv
    assert len(rg.export_transactions_csv(alice["account_no"]).read_text().splitlines()) == 1 + 4
    assert len(rg.export_loans_csv("PENDING").read_text().splitlines()) == 2
    s = rg.system_summary()
    assert s["total_customers"] == 2 and s["active_loans"] == 1 and s["pending_loan_applications"] == 1
    assert s["accounts_by_branch"] == {"Kochi MG Road": 1, "Thiruvananthapuram Main": 1}


def test_backup_restore(svc, alice, tmp_path):
    db = svc["db"]
    bm = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bm.create_backup()
    assert set(bm.verify(archive)) == {"customers.json", "transactions.json", "loans.json",
                                       "fixed_deposits.json", "admins.json"}
    svc["txn"].deposit(alice["account_no"], 5000)
    safety = bm.restore(archive)
    assert svc["acc"].get(alice["account_no"])["balance"] == 20000 and safety.exists()
    bad = tmp_path / "backups" / "bank_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bm.restore(bad)


def test_corrupted_database(db):
    (db.data_dir / "customers.json").write_text("{oops")
    with pytest.raises(DatabaseError):
        db.all("customers")


def test_data_persists_across_instances(svc, alice):
    again = AccountManager(JSONDatabase(svc["db"].data_dir))
    assert again.get(alice["account_no"])["balance"] == 20000
    raw = json.loads((svc["db"].data_dir / "customers.json").read_text())
    assert raw[0]["pan"] == "ABCDE1234F"
