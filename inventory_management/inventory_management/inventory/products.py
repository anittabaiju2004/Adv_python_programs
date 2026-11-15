"""Product Management: product CRUD, stock levels, weighted-average cost,
stock ledger, adjustments, and low / out-of-stock detection."""
from __future__ import annotations

import re

from .auth import log_activity
from .categories import CategoryManager
from .database import JSONDatabase
from .utils import (UNITS, InventoryError, NotFoundError, StockError, ValidationError, now_str,
                    validate_amount, validate_choice, validate_gst_rate, validate_hsn, validate_name,
                    validate_qty, validate_text)

ADJUST_REASONS = ["Damaged", "Expired", "Lost / Theft", "Audit correction", "Found in audit", "Sample / Internal use"]


class ProductManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.categories = CategoryManager(db, actor)

    # ------------------------------------------------------------- helpers
    def _next_id(self) -> str:
        nums = [int(p["product_id"][1:]) for p in self.db.all("products")]
        return f"P{(max(nums) + 1) if nums else 1:04d}"

    def get(self, product_id: str) -> dict:
        key = str(product_id or "").strip().upper()
        p = self.db.find_one("products", product_id=key) or \
            next((x for x in self.db.all("products") if key and key in (x["sku"].upper(), x["barcode"])), None)
        if not p:
            raise NotFoundError(f"Product '{product_id}' not found.")
        return p

    @staticmethod
    def price_with_gst(p: dict) -> float:
        return round(p["selling_price"] * (1 + p["gst_rate"] / 100), 2)

    def _check_prices(self, cost: float, selling: float, mrp: float | None, gst_rate: float) -> None:
        if mrp and round(selling * (1 + gst_rate / 100), 2) > mrp + 0.005:
            raise ValidationError(f"Selling price incl. GST ({selling * (1 + gst_rate / 100):,.2f}) exceeds "
                                  f"the MRP ({mrp:,.2f}).")

    # ---------------------------------------------------------------- crud
    def add(self, name: str, category: str, unit: str, purchase_price, selling_price, opening_stock=0,
            reorder_level=10, gst_rate=None, hsn: str | None = None, brand: str = "", sku: str = "",
            barcode: str = "", mrp=None, location: str = "") -> dict:
        cat = self.categories.get(category)
        name = validate_name(name, "Product name")
        unit = validate_choice(unit, UNITS, "unit")
        cost = validate_amount(purchase_price, "Purchase price", 0.01)
        selling = validate_amount(selling_price, "Selling price", 0.01)
        rate = validate_gst_rate(cat["gst_rate"] if gst_rate in (None, "") else gst_rate)
        mrp = validate_amount(mrp, "MRP") if mrp not in (None, "") else None
        self._check_prices(cost, selling, mrp, rate)
        sku = str(sku or "").strip().upper()
        if sku and not re.fullmatch(r"[A-Z0-9\-]{3,20}", sku):
            raise ValidationError("SKU must be 3-20 letters, digits or hyphens.")
        barcode = str(barcode or "").strip()
        if barcode and not re.fullmatch(r"\d{8}|\d{12,14}", barcode):
            raise ValidationError("Barcode must be EAN-8, UPC-12 or EAN-13 digits.")
        for p in self.db.all("products"):
            if p["name"].lower() == name.lower() and p["unit"] == unit and p.get("brand", "").lower() == brand.strip().lower():
                raise ValidationError(f"Product '{name}' ({unit}) already exists as {p['product_id']}.")
            if sku and p["sku"] == sku:
                raise ValidationError(f"SKU {sku} is already used by {p['product_id']}.")
            if barcode and p["barcode"] == barcode:
                raise ValidationError(f"Barcode {barcode} is already used by {p['product_id']}.")
        product = {"product_id": self._next_id(), "name": name, "category": cat["name"],
                   "brand": validate_text(brand, "Brand", 40), "unit": unit,
                   "hsn": validate_hsn(cat["hsn"] if hsn in (None, "") else hsn), "gst_rate": rate,
                   "purchase_price": cost, "avg_cost": cost, "selling_price": selling, "mrp": mrp,
                   "stock": 0.0, "reorder_level": validate_qty(reorder_level, unit, "Reorder level", allow_zero=True),
                   "sku": sku, "barcode": barcode, "location": validate_text(location, "Location", 20),
                   "active": True, "created_at": now_str(), "updated_at": now_str()}
        self.db.insert("products", product)
        opening = validate_qty(opening_stock or 0, unit, "Opening stock", allow_zero=True)
        if opening:
            self.move(product["product_id"], opening, "OPENING", "Opening stock", unit_cost=cost)
        log_activity(self.db, self.actor, "PRODUCT_ADDED", f"{product['product_id']} {name}")
        return self.get(product["product_id"])

    EDITABLE = {"name", "category", "brand", "unit", "hsn", "gst_rate", "selling_price", "purchase_price", "mrp",
                "reorder_level", "sku", "barcode", "location"}

    def update(self, product_id: str, **changes) -> dict:
        p = self.get(product_id)
        changes = {k: v for k, v in changes.items() if v is not None}
        bad = set(changes) - self.EDITABLE
        if bad:
            raise ValidationError(f"Cannot update {', '.join(sorted(bad))} (stock changes go through purchases, "
                                  "sales or adjustments).")
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = {}
        if "name" in changes:
            clean["name"] = validate_name(changes["name"], "Product name")
        if "category" in changes:
            clean["category"] = self.categories.get(changes["category"])["name"]
        if "brand" in changes:
            clean["brand"] = validate_text(changes["brand"], "Brand", 40)
        if "unit" in changes:
            unit = validate_choice(changes["unit"], UNITS, "unit")
            if unit != p["unit"] and self.db.find("stock_movements", product_id=p["product_id"]):
                raise InventoryError("Unit cannot change once the product has stock history.")
            clean["unit"] = unit
        if "hsn" in changes:
            clean["hsn"] = validate_hsn(changes["hsn"])
        if "gst_rate" in changes:
            clean["gst_rate"] = validate_gst_rate(changes["gst_rate"])
        if "selling_price" in changes:
            clean["selling_price"] = validate_amount(changes["selling_price"], "Selling price")
        if "purchase_price" in changes:
            clean["purchase_price"] = validate_amount(changes["purchase_price"], "Purchase price")
        if "mrp" in changes:
            clean["mrp"] = validate_amount(changes["mrp"], "MRP") if changes["mrp"] not in ("", 0) else None
        if "reorder_level" in changes:
            clean["reorder_level"] = validate_qty(changes["reorder_level"], clean.get("unit", p["unit"]),
                                                  "Reorder level", allow_zero=True)
        if "location" in changes:
            clean["location"] = validate_text(changes["location"], "Location", 20)
        for key in ("sku", "barcode"):
            if key in changes:
                val = str(changes[key] or "").strip().upper()
                if val and any(x[key] == val and x["product_id"] != p["product_id"] for x in self.db.all("products")):
                    raise ValidationError(f"{key.upper()} {val} is already used.")
                clean[key] = val
        merged = {**p, **clean}
        self._check_prices(merged["purchase_price"], merged["selling_price"], merged["mrp"], merged["gst_rate"])
        clean["updated_at"] = now_str()
        log_activity(self.db, self.actor, "PRODUCT_UPDATED", f"{p['product_id']}: {', '.join(c for c in clean if c != 'updated_at')}")
        return self.db.update("products", "product_id", p["product_id"], clean)

    def set_active(self, product_id: str, active: bool) -> dict:
        p = self.get(product_id)
        log_activity(self.db, self.actor, "PRODUCT_REACTIVATED" if active else "PRODUCT_DISCONTINUED", p["product_id"])
        return self.db.update("products", "product_id", p["product_id"], {"active": active, "updated_at": now_str()})

    def delete(self, product_id: str) -> None:
        """Only products with no purchases or sales can be deleted; others are discontinued."""
        p = self.get(product_id)
        moves = [m for m in self.db.find("stock_movements", product_id=p["product_id"]) if m["type"] != "OPENING"]
        if moves:
            raise InventoryError(f"{p['product_id']} has transactions; discontinue it instead of deleting.")
        self.db.delete_where("stock_movements", product_id=p["product_id"])
        self.db.delete("products", "product_id", p["product_id"])
        log_activity(self.db, self.actor, "PRODUCT_DELETED", p["product_id"])

    # --------------------------------------------------------------- stock
    def move(self, product_id: str, qty: float, mtype: str, ref: str, unit_cost: float | None = None,
             note: str = "") -> dict:
        """Change stock by `qty` (+ in, - out) and record it in the stock ledger.

        Inbound stock with a unit cost updates the weighted-average cost:
            new_avg = (stock x avg + qty x cost) / (stock + qty)
        """
        p = self.get(product_id)
        new_stock = round(p["stock"] + qty, 3)
        if new_stock < -0.0005:
            raise StockError(f"Insufficient stock for {p['name']}: {p['stock']:g} {p['unit']} available, "
                             f"{-qty:g} needed.")
        changes = {"stock": max(new_stock, 0.0), "updated_at": now_str()}
        if qty > 0 and unit_cost:
            base = max(p["stock"], 0)
            changes["avg_cost"] = round((base * p["avg_cost"] + qty * unit_cost) / (base + qty), 4)
            if mtype in ("PURCHASE", "OPENING"):
                changes["purchase_price"] = round(unit_cost, 2)
        self.db.update("products", "product_id", p["product_id"], changes)
        mv = {"id": f"M{len(self.db.all('stock_movements')) + 1:06d}", "product_id": p["product_id"], "at": now_str(),
              "type": mtype, "qty": qty, "balance": changes["stock"], "ref": ref,
              "unit_cost": unit_cost if unit_cost is not None else p["avg_cost"], "note": note, "by": self.actor}
        self.db.insert("stock_movements", mv)
        return mv

    def adjust_stock(self, product_id: str, qty, reason: str, note: str = "") -> dict:
        """Manual adjustment (damage, expiry, audit). qty is signed: -3 removes 3, +2 adds 2."""
        p = self.get(product_id)
        try:
            q = float(qty)
        except (TypeError, ValueError):
            raise ValidationError("Quantity must be a number (negative to remove stock).")
        if q == 0:
            raise ValidationError("Quantity cannot be zero.")
        validate_qty(abs(q), p["unit"])
        reason = validate_choice(reason, ADJUST_REASONS, "reason")
        mv = self.move(p["product_id"], round(q, 3), "ADJUSTMENT", reason, note=validate_text(note, "Note", 120))
        log_activity(self.db, self.actor, "STOCK_ADJUSTED", f"{p['product_id']} {q:+g} ({reason})")
        return mv

    def ledger(self, product_id: str) -> list[dict]:
        p = self.get(product_id)
        return self.db.find("stock_movements", product_id=p["product_id"])

    # ------------------------------------------------------------- queries
    SORTS = {"id": lambda p: p["product_id"], "name": lambda p: p["name"].lower(),
             "stock": lambda p: p["stock"], "category": lambda p: (p["category"], p["name"].lower()),
             "value": lambda p: -p["stock"] * p["avg_cost"]}

    def list(self, category: str | None = None, include_inactive: bool = False, sort_by: str = "id") -> list[dict]:
        ps = self.db.all("products")
        if not include_inactive:
            ps = [p for p in ps if p["active"]]
        if category:
            cat = self.categories.get(category)["name"]
            ps = [p for p in ps if p["category"] == cat]
        if sort_by not in self.SORTS:
            raise ValidationError(f"Sort by one of: {', '.join(self.SORTS)}")
        return sorted(ps, key=self.SORTS[sort_by])

    def search(self, keyword: str, include_inactive: bool = False) -> list[dict]:
        k = str(keyword or "").strip().lower()
        return [p for p in self.list(include_inactive=include_inactive)
                if not k or k in p["name"].lower() or k in p["brand"].lower() or k == p["product_id"].lower()
                or k == p["sku"].lower() or k == p["barcode"] or k in p["category"].lower()]

    def low_stock(self) -> list[dict]:
        return [p for p in self.list() if 0 < p["stock"] <= p["reorder_level"]]

    def out_of_stock(self) -> list[dict]:
        return [p for p in self.list() if p["stock"] <= 0]

    def reorder_suggestions(self) -> list[dict]:
        """Products at or below reorder level, with a suggested order quantity
        that brings stock up to twice the reorder level."""
        out = []
        for p in self.list():
            if p["stock"] <= p["reorder_level"]:
                qty = max(p["reorder_level"] * 2 - p["stock"], p["reorder_level"], 1)
                qty = round(qty, 3) if p["unit"] in ("kg", "g", "litre", "ml", "metre") else float(int(qty + 0.999))
                last = self._last_supplier(p["product_id"])
                out.append({"product": p, "suggested_qty": qty, "estimated_cost": round(qty * p["purchase_price"], 2),
                            "last_supplier": last})
        return out

    def _last_supplier(self, product_id: str) -> str | None:
        for po in sorted(self.db.all("purchases"), key=lambda x: x["date"], reverse=True):
            if po["status"] == "RECEIVED" and any(l["product_id"] == product_id for l in po["lines"]):
                return po["supplier_id"]
        return None

    def valuation(self) -> dict:
        ps = self.list()
        cost = round(sum(p["stock"] * p["avg_cost"] for p in ps), 2)
        retail = round(sum(p["stock"] * p["selling_price"] for p in ps), 2)
        return {"products": len(ps), "units": round(sum(p["stock"] for p in ps), 3), "cost_value": cost,
                "selling_value": retail, "potential_margin": round(retail - cost, 2),
                "low_stock": len(self.low_stock()), "out_of_stock": len(self.out_of_stock())}
