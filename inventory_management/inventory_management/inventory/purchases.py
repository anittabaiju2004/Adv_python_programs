"""Purchase Management: purchase orders, goods receipt (automatic stock-in
and weighted-average cost update), supplier payments and cancellation."""
from __future__ import annotations

from datetime import date

from .auth import log_activity
from .database import JSONDatabase
from .products import ProductManager
from .sales import compute_lines, payment_status
from .suppliers import SupplierManager
from .utils import (MAX_LINE_DISCOUNT, PAYMENT_MODES, InventoryError, NotFoundError, ValidationError,
                    is_inter_state, now_str, parse_date, validate_amount, validate_choice, validate_qty,
                    validate_text)


class PurchaseManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.products = ProductManager(db, actor)
        self.suppliers = SupplierManager(db, actor)

    def _next_id(self) -> str:
        return f"PO{len(self.db.all('purchases')) + 1:05d}"

    def build_lines(self, items: list[dict]) -> list[dict]:
        """items: [{product_id, qty, cost (optional, excl. GST), discount_pct (optional)}]"""
        if not items:
            raise ValidationError("Add at least one item.")
        lines, seen = [], set()
        for it in items:
            p = self.products.get(it["product_id"])
            if p["product_id"] in seen:
                raise ValidationError(f"{p['name']} is listed twice; combine the quantities.")
            seen.add(p["product_id"])
            disc = float(it.get("discount_pct") or 0)
            if not 0 <= disc <= MAX_LINE_DISCOUNT:
                raise ValidationError(f"Discount must be between 0 and {MAX_LINE_DISCOUNT:g} %.")
            lines.append({"product_id": p["product_id"], "name": p["name"], "hsn": p["hsn"], "unit": p["unit"],
                          "qty": validate_qty(it["qty"], p["unit"]),
                          "rate": validate_amount(it.get("cost") or p["purchase_price"], "Cost"),
                          "discount_pct": disc, "gst_rate": p["gst_rate"]})
        return lines

    def create(self, supplier_id: str, items: list[dict], supplier_invoice: str = "", on=None,
               receive_now: bool = True, notes: str = "") -> dict:
        s = self.suppliers.get(supplier_id)
        if not s["active"]:
            raise InventoryError(f"Supplier {s['name']} is inactive.")
        on = parse_date(on or date.today())
        if on > date.today():
            raise ValidationError("Purchase date cannot be in the future.")
        doc = compute_lines(self.build_lines(items), is_inter_state(s["state"]))
        po = {"purchase_id": self._next_id(), "date": on.isoformat(), "supplier_id": s["supplier_id"],
              "supplier_name": s["name"], "supplier_invoice": validate_text(supplier_invoice, "Supplier invoice no.", 30),
              **doc, "status": "ORDERED", "received_on": None, "amount_paid": 0.0, "payment_status": "UNPAID",
              "payments": [], "notes": validate_text(notes, "Notes", 120), "created_by": self.actor,
              "created_at": now_str()}
        self.db.insert("purchases", po)
        log_activity(self.db, self.actor, "PURCHASE_ORDER", f"{po['purchase_id']} {s['name']} {doc['grand_total']:.2f}")
        return self.receive(po["purchase_id"], on, supplier_invoice) if receive_now else po

    def get(self, purchase_id: str) -> dict:
        po = self.db.find_one("purchases", purchase_id=str(purchase_id or "").strip().upper())
        if not po:
            raise NotFoundError(f"Purchase '{purchase_id}' not found.")
        return po

    def receive(self, purchase_id: str, on=None, supplier_invoice: str | None = None) -> dict:
        """Goods received: stock goes up and each product's average cost is updated
        using the net cost per unit (after discount; GST is input credit, not cost)."""
        po = self.get(purchase_id)
        if po["status"] != "ORDERED":
            raise InventoryError(f"Purchase is {po['status']}.")
        on = parse_date(on or date.today())
        for l in po["lines"]:
            self.products.move(l["product_id"], l["qty"], "PURCHASE", po["purchase_id"],
                               unit_cost=round(l["taxable"] / l["qty"], 4))
        changes = {"status": "RECEIVED", "received_on": on.isoformat()}
        if supplier_invoice:
            changes["supplier_invoice"] = validate_text(supplier_invoice, "Supplier invoice no.", 30)
        log_activity(self.db, self.actor, "GOODS_RECEIVED", po["purchase_id"])
        return self.db.update("purchases", "purchase_id", po["purchase_id"], changes)

    def cancel(self, purchase_id: str, reason: str) -> dict:
        po = self.get(purchase_id)
        if po["status"] != "ORDERED":
            raise InventoryError("Only purchase orders not yet received can be cancelled.")
        log_activity(self.db, self.actor, "PURCHASE_CANCELLED", po["purchase_id"])
        return self.db.update("purchases", "purchase_id", po["purchase_id"],
                              {"status": "CANCELLED", "notes": validate_text(reason, "Reason", 120, required=True)})

    def pay(self, purchase_id: str, amount, mode: str, reference: str = "", on=None) -> dict:
        po = self.get(purchase_id)
        if po["status"] != "RECEIVED":
            raise InventoryError("Payments are recorded against received purchases.")
        due = round(po["grand_total"] - po["amount_paid"], 2)
        if due <= 0.005:
            raise InventoryError("This purchase is already fully paid.")
        amount = validate_amount(amount, "Amount", 0.01, due)
        mode = validate_choice(mode, [m for m in PAYMENT_MODES if m != "Credit"], "payment mode")
        paid = round(po["amount_paid"] + amount, 2)
        pays = po["payments"] + [{"at": (parse_date(on).isoformat() if on else now_str()), "amount": amount,
                                  "mode": mode, "reference": validate_text(reference, "Reference", 40)}]
        log_activity(self.db, self.actor, "SUPPLIER_PAID", f"{po['purchase_id']} {amount:.2f}")
        return self.db.update("purchases", "purchase_id", po["purchase_id"],
                              {"amount_paid": paid, "payments": pays,
                               "payment_status": payment_status(po["grand_total"], paid)})

    def list(self, status: str | None = None, start=None, end=None, supplier_id: str | None = None) -> list[dict]:
        pos = self.db.all("purchases")
        if status:
            pos = [p for p in pos if p["status"] == status.upper()]
        if start:
            pos = [p for p in pos if p["date"] >= parse_date(start).isoformat()]
        if end:
            pos = [p for p in pos if p["date"] <= parse_date(end).isoformat()]
        if supplier_id:
            pos = [p for p in pos if p["supplier_id"] == supplier_id.upper()]
        return sorted(pos, key=lambda p: (p["date"], p["purchase_id"]), reverse=True)
