"""Contact Management module: add / view / search / update / delete contacts,
favourites, categories, duplicate detection, recycle bin, birthdays and CSV import."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from .database import JSONDatabase
from .models import Contact
from .utils import (BIRTHDAY_WINDOW_DAYS, FALLBACK_CATEGORY, MAX_CATEGORIES, ContactBookError,
                    DuplicateError, NotFoundError, ValidationError, age_on_next_birthday,
                    days_until_birthday, now_str, validate_category_name, validate_date,
                    validate_email, validate_name, validate_phone, validate_text)

EDITABLE = ("first_name", "last_name", "phone", "alt_phone", "email", "company", "job_title",
            "address", "birthday", "category", "favorite", "notes")
SORT_KEYS = {
    "name": lambda c: (c.first_name.lower(), c.last_name.lower()),
    "recent": lambda c: c.created_at,
    "company": lambda c: (c.company.lower() or "~", c.first_name.lower()),
    "category": lambda c: (c.category, c.first_name.lower()),
}


class ContactManager:
    def __init__(self, db: JSONDatabase, username: str):
        self.db = db
        self.username = username

    # ================================================================ categories
    def categories(self) -> list[str]:
        user = self.db.find_one("users", username=self.username) or {}
        return list(user.get("categories") or [FALLBACK_CATEGORY])

    def _save_categories(self, cats: list[str]) -> None:
        self.db.update("users", "username", self.username, {"categories": cats})

    def _match_category(self, name: str) -> str:
        for c in self.categories():
            if c.lower() == str(name or "").strip().lower():
                return c
        raise ValidationError(f"Unknown category '{name}'. Available: {', '.join(self.categories())}")

    def add_category(self, name: str) -> str:
        name = validate_category_name(name)
        cats = self.categories()
        if name.lower() in (c.lower() for c in cats):
            raise ValidationError(f"Category '{name}' already exists.")
        if len(cats) >= MAX_CATEGORIES:
            raise ValidationError(f"You can have at most {MAX_CATEGORIES} categories.")
        self._save_categories(cats + [name])
        return name

    def rename_category(self, old: str, new: str) -> int:
        old = self._match_category(old)
        if old == FALLBACK_CATEGORY:
            raise ValidationError(f"'{FALLBACK_CATEGORY}' cannot be renamed.")
        new = validate_category_name(new)
        cats = self.categories()
        if new.lower() in (c.lower() for c in cats if c != old):
            raise ValidationError(f"Category '{new}' already exists.")
        self._save_categories([new if c == old else c for c in cats])
        return self._recategorise(old, new)

    def delete_category(self, name: str) -> int:
        """Delete a category; its contacts move to 'Other'. Returns how many moved."""
        name = self._match_category(name)
        if name == FALLBACK_CATEGORY:
            raise ValidationError(f"'{FALLBACK_CATEGORY}' cannot be deleted.")
        self._save_categories([c for c in self.categories() if c != name])
        return self._recategorise(name, FALLBACK_CATEGORY)

    def _recategorise(self, old: str, new: str) -> int:
        return self.db.update_where("contacts", {"category": new, "updated_at": now_str()},
                                    owner=self.username, category=old)

    # ================================================================ validation
    def _clean(self, data: dict, partial: bool = False) -> dict:
        out = {}
        checks = {
            "first_name": lambda v: validate_name(v, "First name"),
            "last_name": lambda v: validate_name(v, "Last name", required=False),
            "phone": lambda v: validate_phone(v),
            "alt_phone": lambda v: validate_phone(v, required=False),
            "email": lambda v: validate_email(v),
            "company": lambda v: validate_text(v, "Company", 60),
            "job_title": lambda v: validate_text(v, "Job title", 60),
            "address": lambda v: validate_text(v, "Address", 200),
            "birthday": lambda v: validate_date(v, "Birthday"),
            "category": lambda v: self._match_category(v or FALLBACK_CATEGORY),
            "favorite": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("y", "yes", "true", "1"),
            "notes": lambda v: validate_text(v, "Notes", 500),
        }
        for key, check in checks.items():
            if key in data:
                out[key] = check(data[key])
            elif not partial and key in ("first_name", "phone"):
                out[key] = check("")          # raises "required"
        if out.get("alt_phone") and out.get("alt_phone") == out.get("phone"):
            raise ValidationError("Alternate phone is the same as the main phone.")
        return out

    def find_duplicates(self, phone: str = "", email: str = "", exclude_id: str | None = None) -> list[Contact]:
        """Active contacts sharing a phone number or email with the given values."""
        dups = []
        for c in self.list():
            if c.id == exclude_id:
                continue
            numbers = {c.phone, c.alt_phone} - {""}
            if (phone and phone in numbers) or (email and email == c.email):
                dups.append(c)
        return dups

    def _check_duplicates(self, clean: dict, exclude_id: str | None = None) -> None:
        found = []
        for ph in (clean.get("phone"), clean.get("alt_phone")):
            if ph:
                found += self.find_duplicates(phone=ph, exclude_id=exclude_id)
        if clean.get("email"):
            found += self.find_duplicates(email=clean["email"], exclude_id=exclude_id)
        if found:
            names = ", ".join(sorted({c.full_name for c in found}))
            raise DuplicateError(f"A contact with the same phone or email already exists: {names}.")

    # ====================================================================== crud
    def add(self, allow_duplicate: bool = False, **data) -> Contact:
        unknown = set(data) - set(EDITABLE)
        if unknown:
            raise ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")
        clean = self._clean(data)
        if not allow_duplicate:
            self._check_duplicates(clean)
        contact = Contact(owner=self.username, **clean)
        self.db.insert("contacts", contact.to_dict())
        return contact

    def _raw(self, contact_id: str, include_deleted: bool = False) -> dict:
        rec = self.db.find_one("contacts", id=str(contact_id).strip(), owner=self.username)
        if not rec or (rec.get("deleted") and not include_deleted):
            raise NotFoundError(f"No contact with id '{contact_id}'.")
        return rec

    def get(self, contact_id: str) -> Contact:
        return Contact.from_dict(self._raw(contact_id))

    def update(self, contact_id: str, allow_duplicate: bool = False, **changes) -> Contact:
        self._raw(contact_id)
        changes = {k: v for k, v in changes.items() if k in EDITABLE and v is not None}
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = self._clean(changes, partial=True)
        if not allow_duplicate:
            self._check_duplicates(clean, exclude_id=contact_id)
        clean["updated_at"] = now_str()
        return Contact.from_dict(self.db.update("contacts", "id", contact_id, clean))

    def toggle_favorite(self, contact_id: str) -> Contact:
        c = self.get(contact_id)
        return self.update(contact_id, favorite=not c.favorite, allow_duplicate=True)

    # ------------------------------------------------------------- recycle bin
    def delete(self, contact_id: str) -> Contact:
        """Move a contact to the recycle bin (can be restored)."""
        self._raw(contact_id)
        return Contact.from_dict(self.db.update("contacts", "id", contact_id,
                                                {"deleted": True, "deleted_at": now_str()}))

    def trash(self) -> list[Contact]:
        recs = self.db.find("contacts", owner=self.username, deleted=True)
        return sorted((Contact.from_dict(r) for r in recs), key=lambda c: c.deleted_at or "", reverse=True)

    def restore(self, contact_id: str) -> Contact:
        rec = self._raw(contact_id, include_deleted=True)
        if not rec["deleted"]:
            raise ContactBookError("Contact is not in the recycle bin.")
        if self.find_duplicates(rec["phone"], rec["email"]):
            raise DuplicateError("Cannot restore: an active contact already uses this phone or email.")
        return Contact.from_dict(self.db.update("contacts", "id", contact_id,
                                                {"deleted": False, "deleted_at": None, "updated_at": now_str()}))

    def purge(self, contact_id: str) -> None:
        rec = self._raw(contact_id, include_deleted=True)
        if not rec["deleted"]:
            raise ContactBookError("Move the contact to the recycle bin first.")
        self.db.delete("contacts", "id", contact_id)

    def empty_trash(self) -> int:
        return self.db.delete_where("contacts", owner=self.username, deleted=True)

    # =================================================================== queries
    def list(self, category: str | None = None, favorites_only: bool = False,
             sort_by: str = "name") -> list[Contact]:
        contacts = [Contact.from_dict(r) for r in self.db.find("contacts", owner=self.username)
                    if not r.get("deleted")]
        if category:
            cat = self._match_category(category)
            contacts = [c for c in contacts if c.category == cat]
        if favorites_only:
            contacts = [c for c in contacts if c.favorite]
        key = SORT_KEYS.get(sort_by)
        if not key:
            raise ValidationError(f"Sort by one of: {', '.join(SORT_KEYS)}")
        if sort_by == "recent":
            # File order is insertion order; a stable sort then reversing puts the
            # newest first even when several were created in the same second.
            return sorted(contacts, key=key)[::-1]
        return sorted(contacts, key=key)

    def search(self, keyword: str = "", category: str | None = None, favorites_only: bool = False) -> list[Contact]:
        results = self.list(category, favorites_only)
        keyword = (keyword or "").strip()
        return [c for c in results if c.matches(keyword)] if keyword else results

    def by_letter(self) -> dict[str, list[Contact]]:
        groups: dict[str, list[Contact]] = {}
        for c in self.list():
            letter = c.first_name[0].upper() if c.first_name[0].isalpha() else "#"
            groups.setdefault(letter, []).append(c)
        return groups

    def upcoming_birthdays(self, days: int = BIRTHDAY_WINDOW_DAYS, today=None) -> list[dict]:
        out = []
        for c in self.list():
            d = days_until_birthday(c.birthday, today)
            if d is not None and d <= days:
                out.append({"contact": c, "in_days": d, "turning": age_on_next_birthday(c.birthday, today)})
        return sorted(out, key=lambda x: x["in_days"])

    def stats(self) -> dict:
        contacts = self.list()
        return {
            "total": len(contacts),
            "favorites": sum(c.favorite for c in contacts),
            "with_email": sum(bool(c.email) for c in contacts),
            "with_birthday": sum(bool(c.birthday) for c in contacts),
            "in_trash": len(self.trash()),
            "by_category": dict(Counter(c.category for c in contacts).most_common()),
            "top_companies": [(k, v) for k, v in Counter(c.company for c in contacts if c.company).most_common(5)],
        }

    # ==================================================================== import
    CSV_FIELDS = {"first name": "first_name", "last name": "last_name", "phone": "phone",
                  "alternate phone": "alt_phone", "email": "email", "company": "company",
                  "job title": "job_title", "address": "address", "birthday": "birthday",
                  "category": "category", "favorite": "favorite", "notes": "notes"}

    def import_csv(self, path: Path | str) -> dict:
        """Import contacts from a CSV with headers like the CSV export.

        Invalid rows and duplicates are skipped and reported; unknown
        categories are created automatically if there is room.
        """
        path = Path(path)
        if not path.exists():
            raise ContactBookError(f"File '{path}' not found.")
        imported, skipped = 0, []
        try:
            with path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames:
                    raise ContactBookError("The CSV file is empty.")
                mapping = {h: self.CSV_FIELDS[h.strip().lower()] for h in reader.fieldnames
                           if h and h.strip().lower() in self.CSV_FIELDS}
                if "first_name" not in mapping.values() or "phone" not in mapping.values():
                    raise ContactBookError("CSV must have at least 'First Name' and 'Phone' columns.")
                for line_no, row in enumerate(reader, start=2):
                    data = {mapping[h]: (row.get(h) or "").strip() for h in mapping}
                    cat = data.get("category")
                    if cat and cat.lower() not in (c.lower() for c in self.categories()):
                        try:
                            self.add_category(cat)
                        except ValidationError:
                            data["category"] = FALLBACK_CATEGORY
                    try:
                        self.add(**data)
                        imported += 1
                    except ContactBookError as exc:
                        skipped.append(f"Row {line_no}: {exc}")
        except UnicodeDecodeError:
            raise ContactBookError("The file is not UTF-8 text. Save it as 'CSV UTF-8' and try again.")
        except csv.Error as exc:
            raise ContactBookError(f"Could not read CSV: {exc}")
        return {"imported": imported, "skipped": skipped}
