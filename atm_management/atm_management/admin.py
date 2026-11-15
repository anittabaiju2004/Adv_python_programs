"""admin.py — administrator operations: view, search, freeze, unfreeze and
delete customer accounts."""
from __future__ import annotations

from database import JSONDatabase
from utils import ATMError, AccountNotFoundError, ValidationError, now_str


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
        """Match account number, phone or email exactly-ish; name by substring."""
        q = str(query or "").strip().lower()
        if len(q) < 2:
            raise ValidationError("Enter at least 2 characters to search.")
        return [c for c in self.view_customers()
                if q in c["name"].lower() or q in c["account_no"] or q in c["phone"] or q in c["email"]]

    def get(self, account_no: str) -> dict:
        c = self.db.find_one("customers", account_no=str(account_no).strip())
        if not c:
            raise AccountNotFoundError(f"Account {account_no} not found.")
        return c

    def freeze(self, account_no: str, reason: str = "Frozen by administrator") -> dict:
        c = self.get(account_no)
        if c["status"] == "FROZEN":
            raise ATMError("Account is already frozen.")
        return self.db.update("customers", "account_no", c["account_no"],
                              {"status": "FROZEN", "frozen_reason": reason.strip() or "Frozen by administrator",
                               "frozen_by": self.admin, "frozen_at": now_str()})

    def unfreeze(self, account_no: str) -> dict:
        c = self.get(account_no)
        if c["status"] == "ACTIVE":
            raise ATMError("Account is already active.")
        return self.db.update("customers", "account_no", c["account_no"],
                              {"status": "ACTIVE", "frozen_reason": None, "failed_attempts": 0,
                               "unfrozen_by": self.admin, "unfrozen_at": now_str()})

    def delete_check(self, account_no: str) -> list[str]:
        """Reasons the account cannot be deleted yet (empty list = OK)."""
        c = self.get(account_no)
        problems = []
        if any(l["status"] == "ACTIVE" for l in self.db.find("loans", account_no=c["account_no"])):
            problems.append("customer has an active loan")
        if any(f["status"] == "ACTIVE" for f in self.db.find("fixed_deposits", account_no=c["account_no"])):
            problems.append("customer has an active fixed deposit")
        return problems

    def delete_account(self, account_no: str) -> dict:
        """Delete a customer and their records. Refused while loans or FDs are
        active. Returns the deleted customer plus removed record counts; the
        remaining balance is reported so it can be paid out."""
        problems = self.delete_check(account_no)
        if problems:
            raise ATMError("Cannot delete: " + "; ".join(problems) + ".")
        c = self.get(account_no)
        removed = {coll: self.db.delete_where(coll, account_no=c["account_no"])
                   for coll in ("transactions", "loans", "fixed_deposits")}
        self.db.delete_where("customers", account_no=c["account_no"])
        return {"customer": c, "removed": removed, "balance_to_refund": c["balance"]}
