"""Category Management: product categories with default HSN code and GST rate."""
from __future__ import annotations

from .auth import log_activity
from .database import JSONDatabase
from .utils import (InventoryError, NotFoundError, ValidationError, now_str, validate_gst_rate, validate_hsn,
                    validate_name, validate_text)

DEFAULT_CATEGORIES = [  # name, default HSN, default GST %, description
    ("Groceries", "1006", 5.0, "Rice, pulses, flour, spices"),
    ("Beverages", "2202", 40.0, "Soft drinks and aerated beverages"),
    ("Personal Care", "3305", 5.0, "Soap, shampoo, toothpaste"),
    ("Household", "3402", 18.0, "Detergents and cleaning products"),
    ("Stationery", "9608", 18.0, "Pens, files, office supplies"),
    ("Electronics", "8504", 18.0, "Chargers, batteries, accessories"),
]


class CategoryManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        if not self.db.all("categories"):
            for name, hsn, rate, desc in DEFAULT_CATEGORIES:
                self.db.insert("categories", {"name": name, "hsn": hsn, "gst_rate": rate, "description": desc,
                                              "created_at": now_str()})

    def list(self) -> list[dict]:
        return sorted(self.db.all("categories"), key=lambda c: c["name"])

    def names(self) -> list[str]:
        return [c["name"] for c in self.list()]

    def get(self, name: str) -> dict:
        for c in self.db.all("categories"):
            if c["name"].lower() == str(name or "").strip().lower():
                return c
        raise NotFoundError(f"Category '{name}' not found.")

    def add(self, name: str, gst_rate, hsn: str = "", description: str = "") -> dict:
        name = validate_name(name, "Category name", 40)
        if name.lower() in (n.lower() for n in self.names()):
            raise ValidationError(f"Category '{name}' already exists.")
        c = {"name": name, "hsn": validate_hsn(hsn), "gst_rate": validate_gst_rate(gst_rate),
             "description": validate_text(description, "Description", 120), "created_at": now_str()}
        self.db.insert("categories", c)
        log_activity(self.db, self.actor, "CATEGORY_ADDED", name)
        return c

    def update(self, name: str, new_name: str | None = None, gst_rate=None, hsn: str | None = None,
               description: str | None = None) -> dict:
        c = self.get(name)
        changes = {}
        if new_name and new_name.strip() != c["name"]:
            new_name = validate_name(new_name, "Category name", 40)
            if new_name.lower() in (n.lower() for n in self.names() if n != c["name"]):
                raise ValidationError(f"Category '{new_name}' already exists.")
            changes["name"] = new_name
        if gst_rate not in (None, ""):
            changes["gst_rate"] = validate_gst_rate(gst_rate)
        if hsn is not None:
            changes["hsn"] = validate_hsn(hsn)
        if description is not None:
            changes["description"] = validate_text(description, "Description", 120)
        if not changes:
            raise ValidationError("Nothing to update.")
        updated = self.db.update("categories", "name", c["name"], changes)
        if "name" in changes:   # keep products pointing at the renamed category
            self.db.update_where("products", {"category": changes["name"]}, category=c["name"])
        log_activity(self.db, self.actor, "CATEGORY_UPDATED", f"{c['name']}: {', '.join(changes)}")
        return updated

    def delete(self, name: str) -> None:
        c = self.get(name)
        if self.db.find("products", category=c["name"]):
            raise InventoryError(f"Category '{c['name']}' has products. Move them to another category first.")
        self.db.delete("categories", "name", c["name"])
        log_activity(self.db, self.actor, "CATEGORY_DELETED", c["name"])

    def product_counts(self) -> dict[str, int]:
        counts = {n: 0 for n in self.names()}
        for p in self.db.all("products"):
            if p["active"]:
                counts[p["category"]] = counts.get(p["category"], 0) + 1
        return counts
