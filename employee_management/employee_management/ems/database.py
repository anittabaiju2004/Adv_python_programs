"""JSON file database.

Each collection lives in its own file inside the data directory, e.g.
``data/employees.json``. Writes are atomic (write to a temp file, then
``os.replace``) so a crash can never leave a half-written file behind.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Callable

from .utils import DatabaseError

COLLECTIONS = ("users", "employees", "departments", "attendance", "leaves", "payroll")


class JSONDatabase:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self._lock = threading.RLock()
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(f"Cannot create data directory: {exc}") from exc
        for name in COLLECTIONS:
            path = self._path(name)
            if not path.exists():
                self._write(name, [])

    # ------------------------------------------------------------------ io
    def _path(self, collection: str) -> Path:
        if collection not in COLLECTIONS:
            raise DatabaseError(f"Unknown collection '{collection}'.")
        return self.data_dir / f"{collection}.json"

    def _read(self, collection: str) -> list[dict]:
        path = self._path(collection)
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise DatabaseError(f"{path.name} is corrupted: {exc}. Restore from a backup.") from exc
        except OSError as exc:
            raise DatabaseError(f"Cannot read {path.name}: {exc}") from exc
        if not isinstance(data, list):
            raise DatabaseError(f"{path.name} has an invalid format.")
        return data

    def _write(self, collection: str, records: list[dict]) -> None:
        path = self._path(collection)
        try:
            fd, tmp = tempfile.mkstemp(dir=self.data_dir, prefix=f".{collection}.", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(records, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except OSError as exc:
            raise DatabaseError(f"Cannot write {path.name}: {exc}") from exc

    # ---------------------------------------------------------------- crud
    def all(self, collection: str) -> list[dict]:
        with self._lock:
            return self._read(collection)

    def find(self, collection: str, predicate: Callable[[dict], bool] | None = None, **match) -> list[dict]:
        records = self.all(collection)
        out = [r for r in records if all(r.get(k) == v for k, v in match.items())]
        if predicate:
            out = [r for r in out if predicate(r)]
        return out

    def find_one(self, collection: str, **match) -> dict | None:
        found = self.find(collection, **match)
        return found[0] if found else None

    def insert(self, collection: str, record: dict) -> dict:
        with self._lock:
            records = self._read(collection)
            records.append(record)
            self._write(collection, records)
        return record

    def update(self, collection: str, key: str, value, changes: dict) -> dict | None:
        with self._lock:
            records = self._read(collection)
            for rec in records:
                if rec.get(key) == value:
                    rec.update(changes)
                    self._write(collection, records)
                    return rec
        return None

    def update_where(self, collection: str, changes: dict, **match) -> int:
        """Apply `changes` to every record matching all `match` fields. Returns the count."""
        with self._lock:
            records = self._read(collection)
            hits = [r for r in records if all(r.get(k) == v for k, v in match.items())]
            for r in hits:
                r.update(changes)
            if hits:
                self._write(collection, records)
            return len(hits)

    def delete(self, collection: str, key: str, value) -> bool:
        with self._lock:
            records = self._read(collection)
            kept = [r for r in records if r.get(key) != value]
            if len(kept) == len(records):
                return False
            self._write(collection, kept)
            return True

    def delete_where(self, collection: str, **match) -> int:
        with self._lock:
            records = self._read(collection)
            kept = [r for r in records if not all(r.get(k) == v for k, v in match.items())]
            removed = len(records) - len(kept)
            if removed:
                self._write(collection, kept)
            return removed
