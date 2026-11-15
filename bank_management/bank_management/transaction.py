"""transaction.py — deposit, withdrawal, fund transfer (IMPS/NEFT/RTGS),
balance inquiry, transaction history, mini statement and receipts."""
from __future__ import annotations

from auth import AuthManager
from database import JSONDatabase
from utils import (AccountFrozenError, AccountNotFoundError, BANK_NAME, DAILY_TRANSFER_LIMIT,
                   DAILY_WITHDRAWAL_LIMIT, InsufficientFundsError, LimitExceededError,
                   MAX_DEPOSIT_PER_TXN, MAX_WITHDRAWAL_PER_TXN, MIN_BALANCE, MINI_STATEMENT_COUNT,
                   TRANSFER_MODES, ValidationError, mask_account, money, new_id, now_str, today,
                   validate_amount, validate_choice)

CREDIT_TYPES = {"DEPOSIT", "TRANSFER_IN", "FD_CLOSURE", "LOAN_CREDIT", "OPENING_DEPOSIT", "INTEREST_CREDIT"}
DEBIT_TYPES = {"WITHDRAWAL", "TRANSFER_OUT", "FD_OPEN", "LOAN_REPAYMENT"}
TYPE_LABELS = {"DEPOSIT": "Deposit", "WITHDRAWAL": "Withdrawal", "TRANSFER_IN": "Transfer In",
               "TRANSFER_OUT": "Transfer Out", "FD_OPEN": "FD Opened", "FD_CLOSURE": "FD Closed",
               "LOAN_CREDIT": "Loan Disbursal", "LOAN_REPAYMENT": "Loan Repayment",
               "OPENING_DEPOSIT": "Opening Deposit", "INTEREST_CREDIT": "Interest Credit"}


class TransactionManager:
    def __init__(self, db: JSONDatabase, auth: AuthManager | None = None):
        self.db = db
        self.auth = auth or AuthManager(db)

    # ============================================================ internals
    @staticmethod
    def available_balance(customer: dict) -> float:
        """Balance that can be spent while keeping the minimum balance."""
        return round(customer["balance"] - MIN_BALANCE[customer["account_type"]], 2)

    def _make_txn(self, cust: dict, txn_type: str, amount: float, description: str,
                  counterparty: str | None = None) -> dict:
        return {"txn_id": new_id("TXN"), "account_no": cust["account_no"], "type": txn_type,
                "amount": amount, "balance_after": cust["balance"], "counterparty": counterparty,
                "description": description, "timestamp": now_str()}

    def post(self, account_no: str, txn_type: str, amount: float, description: str,
             counterparty: str | None = None, enforce_min_balance: bool = True) -> dict:
        """Credit or debit one account and record the transaction.

        This is the single place where balances change (used by deposits,
        withdrawals, FDs and loans), so every movement is logged.
        """
        amount = validate_amount(amount)
        is_credit = txn_type in CREDIT_TYPES
        if not is_credit and txn_type not in DEBIT_TYPES:
            raise ValidationError(f"Unknown transaction type {txn_type}.")
        with self.db.editing("customers") as customers:
            cust = next((c for c in customers if c["account_no"] == account_no), None)
            if cust is None:
                raise AccountNotFoundError("Account not found.")
            if cust["status"] != "ACTIVE":
                raise AccountFrozenError("Account is frozen. Please contact the bank administrator.")
            if not is_credit:
                limit = self.available_balance(cust) if enforce_min_balance else cust["balance"]
                if amount > limit:
                    raise InsufficientFundsError(
                        f"Insufficient funds. Available: {money(max(0, limit))} "
                        f"(minimum balance {money(MIN_BALANCE[cust['account_type']])} must be kept).")
            cust["balance"] = round(cust["balance"] + (amount if is_credit else -amount), 2)
            txn = self._make_txn(cust, txn_type, amount, description, counterparty)
        self.db.insert("transactions", txn)
        return txn

    def _today_total(self, account_no: str, txn_type: str) -> float:
        prefix = today().isoformat()
        return round(sum(t["amount"] for t in self.db.find("transactions", account_no=account_no, type=txn_type)
                         if t["timestamp"].startswith(prefix)), 2)

    # ============================================================ operations
    DEPOSIT_MODES = ["Cash", "Cheque"]

    def deposit(self, account_no: str, amount, mode: str = "Cash", reference: str = "") -> dict:
        amount = validate_amount(amount)
        mode = validate_choice(mode, self.DEPOSIT_MODES, "deposit mode")
        if amount > MAX_DEPOSIT_PER_TXN:
            raise LimitExceededError(f"Maximum deposit per transaction is {money(MAX_DEPOSIT_PER_TXN)}.")
        reference = str(reference or "").strip()[:20]
        if mode == "Cheque" and not (reference.isdigit() and len(reference) == 6):
            raise ValidationError("Cheque number must be 6 digits.")
        desc = f"{mode} deposit" + (f" (Chq {reference})" if mode == "Cheque" else "")
        return self.post(account_no, "DEPOSIT", amount, desc)

    def withdraw(self, account_no: str, pin: str, amount) -> dict:
        self.auth.verify_pin(account_no, pin)
        amount = validate_amount(amount)
        if amount > MAX_WITHDRAWAL_PER_TXN:
            raise LimitExceededError(f"Maximum withdrawal per transaction is {money(MAX_WITHDRAWAL_PER_TXN)}.")
        used = self._today_total(account_no, "WITHDRAWAL")
        if used + amount > DAILY_WITHDRAWAL_LIMIT:
            raise LimitExceededError(f"Daily withdrawal limit {money(DAILY_WITHDRAWAL_LIMIT)} reached. "
                                     f"Remaining today: {money(DAILY_WITHDRAWAL_LIMIT - used)}.")
        return self.post(account_no, "WITHDRAWAL", amount, "Cash withdrawal")

    def transfer(self, sender: str, pin: str, receiver: str, amount, remarks: str = "",
                 mode: str = "IMPS") -> tuple[dict, dict]:
        """Move money between two accounts in one atomic save."""
        self.auth.verify_pin(sender, pin)
        amount = validate_amount(amount)
        mode = validate_choice(mode, TRANSFER_MODES, "transfer mode")
        lo, hi = TRANSFER_MODES[mode]
        if not lo <= amount <= hi:
            raise LimitExceededError(f"{mode} transfers must be between {money(lo)} and {money(hi)}.")
        receiver = str(receiver).strip()
        if receiver == sender:
            raise ValidationError("Cannot transfer to the same account.")
        used = self._today_total(sender, "TRANSFER_OUT")
        if used + amount > DAILY_TRANSFER_LIMIT:
            raise LimitExceededError(f"Daily transfer limit {money(DAILY_TRANSFER_LIMIT)} reached. "
                                     f"Remaining today: {money(DAILY_TRANSFER_LIMIT - used)}.")
        remarks = str(remarks or "").strip()[:60]
        with self.db.editing("customers") as customers:
            by_no = {c["account_no"]: c for c in customers}
            src, dst = by_no.get(sender), by_no.get(receiver)
            if dst is None:
                raise AccountNotFoundError(f"Receiver account {receiver} does not exist.")
            if dst["status"] != "ACTIVE":
                raise AccountFrozenError("Receiver account is frozen; transfer not allowed.")
            if amount > self.available_balance(src):
                raise InsufficientFundsError(f"Insufficient funds. Available: "
                                             f"{money(max(0, self.available_balance(src)))}.")
            src["balance"] = round(src["balance"] - amount, 2)
            dst["balance"] = round(dst["balance"] + amount, 2)
            out = self._make_txn(src, "TRANSFER_OUT", amount,
                                 f"{mode} to {dst['name']}" + (f" - {remarks}" if remarks else ""), receiver)
            inc = self._make_txn(dst, "TRANSFER_IN", amount,
                                 f"{mode} from {src['name']}" + (f" - {remarks}" if remarks else ""), sender)
        self.db.insert("transactions", out)
        self.db.insert("transactions", inc)
        return out, inc

    def balance_inquiry(self, account_no: str, pin: str) -> dict:
        c = self.auth.verify_pin(account_no, pin)
        return {"account_no": c["account_no"], "name": c["name"], "account_type": c["account_type"],
                "balance": c["balance"], "available": max(0.0, self.available_balance(c)),
                "withdrawn_today": self._today_total(account_no, "WITHDRAWAL"),
                "checked_at": now_str()}

    # ============================================================== history
    def history(self, account_no: str, txn_type: str | None = None,
                start: str | None = None, end: str | None = None) -> list[dict]:
        txns = self.db.find("transactions", account_no=account_no)
        if txn_type:
            wanted = {"TRANSFER": {"TRANSFER_IN", "TRANSFER_OUT"}}.get(txn_type.upper(), {txn_type.upper()})
            txns = [t for t in txns if t["type"] in wanted]
        if start:
            txns = [t for t in txns if t["timestamp"][:10] >= start]
        if end:
            txns = [t for t in txns if t["timestamp"][:10] <= end]
        # The file is append-only, so file order is chronological; a stable sort on
        # timestamp keeps that order for transactions within the same second.
        return sorted(txns, key=lambda t: t["timestamp"])[::-1]

    def mini_statement(self, account_no: str, count: int = MINI_STATEMENT_COUNT) -> dict:
        txns = self.history(account_no)[:count]
        cust = self.db.find_one("customers", account_no=account_no)
        return {"account_no": account_no, "name": cust["name"] if cust else "", "transactions": txns,
                "balance": cust["balance"] if cust else 0.0,
                "credits": round(sum(t["amount"] for t in txns if t["type"] in CREDIT_TYPES), 2),
                "debits": round(sum(t["amount"] for t in txns if t["type"] in DEBIT_TYPES), 2)}

    @staticmethod
    def receipt(txn: dict) -> str:
        sign = "+" if txn["type"] in CREDIT_TYPES else "-"
        lines = [
            "-" * 40, f"{BANK_NAME:^40}", f"{'TRANSACTION RECEIPT':^40}", "-" * 40,
            f"Date/Time : {txn['timestamp']}",
            f"Txn ID    : {txn['txn_id']}",
            f"Account   : {mask_account(txn['account_no'])}",
            f"Type      : {TYPE_LABELS.get(txn['type'], txn['type'])}",
            f"Amount    : {sign}{money(txn['amount'])}",
        ]
        if txn.get("counterparty"):
            lines.append(f"{'To' if txn['type'] == 'TRANSFER_OUT' else 'From':<10}: {mask_account(txn['counterparty'])}")
        lines += [f"Balance   : {money(txn['balance_after'])}", "-" * 40,
                  f"{'Thank you for banking with us':^40}", "-" * 40]
        return "\n".join(lines)
