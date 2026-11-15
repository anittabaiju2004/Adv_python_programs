"""account.py — customer registration (with KYC), account lookup, interest
calculator, fixed deposits and loan management."""
from __future__ import annotations

import secrets
from datetime import date, datetime

from auth import AuthManager
from database import JSONDatabase
from transaction import TransactionManager
from utils import (ACCOUNT_TYPES, BankError, AccountNotFoundError, BRANCHES, DATE_FMT, FD_MIN_AMOUNT,
                   FD_PREMATURE_PENALTY, FD_RATES, LOAN_MIN, LOAN_TENURE_MIN, LOAN_TYPES,
                   MAX_ACTIVE_LOANS, MIN_AGE, MIN_OPENING_DEPOSIT, SENIOR_CITIZEN_AGE,
                   SENIOR_CITIZEN_BONUS, LimitExceededError, ValidationError, add_months, age_on, emi,
                   hash_secret, money, new_id, now_str, simple_interest, today, validate_amount,
                   validate_choice, validate_dob, validate_email, validate_name, validate_pan,
                   validate_phone, validate_pin, validate_positive_int)



# =================================================================== accounts
class AccountManager:
    def __init__(self, db: JSONDatabase, auth: AuthManager | None = None):
        self.db = db
        self.auth = auth or AuthManager(db)
        self.txn = TransactionManager(db, self.auth)

    def _generate_account_no(self, branch_code: str) -> str:
        """11 digits: 3-digit branch code + 8 random digits."""
        existing = {c["account_no"] for c in self.db.all("customers")}
        while True:
            no = branch_code + "".join(secrets.choice("0123456789") for _ in range(8))
            if no not in existing:
                return no

    def register(self, name: str, dob: str, phone: str, email: str, pan: str, pin: str,
                 confirm_pin: str, account_type: str = "Savings", initial_deposit=None,
                 branch_code: str = "101", address: str = "", nominee: str = "") -> dict:
        name = validate_name(name)
        dob = validate_dob(dob, MIN_AGE)
        phone = validate_phone(phone)
        email = validate_email(email)
        pan = validate_pan(pan)
        account_type = validate_choice(account_type, ACCOUNT_TYPES, "account type")
        if branch_code not in BRANCHES:
            raise ValidationError(f"Unknown branch code. Choose from: {', '.join(BRANCHES)}")
        validate_pin(pin)
        if pin != confirm_pin:
            raise ValidationError("PIN and confirmation PIN do not match.")
        minimum = MIN_OPENING_DEPOSIT[account_type]
        deposit = 0.0 if initial_deposit in (None, "", 0, "0") else validate_amount(initial_deposit, "Opening deposit")
        if deposit < minimum:
            raise ValidationError(f"Minimum opening deposit for a {account_type} account is {money(minimum)}.")
        nominee = validate_name(nominee) if str(nominee or "").strip() else ""
        # Duplicate account prevention (one account per PAN / phone / email)
        for c in self.db.all("customers"):
            if c["pan"] == pan:
                raise ValidationError("An account with this PAN already exists.")
            if c["phone"] == phone:
                raise ValidationError("An account with this phone number already exists.")
            if c["email"] == email:
                raise ValidationError("An account with this email address already exists.")
        pin_hash, salt = hash_secret(pin)
        customer = {
            "account_no": self._generate_account_no(branch_code), "name": name, "dob": dob,
            "phone": phone, "email": email, "pan": pan, "address": str(address or "").strip()[:120],
            "nominee": nominee, "branch_code": branch_code, "branch": BRANCHES[branch_code][0],
            "ifsc": BRANCHES[branch_code][1], "account_type": account_type, "balance": 0.0,
            "pin_hash": pin_hash, "pin_salt": salt, "status": "ACTIVE", "failed_attempts": 0,
            "frozen_reason": None, "last_interest_month": None, "created_at": now_str(), "last_login": None,
        }
        self.db.insert("customers", customer)
        if deposit:
            self.txn.post(customer["account_no"], "OPENING_DEPOSIT", deposit, "Account opening deposit")
        return self.get(customer["account_no"])

    def get(self, account_no: str) -> dict:
        c = self.db.find_one("customers", account_no=str(account_no).strip())
        if not c:
            raise AccountNotFoundError(f"Account {account_no} not found.")
        return c

    def update_contact(self, account_no: str, phone: str | None = None, email: str | None = None,
                       address: str | None = None, nominee: str | None = None) -> dict:
        self.get(account_no)
        changes = {}
        others = [c for c in self.db.all("customers") if c["account_no"] != account_no]
        if phone:
            changes["phone"] = validate_phone(phone)
            if any(c["phone"] == changes["phone"] for c in others):
                raise ValidationError("Phone number already in use.")
        if email:
            changes["email"] = validate_email(email)
            if any(c["email"] == changes["email"] for c in others):
                raise ValidationError("Email already in use.")
        if address:
            changes["address"] = address.strip()[:120]
        if nominee:
            changes["nominee"] = validate_name(nominee)
        if not changes:
            raise ValidationError("Nothing to update.")
        return self.db.update("customers", "account_no", account_no, changes)

    @staticmethod
    def is_senior(customer: dict) -> bool:
        return age_on(customer["dob"]) >= SENIOR_CITIZEN_AGE

    @staticmethod
    def interest_calculator(principal, rate, years) -> dict:
        interest, maturity = simple_interest(principal, rate, years)
        return {"principal": round(float(principal), 2), "rate": float(rate), "years": float(years),
                "interest": interest, "maturity_amount": maturity}


# ============================================================ fixed deposits
def fd_rate_for(months: int, senior: bool = False) -> float:
    for lo, hi, rate in FD_RATES:
        if lo <= months <= hi:
            return round(rate + (SENIOR_CITIZEN_BONUS if senior else 0), 2)
    raise ValidationError(f"FD tenure must be between {FD_RATES[0][0]} and {FD_RATES[-1][1]} months.")


def _parse(d: str) -> date:
    return datetime.strptime(d, DATE_FMT).date()


class FixedDepositManager:
    def __init__(self, db: JSONDatabase, auth: AuthManager | None = None):
        self.db = db
        self.auth = auth or AuthManager(db)
        self.txn = TransactionManager(db, self.auth)

    def create(self, account_no: str, pin: str, amount, months, on: date | None = None) -> dict:
        cust = self.auth.verify_pin(account_no, pin)
        amount = validate_amount(amount)
        if amount < FD_MIN_AMOUNT:
            raise ValidationError(f"Minimum FD amount is {money(FD_MIN_AMOUNT)}.")
        months = validate_positive_int(months, "Tenure (months)", FD_RATES[0][0], FD_RATES[-1][1])
        senior = AccountManager.is_senior(cust)
        rate = fd_rate_for(months, senior)
        start = on or today()
        interest, maturity = simple_interest(amount, rate, months / 12)
        fd_id = new_id("FD")
        self.txn.post(account_no, "FD_OPEN", amount, f"Fixed deposit opened {fd_id}")
        fd = {"fd_id": fd_id, "account_no": account_no, "principal": amount, "rate": rate,
              "senior_citizen": senior, "months": months, "start_date": start.strftime(DATE_FMT),
              "maturity_date": add_months(start, months).strftime(DATE_FMT),
              "interest": interest, "maturity_amount": maturity, "status": "ACTIVE",
              "closed_on": None, "payout": None}
        self.db.insert("fixed_deposits", fd)
        return fd

    def list(self, account_no: str, active_only: bool = False) -> list[dict]:
        fds = self.db.find("fixed_deposits", account_no=account_no)
        if active_only:
            fds = [f for f in fds if f["status"] == "ACTIVE"]
        return sorted(fds, key=lambda f: f["start_date"], reverse=True)

    def _get(self, account_no: str, fd_id: str) -> dict:
        fd = self.db.find_one("fixed_deposits", fd_id=str(fd_id).strip().upper(), account_no=account_no)
        if not fd:
            raise BankError(f"Fixed deposit {fd_id} not found.")
        return fd

    def closure_quote(self, account_no: str, fd_id: str, on: date | None = None) -> dict:
        fd = self._get(account_no, fd_id)
        if fd["status"] != "ACTIVE":
            raise BankError("This FD is already closed.")
        on = on or today()
        if on >= _parse(fd["maturity_date"]):
            return {"premature": False, "payout": fd["maturity_amount"], "interest": fd["interest"], "rate": fd["rate"]}
        days = max(0, (on - _parse(fd["start_date"])).days)
        rate = max(0.0, round(fd["rate"] - FD_PREMATURE_PENALTY, 2))
        interest = round(fd["principal"] * rate * days / 36500, 2)
        return {"premature": True, "payout": round(fd["principal"] + interest, 2), "interest": interest,
                "rate": rate, "days": days}

    def close(self, account_no: str, pin: str, fd_id: str, on: date | None = None) -> dict:
        self.auth.verify_pin(account_no, pin)
        fd = self._get(account_no, fd_id)
        quote = self.closure_quote(account_no, fd_id, on)
        self.txn.post(account_no, "FD_CLOSURE", quote["payout"],
                      f"FD {'premature ' if quote['premature'] else ''}closure {fd['fd_id']}")
        self.db.update("fixed_deposits", "fd_id", fd["fd_id"],
                       {"status": "CLOSED", "closed_on": (on or today()).strftime(DATE_FMT),
                        "payout": quote["payout"]})
        return {**fd, **quote}


# ===================================================================== loans
class LoanManager:
    """Loan workflow:  customer applies -> PENDING -> admin approves (amount is
    disbursed, ACTIVE) or rejects (REJECTED) -> customer repays -> CLOSED."""

    def __init__(self, db: JSONDatabase, auth: AuthManager | None = None):
        self.db = db
        self.auth = auth or AuthManager(db)
        self.txn = TransactionManager(db, self.auth)

    @staticmethod
    def quote(loan_type: str, amount, months) -> dict:
        loan_type = validate_choice(loan_type, LOAN_TYPES, "loan type")
        rate, max_amount, max_months = LOAN_TYPES[loan_type]
        amount = validate_amount(amount, "Loan amount")
        if not LOAN_MIN <= amount <= max_amount:
            raise ValidationError(f"{loan_type} loan amount must be between {money(LOAN_MIN)} and {money(max_amount)}.")
        months = validate_positive_int(months, "Tenure (months)", LOAN_TENURE_MIN, max_months)
        monthly = emi(amount, rate, months)
        total = round(monthly * months, 2)
        return {"loan_type": loan_type, "principal": amount, "rate": rate, "months": months,
                "emi": monthly, "total_payable": total, "interest": round(total - amount, 2)}

    def apply(self, account_no: str, pin: str, loan_type: str, amount, months, purpose: str = "") -> dict:
        self.auth.verify_pin(account_no, pin)
        q = self.quote(loan_type, amount, months)
        open_loans = [l for l in self.list(account_no) if l["status"] in ("PENDING", "ACTIVE")]
        if len(open_loans) >= MAX_ACTIVE_LOANS:
            raise LimitExceededError(f"You already have {MAX_ACTIVE_LOANS} active or pending loans.")
        loan = {"loan_id": new_id("LN"), "account_no": account_no, **q, "purpose": str(purpose or "").strip()[:80],
                "amount_paid": 0.0, "outstanding": q["total_payable"], "status": "PENDING",
                "applied_on": today().strftime(DATE_FMT), "decided_on": None, "decided_by": None,
                "remarks": None, "closed_on": None}
        self.db.insert("loans", loan)
        return loan

    def list(self, account_no: str | None = None, status: str | None = None) -> list[dict]:
        loans = self.db.find("loans", **({"account_no": account_no} if account_no else {}))
        if status:
            loans = [l for l in loans if l["status"] == status.upper()]
        return sorted(loans, key=lambda l: l["applied_on"], reverse=True)

    def _get(self, loan_id: str, account_no: str | None = None) -> dict:
        match = {"loan_id": str(loan_id).strip().upper()}
        if account_no:
            match["account_no"] = account_no
        loan = self.db.find_one("loans", **match)
        if not loan:
            raise BankError(f"Loan {loan_id} not found.")
        return loan

    def cancel(self, account_no: str, loan_id: str) -> dict:
        loan = self._get(loan_id, account_no)
        if loan["status"] != "PENDING":
            raise BankError("Only pending applications can be cancelled.")
        return self.db.update("loans", "loan_id", loan["loan_id"], {"status": "CANCELLED", "decided_on": today().strftime(DATE_FMT)})

    # ---- admin decisions (called from admin.py)
    def approve(self, loan_id: str, admin: str) -> dict:
        loan = self._get(loan_id)
        if loan["status"] != "PENDING":
            raise BankError(f"Loan is {loan['status']}, not pending.")
        self.txn.post(loan["account_no"], "LOAN_CREDIT", loan["principal"],
                      f"{loan['loan_type']} loan disbursed {loan['loan_id']}")
        return self.db.update("loans", "loan_id", loan["loan_id"],
                              {"status": "ACTIVE", "decided_on": today().strftime(DATE_FMT), "decided_by": admin})

    def reject(self, loan_id: str, admin: str, reason: str) -> dict:
        loan = self._get(loan_id)
        if loan["status"] != "PENDING":
            raise BankError(f"Loan is {loan['status']}, not pending.")
        return self.db.update("loans", "loan_id", loan["loan_id"],
                              {"status": "REJECTED", "decided_on": today().strftime(DATE_FMT), "decided_by": admin,
                               "remarks": str(reason or "Not eligible").strip()[:100]})

    def repay(self, account_no: str, pin: str, loan_id: str, amount) -> dict:
        self.auth.verify_pin(account_no, pin)
        loan = self._get(loan_id, account_no)
        if loan["status"] != "ACTIVE":
            raise BankError(f"This loan is {loan['status'].lower()}; repayment not possible.")
        amount = validate_amount(amount)
        if amount > loan["outstanding"]:
            raise ValidationError(f"Amount exceeds outstanding balance {money(loan['outstanding'])}.")
        self.txn.post(account_no, "LOAN_REPAYMENT", amount, f"Loan repayment {loan['loan_id']}")
        paid = round(loan["amount_paid"] + amount, 2)
        outstanding = round(loan["total_payable"] - paid, 2)
        changes = {"amount_paid": paid, "outstanding": outstanding}
        if outstanding <= 0:
            changes.update(status="CLOSED", outstanding=0.0, closed_on=today().strftime(DATE_FMT))
        return self.db.update("loans", "loan_id", loan["loan_id"], changes)

    def close_completed(self, account_no: str) -> list[dict]:
        closed = []
        for loan in self.list(account_no, "ACTIVE"):
            if loan["outstanding"] <= 0:
                closed.append(self.db.update("loans", "loan_id", loan["loan_id"],
                                             {"status": "CLOSED", "closed_on": today().strftime(DATE_FMT)}))
        return closed

    @staticmethod
    def emis_paid(loan: dict) -> int:
        return int(loan["amount_paid"] // loan["emi"]) if loan["emi"] else 0
