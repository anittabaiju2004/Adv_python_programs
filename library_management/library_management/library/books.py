"""Book Management: catalogue (titles) and physical copies with accession
numbers, search, availability, and copy withdrawal."""
from __future__ import annotations

from collections import Counter
from datetime import date

from .auth import log_activity
from .database import JSONDatabase
from .utils import (CATEGORIES, LANGUAGES, LibraryError, NotFoundError, ValidationError, now_str,
                    validate_amount, validate_choice, validate_int, validate_isbn, validate_text, validate_title)

COPY_STATUSES = ["AVAILABLE", "ISSUED", "ON_HOLD", "LOST", "DAMAGED", "WITHDRAWN"]
IN_COLLECTION = ("AVAILABLE", "ISSUED", "ON_HOLD", "DAMAGED")


class BookManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    # ------------------------------------------------------------- ids
    def _next_book_id(self) -> str:
        nums = [int(b["book_id"][1:]) for b in self.db.all("books")]
        return f"B{(max(nums) + 1) if nums else 1:04d}"

    def _next_accession(self) -> int:
        nums = [int(c["accession"][3:]) for c in self.db.all("copies")]
        return (max(nums) + 1) if nums else 1

    # ------------------------------------------------------------ titles
    def _clean(self, data: dict, current: dict | None = None) -> dict:
        out = {}
        if "title" in data:
            out["title"] = validate_title(data["title"])
        if "authors" in data:
            out["authors"] = validate_title(data["authors"], "Author(s)", 120)
        if "isbn" in data:
            out["isbn"] = validate_isbn(data["isbn"])
            if out["isbn"]:
                clash = next((b for b in self.db.all("books") if b["isbn"] == out["isbn"]
                              and (not current or b["book_id"] != current["book_id"])), None)
                if clash:
                    raise ValidationError(f"ISBN already catalogued as {clash['book_id']} ({clash['title']}). "
                                          "Add copies to it instead.")
        if "publisher" in data:
            out["publisher"] = validate_text(data["publisher"], "Publisher", 80)
        if "year" in data and str(data["year"]).strip():
            out["year"] = validate_int(data["year"], "Year", 1450, date.today().year)
        if "edition" in data:
            out["edition"] = validate_text(data["edition"], "Edition", 20)
        if "category" in data:
            out["category"] = validate_choice(data["category"], CATEGORIES, "category")
        if "language" in data:
            out["language"] = validate_choice(data["language"] or "English", LANGUAGES, "language")
        if "price" in data:
            out["price"] = validate_amount(data["price"], "Price", 1, 1_00_000)
        if "shelf" in data:
            out["shelf"] = validate_text(data["shelf"], "Shelf", 20).upper()
        if "keywords" in data:
            out["keywords"] = validate_text(data["keywords"], "Keywords", 150)
        if "reference_only" in data:
            v = data["reference_only"]
            out["reference_only"] = v if isinstance(v, bool) else str(v).lower() in ("y", "yes", "true", "1")
        return out

    def add(self, title: str, authors: str, category: str, price, copies=1, isbn: str = "", publisher: str = "",
            year="", edition: str = "", language: str = "English", shelf: str = "", keywords: str = "",
            reference_only: bool = False) -> dict:
        clean = self._clean({"title": title, "authors": authors, "category": category, "price": price, "isbn": isbn,
                             "publisher": publisher, "year": year, "edition": edition, "language": language,
                             "shelf": shelf, "keywords": keywords, "reference_only": reference_only})
        if not clean.get("isbn"):
            dup = next((b for b in self.db.all("books") if b["title"].lower() == clean["title"].lower()
                        and b["authors"].lower() == clean["authors"].lower()), None)
            if dup:
                raise ValidationError(f"'{dup['title']}' by {dup['authors']} already exists as {dup['book_id']}.")
        book = {"book_id": self._next_book_id(), "isbn": "", "publisher": "", "year": None, "edition": "",
                "language": "English", "shelf": "", "keywords": "", "reference_only": False, **clean,
                "created_at": now_str()}
        self.db.insert("books", book)
        log_activity(self.db, self.actor, "BOOK_ADDED", f"{book['book_id']} {book['title']}")
        n = validate_int(copies, "Number of copies", 0, 200)
        if n:
            self.add_copies(book["book_id"], n)
        return book

    def get(self, ref: str) -> dict:
        key = str(ref or "").strip().upper()
        b = self.db.find_one("books", book_id=key)
        if not b and key:
            try:
                isbn = validate_isbn(key)
                b = self.db.find_one("books", isbn=isbn) if isbn else None
            except ValidationError:
                b = None
        if not b and key.startswith("ACC"):
            c = self.db.find_one("copies", accession=key)
            b = self.db.find_one("books", book_id=c["book_id"]) if c else None
        if not b:
            raise NotFoundError(f"Book '{ref}' not found.")
        return b

    def update(self, book_id: str, **changes) -> dict:
        b = self.get(book_id)
        changes = {k: v for k, v in changes.items() if v is not None}
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = self._clean(changes, b)
        log_activity(self.db, self.actor, "BOOK_UPDATED", f"{b['book_id']}: {', '.join(clean)}")
        return self.db.update("books", "book_id", b["book_id"], clean)

    def delete(self, book_id: str) -> None:
        b = self.get(book_id)
        if self.db.find("loans", book_id=b["book_id"]) or self.db.find("reservations", book_id=b["book_id"]):
            raise LibraryError("This title has circulation history; withdraw its copies instead of deleting.")
        self.db.delete_where("copies", book_id=b["book_id"])
        self.db.delete("books", "book_id", b["book_id"])
        log_activity(self.db, self.actor, "BOOK_DELETED", b["book_id"])

    # ------------------------------------------------------------ copies
    def add_copies(self, book_id: str, count: int = 1, condition: str = "New") -> list[dict]:
        b = self.get(book_id)
        count = validate_int(count, "Number of copies", 1, 200)
        start = self._next_accession()
        out = []
        for i in range(count):
            c = {"accession": f"ACC{start + i:05d}", "book_id": b["book_id"], "status": "AVAILABLE",
                 "condition": validate_text(condition, "Condition", 30) or "New", "hold_for": None,
                 "hold_until": None, "added_on": now_str()[:10], "note": ""}
            self.db.insert("copies", c)
            out.append(c)
        log_activity(self.db, self.actor, "COPIES_ADDED", f"{b['book_id']} x{count}")
        return out

    def get_copy(self, accession: str) -> dict:
        c = self.db.find_one("copies", accession=str(accession or "").strip().upper())
        if not c:
            raise NotFoundError(f"Copy '{accession}' not found.")
        return c

    def copies(self, book_id: str) -> list[dict]:
        return sorted(self.db.find("copies", book_id=self.get(book_id)["book_id"]), key=lambda c: c["accession"])

    def withdraw_copy(self, accession: str, reason: str) -> dict:
        c = self.get_copy(accession)
        if c["status"] not in ("AVAILABLE", "DAMAGED"):
            raise LibraryError(f"Copy {c['accession']} is {c['status']}; only available or damaged copies can be withdrawn.")
        log_activity(self.db, self.actor, "COPY_WITHDRAWN", f"{c['accession']} ({reason})")
        return self.db.update("copies", "accession", c["accession"],
                              {"status": "WITHDRAWN", "note": validate_text(reason, "Reason", 80, required=True)})

    def set_copy_status(self, accession: str, status: str, note: str = "") -> dict:
        """Used for repairs: DAMAGED -> AVAILABLE once fixed, or mark an available copy damaged."""
        c = self.get_copy(accession)
        status = validate_choice(status, ["AVAILABLE", "DAMAGED"], "status")
        if c["status"] not in ("AVAILABLE", "DAMAGED"):
            raise LibraryError(f"Copy is {c['status']}; change it through circulation.")
        return self.db.update("copies", "accession", c["accession"], {"status": status, "note": note})

    # ----------------------------------------------------------- queries
    def availability(self, book_id: str) -> dict:
        cs = self.copies(book_id)
        counts = Counter(c["status"] for c in cs)
        return {"total": sum(counts[s] for s in IN_COLLECTION), "available": counts["AVAILABLE"],
                "issued": counts["ISSUED"], "on_hold": counts["ON_HOLD"], "damaged": counts["DAMAGED"],
                "lost": counts["LOST"], "withdrawn": counts["WITHDRAWN"]}

    def list(self, category: str | None = None) -> list[dict]:
        bs = self.db.all("books")
        if category:
            category = validate_choice(category, CATEGORIES, "category")
            bs = [b for b in bs if b["category"] == category]
        return sorted(bs, key=lambda b: b["book_id"])

    def search(self, keyword: str = "", category: str | None = None, available_only: bool = False) -> list[dict]:
        k = str(keyword or "").strip().lower()
        isbn = ""
        try:
            isbn = validate_isbn(k) if k and k.replace("-", "").replace(" ", "").isdigit() else ""
        except ValidationError:
            pass
        out = []
        avail = Counter(c["book_id"] for c in self.db.all("copies") if c["status"] == "AVAILABLE")
        for b in self.list(category):
            hay = " ".join([b["title"], b["authors"], b["publisher"], b["keywords"], b["category"]]).lower()
            if k and not (k in hay or k == b["book_id"].lower() or (isbn and isbn == b["isbn"])):
                continue
            if available_only and not avail[b["book_id"]]:
                continue
            out.append({**b, "available": avail[b["book_id"]]})
        return out

    def stats(self) -> dict:
        copies = self.db.all("copies")
        st = Counter(c["status"] for c in copies)
        books = self.db.all("books")
        return {"titles": len(books), "copies": sum(st[s] for s in IN_COLLECTION), "by_status": dict(st),
                "by_category": dict(Counter(b["category"] for b in books).most_common()),
                "collection_value": round(sum(next((b["price"] for b in books if b["book_id"] == c["book_id"]), 0)
                                              for c in copies if c["status"] in IN_COLLECTION), 2)}
