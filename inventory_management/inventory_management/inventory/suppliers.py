"""Supplier Management: supplier records, purchase history and amounts payable."""
from __future__ import annotations

from .parties import PartyManager


class SupplierManager(PartyManager):
    collection = "suppliers"
    id_field = "supplier_id"
    prefix = "SUP"
    label = "Supplier"

    def _transactions(self, supplier_id: str) -> list[dict]:
        return self.db.find("purchases", supplier_id=supplier_id)

    def statement(self, supplier_id: str) -> dict:
        s = self.get(supplier_id)
        pos = sorted(self._transactions(s["supplier_id"]), key=lambda p: p["date"], reverse=True)
        received = [p for p in pos if p["status"] == "RECEIVED"]
        billed = round(sum(p["grand_total"] for p in received), 2)
        paid = round(sum(p["amount_paid"] for p in received), 2)
        return {"supplier": s, "purchases": pos, "billed": billed, "paid": paid, "payable": round(billed - paid, 2),
                "open_orders": [p for p in pos if p["status"] == "ORDERED"]}

    def payables(self) -> list[dict]:
        out = []
        for s in self.list(include_inactive=True):
            st = self.statement(s["supplier_id"])
            if st["payable"] > 0.005:
                out.append({"supplier": s, "payable": st["payable"]})
        return sorted(out, key=lambda x: -x["payable"])
