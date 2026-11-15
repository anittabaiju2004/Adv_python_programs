"""Category Management: quiz / question categories."""
from __future__ import annotations

from .auth import log_activity
from .database import JSONDatabase
from .utils import QuizError, NotFoundError, ValidationError, now_str, validate_text


class CategoryManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def list(self) -> list[dict]:
        return sorted(self.db.all("categories"), key=lambda c: c["name"])

    def names(self) -> list[str]:
        return [c["name"] for c in self.list()]

    def get(self, name: str) -> dict:
        for c in self.db.all("categories"):
            if c["name"].lower() == str(name or "").strip().lower():
                return c
        raise NotFoundError(f"Category '{name}' not found.")

    def add(self, name: str, description: str = "") -> dict:
        name = validate_text(name, "Category name", 40, required=True)
        if not name[0].isalnum():
            raise ValidationError("Category name must start with a letter or digit.")
        if name.lower() in (n.lower() for n in self.names()):
            raise ValidationError(f"Category '{name}' already exists.")
        c = {"name": name, "description": validate_text(description, "Description", 150), "created_at": now_str()}
        self.db.insert("categories", c)
        log_activity(self.db, self.actor, "CATEGORY_ADDED", name)
        return c

    def update(self, name: str, new_name: str | None = None, description: str | None = None) -> dict:
        c = self.get(name)
        changes = {}
        if new_name and new_name.strip() != c["name"]:
            new_name = validate_text(new_name, "Category name", 40, required=True)
            if new_name.lower() in (n.lower() for n in self.names() if n != c["name"]):
                raise ValidationError(f"Category '{new_name}' already exists.")
            changes["name"] = new_name
        if description is not None:
            changes["description"] = validate_text(description, "Description", 150)
        if not changes:
            raise ValidationError("Nothing to update.")
        updated = self.db.update("categories", "name", c["name"], changes)
        if "name" in changes:                 # keep questions and quizzes pointing at the renamed category
            self.db.update_where("questions", {"category": changes["name"]}, category=c["name"])
            self.db.update_where("quizzes", {"category": changes["name"]}, category=c["name"])
        log_activity(self.db, self.actor, "CATEGORY_UPDATED", c["name"])
        return updated

    def delete(self, name: str) -> None:
        c = self.get(name)
        if self.db.find("questions", category=c["name"]) or self.db.find("quizzes", category=c["name"]):
            raise QuizError(f"'{c['name']}' still has questions or quizzes.")
        self.db.delete("categories", "name", c["name"])
        log_activity(self.db, self.actor, "CATEGORY_DELETED", c["name"])

    def stats(self) -> list[dict]:
        qs = self.db.all("questions")
        out = []
        for c in self.list():
            mine = [q for q in qs if q["category"] == c["name"] and q["active"]]
            out.append({**c, "questions": len(mine),
                        **{d.lower(): sum(1 for q in mine if q["difficulty"] == d) for d in ("Easy", "Medium", "Hard")}})
        return out
