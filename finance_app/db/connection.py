from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from finance_app.db.schema import AUDIT_SCHEMA, DEFAULT_ACCOUNTS, DEFAULT_CATEGORIES, FINANCE_SCHEMA
from finance_app.utils.paths import audit_db_path, finance_db_path


LOGGER = logging.getLogger(__name__)


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def db_session(path: Path):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except sqlite3.DatabaseError:
        conn.rollback()
        LOGGER.exception("SQLite operation failed")
        raise
    finally:
        conn.close()


class DatabaseManager:
    def __init__(self) -> None:
        self.finance_path = finance_db_path()
        self.audit_path = audit_db_path()

    def initialize(self) -> None:
        self._repair_if_needed(self.finance_path)
        self._repair_if_needed(self.audit_path)
        with db_session(self.finance_path) as conn:
            self._migrate_payment_modes(conn)
            conn.executescript(FINANCE_SCHEMA)
            conn.executemany(
                "INSERT OR IGNORE INTO categories(name, kind, color) VALUES (?, ?, ?)",
                DEFAULT_CATEGORIES,
            )
            conn.executemany(
                "INSERT OR IGNORE INTO accounts(name, kind, color) VALUES (?, ?, ?)",
                DEFAULT_ACCOUNTS,
            )
        with db_session(self.audit_path) as conn:
            conn.executescript(AUDIT_SCHEMA)

    def _repair_if_needed(self, path: Path) -> None:
        try:
            with connect(path) as conn:
                conn.execute("PRAGMA quick_check").fetchone()
        except sqlite3.DatabaseError:
            LOGGER.exception("Database appears damaged, preserving copy and rebuilding: %s", path)
            damaged = path.with_suffix(path.suffix + ".damaged")
            try:
                path.replace(damaged)
            except OSError:
                LOGGER.exception("Unable to preserve damaged DB")

    def _migrate_payment_modes(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('transactions', 'balance_transfers')").fetchall()
        sql = " ".join(row["sql"] or "" for row in rows)
        if "payment_mode IN ('Cash', 'Online')" not in sql and "from_mode IN ('Cash', 'Online')" not in sql:
            return
        LOGGER.info("Migrating payment mode tables to account-based ledger")
        conn.executescript(
            """
            PRAGMA foreign_keys=OFF;

            ALTER TABLE transactions RENAME TO transactions_old;
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL CHECK(amount >= 0),
                category TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
                payment_mode TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                receipt_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO transactions(id, amount, category, type, payment_mode, timestamp, note, receipt_path, created_at)
            SELECT id, amount, category, type, payment_mode, timestamp, note, receipt_path, created_at FROM transactions_old;
            DROP TABLE transactions_old;

            ALTER TABLE balance_transfers RENAME TO balance_transfers_old;
            CREATE TABLE balance_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL CHECK(amount > 0),
                from_mode TEXT NOT NULL,
                to_mode TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK(from_mode <> to_mode)
            );
            INSERT INTO balance_transfers(id, amount, from_mode, to_mode, timestamp, note, created_at)
            SELECT id, amount, from_mode, to_mode, timestamp, note, created_at FROM balance_transfers_old;
            DROP TABLE balance_transfers_old;

            PRAGMA foreign_keys=ON;
            """
        )
