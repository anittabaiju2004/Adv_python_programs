"""admin.py — administrator operations: view, search, freeze, unfreeze and
delete customer accounts, approve/reject loans, post savings interest."""
from __future__ import annotations

from account import LoanManager
from database import JSONDatabase
from transaction import TransactionManager
from utils import (BankError, AccountNotFoundError, SAVINGS_INTEREST_RATE, ValidationError, now_str,
                   today, validate_month_str)


class AdminManager:
    def __init__(self, db: JSONDatabase, admin_username: str):
        self.db = db
        self.admin = admin_username

    def view_customers(self, status: str | None = None) -> list[dict]:
        customers = self.db.all("customers")
        if status:
            customers = [c for c in customers if c["status"] == status.upper()]
        return sorted(customers, key=lambda c: c["created_at"])

    def search_customers(self, query: str) -> list[dict]:
        """Match by name, account number, phone, email or PAN (substring)."""
        q = str(query or "").strip().lower()
        if len(q) < 2:
            raise ValidationError("Enter at least 2 characters to search.")
        return [c for c in self.view_customers()
                if q in c["name"].lower() or q in c["account_no"] or q in c["phone"] or q in c["email"]
                or q in c.get("pan", "").lower()]

    def get(self, account_no: str) -> dict:
        c = self.db.find_one("customers", account_no=str(account_no).strip())
        if not c:
            raise AccountNotFoundError(f"Account {account_no} not found.")
        return c

    def freeze(self, account_no: str, reason: str = "Frozen by administrator") -> dict:
        c = self.get(account_no)
        if c["status"] == "FROZEN":
            raise BankError("Account is already frozen.")
        return self.db.update("customers", "account_no", c["account_no"],
                              {"status": "FROZEN", "frozen_reason": reason.strip() or "Frozen by administrator",
                               "frozen_by": self.admin, "frozen_at": now_str()})

    def unfreeze(self, account_no: str) -> dict:
        c = self.get(account_no)
        if c["status"] == "ACTIVE":
            raise BankError("Account is already active.")
        return self.db.update("customers", "account_no", c["account_no"],
                              {"status": "ACTIVE", "frozen_reason": None, "failed_attempts": 0,
                               "unfrozen_by": self.admin, "unfrozen_at": now_str()})

    def delete_check(self, account_no: str) -> list[str]:
        """Reasons the account cannot be deleted yet (empty list = OK)."""
        c = self.get(account_no)
        problems = []
        if any(l["status"] in ("ACTIVE", "PENDING") for l in self.db.find("loans", account_no=c["account_no"])):
            problems.append("customer has an active or pending loan")
        if any(f["status"] == "ACTIVE" for f in self.db.find("fixed_deposits", account_no=c["account_no"])):
            problems.append("customer has an active fixed deposit")
        return problems

    def delete_account(self, account_no: str) -> dict:
        """Delete a customer and their records. Refused while loans or FDs are
        active. Returns the deleted customer plus removed record counts; the
        remaining balance is reported so it can be paid out."""
        problems = self.delete_check(account_no)
        if problems:
            raise BankError("Cannot delete: " + "; ".join(problems) + ".")
        c = self.get(account_no)
        removed = {coll: self.db.delete_where(coll, account_no=c["account_no"])
                   for coll in ("transactions", "loans", "fixed_deposits")}
        self.db.delete_where("customers", account_no=c["account_no"])
        return {"customer": c, "removed": removed, "balance_to_refund": c["balance"]}

    # ------------------------------------------------------------- loans
    def pending_loans(self) -> list[dict]:
        loans = LoanManager(self.db).list(status="PENDING")
        names = {c["account_no"]: c for c in self.db.all("customers")}
        return [{**l, "customer": names.get(l["account_no"], {}).get("name", "?"),
                 "customer_balance": names.get(l["account_no"], {}).get("balance", 0.0)} for l in loans]

    def approve_loan(self, loan_id: str) -> dict:
        return LoanManager(self.db).approve(loan_id, self.admin)

    def reject_loan(self, loan_id: str, reason: str) -> dict:
        return LoanManager(self.db).reject(loan_id, self.admin, reason)

    # ---------------------------------------------------- savings interest
    def apply_savings_interest(self, month: str | None = None) -> dict:
        """Credit one month of interest to every active Savings account.

        Interest = balance x rate / 12 / 100. Each account is credited at most
        once per month (tracked in `last_interest_month`), so running this
        twice for the same month is harmless.
        """
        month = validate_month_str(month or today().strftime("%Y-%m"))
        txn = TransactionManager(self.db)
        credited, total = [], 0.0
        for c in self.db.all("customers"):
            if c["account_type"] != "Savings" or c["status"] != "ACTIVE":
                continue
            if (c.get("last_interest_month") or "") >= month:
                continue
            interest = round(c["balance"] * SAVINGS_INTEREST_RATE / 12 / 100, 2)
            if interest >= 0.01:
                txn.post(c["account_no"], "INTEREST_CREDIT", interest,
                         f"Savings interest {month} @ {SAVINGS_INTEREST_RATE}% p.a.")
                credited.append((c["account_no"], interest))
                total += interest
            self.db.update("customers", "account_no", c["account_no"], {"last_interest_month": month})
        return {"month": month, "accounts": len(credited), "total": round(total, 2), "details": credited}

    # ------------------------------------------------- transaction monitor
    def all_transactions(self, txn_type: str | None = None, min_amount: float | None = None,
                         date: str | None = None, limit: int = 50) -> list[dict]:
        txns = self.db.all("transactions")
        if txn_type:
            txns = [t for t in txns if t["type"] == txn_type.upper()]
        if min_amount is not None:
            txns = [t for t in txns if t["amount"] >= min_amount]
        if date:
            txns = [t for t in txns if t["timestamp"].startswith(date)]
        return sorted(txns, key=lambda t: t["timestamp"])[::-1][:limit]
