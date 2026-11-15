"""Bill Reminder: track due dates, upcoming / overdue bills and recurring bills."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from .config import BILL_REMINDER_DAYS, DATE_FORMAT
from .database import JSONDatabase
from .exceptions import NotFoundError
from .models import Bill
from .transactions import ExpenseManager
from .validators import validate_amount, validate_choice, validate_date, validate_text

RECURRENCE = ["none", "monthly", "yearly"]


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year, month = d.year + m // 12, m % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class BillManager:
    def __init__(self, db: JSONDatabase, username: str):
        self.db = db
        self.username = username

    def _raw(self, bill_id: str) -> dict:
        rec = self.db.find_one("bills", id=bill_id, username=self.username)
        if not rec:
            raise NotFoundError(f"No bill with id '{bill_id}'.")
        return rec

    def add_bill(self, name: str, amount, due_date: str, recurring: str = "none") -> Bill:
        bill = Bill(self.username,
                    validate_text(name, "Bill name", 1, 60),
                    validate_amount(amount),
                    validate_date(due_date),
                    validate_choice(recurring, RECURRENCE, "recurrence"))
        self.db.insert("bills", bill.to_dict())
        return bill

    def list_bills(self, include_paid: bool = True) -> list[Bill]:
        bills = [Bill.from_dict(r) for r in self.db.find("bills", username=self.username)]
        if not include_paid:
            bills = [b for b in bills if not b.paid]
        return sorted(bills, key=lambda b: b.due_date)

    def upcoming(self, days: int = BILL_REMINDER_DAYS, today: date | None = None) -> list[Bill]:
        today = today or date.today()
        horizon = (today + timedelta(days=days)).strftime(DATE_FORMAT)
        t = today.strftime(DATE_FORMAT)
        return [b for b in self.list_bills(False) if t <= b.due_date <= horizon]

    def overdue(self, today: date | None = None) -> list[Bill]:
        t = (today or date.today()).strftime(DATE_FORMAT)
        return [b for b in self.list_bills(False) if b.due_date < t]

    def mark_paid(self, bill_id: str, record_expense: bool = True) -> Bill | None:
        """Mark a bill paid. Optionally log it as an expense.

        For recurring bills a new unpaid bill for the next period is created
        and returned.
        """
        bill = Bill.from_dict(self._raw(bill_id))
        self.db.update("bills", "id", bill_id, {"paid": True})
        if record_expense:
            ExpenseManager(self.db, self.username).add(
                bill.amount, "Bills", None, f"Bill paid: {bill.name}", "Other")
        if bill.recurring != "none":
            due = datetime.strptime(bill.due_date, DATE_FORMAT).date()
            nxt = _add_months(due, 1 if bill.recurring == "monthly" else 12)
            return self.add_bill(bill.name, bill.amount, nxt.strftime(DATE_FORMAT), bill.recurring)
        return None

    def delete_bill(self, bill_id: str) -> None:
        self._raw(bill_id)
        self.db.delete("bills", "id", bill_id)

    def reminders(self, today: date | None = None) -> list[str]:
        msgs = [f"[!] OVERDUE: {b.name} ({b.amount:.2f}) was due {b.due_date}" for b in self.overdue(today)]
        msgs += [f"[*] Upcoming: {b.name} ({b.amount:.2f}) due {b.due_date}" for b in self.upcoming(today=today)]
        return msgs
