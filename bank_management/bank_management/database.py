"""database.py — JSON file database.

Database files: customers.json, transactions.json, loans.json,
fixed_deposits.json, admins.json. Data is loaded automatically on every
read and saved automatically on every change. Writes are atomic (temp file
+ os.replace), so a crash never leaves a half-written file.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from utils import DatabaseError

COLLECTIONS = ("customers", "transactions", "loans", "fixed_deposits", "admins")
FILE_NAMES = {c: f"{c}.json" for c in COLLECTIONS}


class JSONDatabase:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self._lock = threading.RLock()
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(f"Cannot create data directory: {exc}") from exc
        for c in COLLECTIONS:
            if not self.path(c).exists():
                self._save(c, [])

    def path(self, collection: str) -> Path:
        if collection not in COLLECTIONS:
            raise DatabaseError(f"Unknown collection '{collection}'.")
        return self.data_dir / FILE_NAMES[collection]

    # ------------------------------------------------------------- raw io
    def _load(self, collection: str) -> list[dict]:
        p = self.path(collection)
        try:
            with p.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise DatabaseError(f"{p.name} is corrupted ({exc}). Restore a backup.") from exc
        except OSError as exc:
            raise DatabaseError(f"Cannot read {p.name}: {exc}") from exc
        if not isinstance(data, list):
            raise DatabaseError(f"{p.name} has an invalid format.")
        return data

    def _save(self, collection: str, records: list[dict]) -> None:
        p = self.path(collection)
        try:
            fd, tmp = tempfile.mkstemp(dir=self.data_dir, prefix=f".{collection}.", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(records, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, p)
        except OSError as exc:
            raise DatabaseError(f"Cannot write {p.name}: {exc}") from exc

    # --------------------------------------------------------------- api
    def all(self, collection: str) -> list[dict]:
        with self._lock:
            return self._load(collection)

    def find(self, collection: str, predicate: Callable[[dict], bool] | None = None, **match) -> list[dict]:
        out = [r for r in self.all(collection) if all(r.get(k) == v for k, v in match.items())]
        return [r for r in out if predicate(r)] if predicate else out

    def find_one(self, collection: str, **match) -> dict | None:
        found = self.find(collection, **match)
        return found[0] if found else None

    def insert(self, collection: str, record: dict) -> dict:
        with self._lock:
            records = self._load(collection)
            records.append(record)
            self._save(collection, records)
        return record

    def update(self, collection: str, key: str, value, changes: dict) -> dict | None:
        with self._lock:
            records = self._load(collection)
            for r in records:
                if r.get(key) == value:
                    r.update(changes)
                    self._save(collection, records)
                    return r
        return None

    def delete_where(self, collection: str, **match) -> int:
        with self._lock:
            records = self._load(collection)
            kept = [r for r in records if not all(r.get(k) == v for k, v in match.items())]
            if len(kept) != len(records):
                self._save(collection, kept)
            return len(records) - len(kept)

    @contextmanager
    def editing(self, collection: str):
        """Load a whole collection, let the caller mutate it, and save once.

        Used for operations that must change several records together
        (e.g. a fund transfer updating two balances) so they are written in
        a single atomic save. Nothing is saved if the block raises.
        """
        with self._lock:
            records = self._load(collection)
            yield records
            self._save(collection, records)
