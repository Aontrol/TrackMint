from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from finance_app.core.audit import AuditLogger
from finance_app.db.connection import db_session
from finance_app.db.schema import DEFAULT_ACCOUNTS, DEFAULT_CATEGORIES, FINANCE_SCHEMA
from finance_app.security.encryption import EncryptionService
from finance_app.utils.paths import backup_dir, finance_db_path


LOGGER = logging.getLogger(__name__)


class BackupService:
    def __init__(self, encryption: EncryptionService, audit: AuditLogger) -> None:
        self.encryption = encryption
        self.audit = audit

    def encrypted_local_backup(self, target: Path | None = None) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = target or backup_dir() / f"finance_backup_{timestamp}.enc"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.encryption.encrypt_file(finance_db_path(), target)
        self.audit.log("backup", new_value={"path": str(target), "encrypted": True}, source="local")
        return target

    def restore_encrypted_backup(self, encrypted_path: Path) -> None:
        tmp = backup_dir() / "restore_candidate.db"
        self.encryption.decrypt_file(encrypted_path, tmp)
        if not self._looks_like_finance_db(tmp):
            tmp.unlink(missing_ok=True)
            raise ValueError("Backup was decrypted but is not a valid TrackMint database")
        shutil.copy2(tmp, finance_db_path())
        tmp.unlink(missing_ok=True)
        with db_session(finance_db_path()) as conn:
            conn.executescript(FINANCE_SCHEMA)
        self.audit.log("restore", new_value={"path": str(encrypted_path)}, source="desktop")

    def reset_application(self) -> Path:
        backup = self.encrypted_local_backup()
        self._replace_with_clean_database()
        self.audit.log("app_reset", new_value={"backup_path": str(backup)}, source="desktop")
        return backup

    def _replace_with_clean_database(self) -> None:
        db_path = finance_db_path()
        for path in (db_path, db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("Unable to remove database file during reset: %s", path)
                raise
        with db_session(db_path) as conn:
            conn.executescript(FINANCE_SCHEMA)
            conn.executemany(
                "INSERT OR IGNORE INTO categories(name, kind, color) VALUES (?, ?, ?)",
                DEFAULT_CATEGORIES,
            )
            conn.executemany(
                "INSERT OR IGNORE INTO accounts(name, kind, color) VALUES (?, ?, ?)",
                DEFAULT_ACCOUNTS,
            )

    def _looks_like_finance_db(self, path: Path) -> bool:
        import sqlite3

        conn = None
        try:
            conn = sqlite3.connect(path)
            names = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            return {"transactions", "categories", "user_settings"}.issubset(names)
        except sqlite3.DatabaseError:
            LOGGER.exception("Rejected invalid backup")
            return False
        finally:
            if conn is not None:
                conn.close()
