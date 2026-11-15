"""Backup & Restore: zip snapshots of the JSON data directory."""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from .database import COLLECTIONS
from .exceptions import BackupError


class BackupManager:
    def __init__(self, data_dir: Path | str, backup_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: str = "manual") -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base = self.backup_dir / f"backup_{label}_{stamp}"
        try:
            archive = shutil.make_archive(str(base), "zip", root_dir=self.data_dir)
        except OSError as exc:
            raise BackupError(f"Backup failed: {exc}") from exc
        return Path(archive)

    def list_backups(self) -> list[Path]:
        return sorted(self.backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    @staticmethod
    def verify(archive: Path) -> None:
        """Check the archive is a valid zip containing valid JSON collections."""
        try:
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
                for coll in COLLECTIONS:
                    name = f"{coll}.json"
                    if name not in names:
                        raise BackupError(f"Backup is missing {name}.")
                    data = json.loads(zf.read(name).decode("utf-8"))
                    if not isinstance(data, list):
                        raise BackupError(f"{name} in backup has an invalid format.")
        except zipfile.BadZipFile as exc:
            raise BackupError(f"{archive.name} is not a valid backup archive.") from exc
        except json.JSONDecodeError as exc:
            raise BackupError(f"Backup contains corrupted JSON: {exc}") from exc

    def restore(self, archive: Path | str) -> Path:
        """Restore data from an archive. A safety backup of current data is made first
        and returned so the restore itself can be undone."""
        archive = Path(archive)
        if not archive.exists():
            raise BackupError(f"Backup file '{archive}' not found.")
        self.verify(archive)
        safety = self.create_backup("pre_restore")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with zipfile.ZipFile(archive) as zf:
                    for coll in COLLECTIONS:
                        zf.extract(f"{coll}.json", tmp)
                for coll in COLLECTIONS:
                    shutil.copy2(Path(tmp) / f"{coll}.json", self.data_dir / f"{coll}.json")
        except OSError as exc:
            raise BackupError(f"Restore failed: {exc}. Safety backup at {safety.name}") from exc
        return safety

    def delete_backup(self, archive: Path | str) -> None:
        archive = Path(archive)
        if archive.parent.resolve() != self.backup_dir.resolve() or not archive.exists():
            raise BackupError("Backup not found.")
        archive.unlink()
