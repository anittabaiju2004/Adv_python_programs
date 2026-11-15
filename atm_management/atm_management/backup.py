"""backup.py — back up the JSON database, list backups and restore."""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from database import FILE_NAMES
from utils import BackupError


class BackupManager:
    def __init__(self, data_dir: Path | str, backup_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: str = "manual") -> Path:
        base = self.backup_dir / f"atm_backup_{label}_{datetime.now():%Y%m%d_%H%M%S_%f}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for name in FILE_NAMES.values():          # only the database files
                    src = self.data_dir / name
                    if src.exists():
                        shutil.copy2(src, Path(tmp) / name)
                return Path(shutil.make_archive(str(base), "zip", root_dir=tmp))
        except OSError as exc:
            raise BackupError(f"Backup failed: {exc}") from exc

    def list_backups(self) -> list[dict]:
        out = []
        for p in sorted(self.backup_dir.glob("atm_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
            out.append({"path": p, "name": p.name, "size_kb": round(p.stat().st_size / 1024, 1),
                        "created": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
        return out

    @staticmethod
    def verify(archive: Path) -> dict:
        """Validate a backup and return record counts per file."""
        counts = {}
        try:
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
                for name in FILE_NAMES.values():
                    if name not in names:
                        raise BackupError(f"Backup is missing {name}.")
                    data = json.loads(zf.read(name).decode("utf-8"))
                    if not isinstance(data, list):
                        raise BackupError(f"{name} in backup has an invalid format.")
                    counts[name] = len(data)
        except zipfile.BadZipFile as exc:
            raise BackupError(f"{archive.name} is not a valid backup archive.") from exc
        except json.JSONDecodeError as exc:
            raise BackupError(f"Backup contains corrupted JSON: {exc}") from exc
        return counts

    def restore(self, archive: Path | str) -> Path:
        """Replace current data with a backup. Current data is saved first as a
        'pre_restore' backup (returned) so the restore can be undone."""
        archive = Path(archive)
        if not archive.exists():
            raise BackupError(f"Backup '{archive.name}' not found.")
        self.verify(archive)
        safety = self.create_backup("pre_restore")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with zipfile.ZipFile(archive) as zf:
                    for name in FILE_NAMES.values():
                        zf.extract(name, tmp)
                for name in FILE_NAMES.values():
                    shutil.copy2(Path(tmp) / name, self.data_dir / name)
        except OSError as exc:
            raise BackupError(f"Restore failed: {exc}. Previous data kept in {safety.name}.") from exc
        return safety
