"""Customer Management: customer records (walk-in and registered B2B),
purchase history and amounts receivable for credit sales."""
from __future__ import annotations

from .database import JSONDatabase
from .parties import PartyManager
from .utils import BUSINESS_STATE, WALK_IN_CUSTOMER, InventoryError, now_str


class CustomerManager(PartyManager):
    collection = "customers"
    id_field = "customer_id"
    prefix = "CUST"
    label = "Customer"
    phone_required = False

    def __init__(self, db: JSONDatabase, actor: str = "system"):
        super().__init__(db, actor)
        if not self.db.find_one("customers", customer_id=WALK_IN_CUSTOMER):
            self.db.insert("customers", {"customer_id": WALK_IN_CUSTOMER, "name": "Walk-in Customer", "phone": "",
                                         "email": "", "address": "", "gstin": "", "state": BUSINESS_STATE,
                                         "contact_person": "", "active": True, "created_at": now_str()})

    def _transactions(self, customer_id: str) -> list[dict]:
        return self.db.find("sales", customer_id=customer_id)

    def delete(self, customer_id: str) -> None:
        if str(customer_id).upper() == WALK_IN_CUSTOMER:
            raise InventoryError("The walk-in customer record cannot be deleted.")
        super().delete(customer_id)

    def update(self, customer_id: str, **changes) -> dict:
        if str(customer_id).upper() == WALK_IN_CUSTOMER:
            raise InventoryError("The walk-in customer record cannot be edited.")
        return super().update(customer_id, **changes)

    def history(self, customer_id: str) -> dict:
        c = self.get(customer_id)
        sales = sorted((s for s in self._transactions(c["customer_id"]) if s["status"] != "CANCELLED"),
                       key=lambda s: s["date"], reverse=True)
        billed = round(sum(s["grand_total"] for s in sales), 2)
        paid = round(sum(s["amount_paid"] for s in sales), 2)
        return {"customer": c, "sales": sales, "invoices": len(sales), "billed": billed, "paid": paid,
                "receivable": round(billed - paid, 2),
                "last_purchase": sales[0]["date"] if sales else None}

    def receivables(self) -> list[dict]:
        out = []
        for c in self.list(include_inactive=True):
            h = self.history(c["customer_id"])
            if h["receivable"] > 0.005:
                unpaid = [s for s in h["sales"] if s["grand_total"] - s["amount_paid"] > 0.005]
                out.append({"customer": c, "receivable": h["receivable"],
                            "oldest_due": min(s["date"] for s in unpaid)})
        return sorted(out, key=lambda x: -x["receivable"])
