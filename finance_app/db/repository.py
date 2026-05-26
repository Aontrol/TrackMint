from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from finance_app.db.connection import db_session
from finance_app.utils.paths import finance_db_path


class FinanceRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or finance_db_path()

    def add_transaction(self, data: dict[str, Any]) -> int:
        with db_session(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO transactions(amount, category, type, payment_mode, timestamp, note, receipt_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    float(data["amount"]),
                    data["category"],
                    data["type"],
                    data["payment_mode"],
                    data["timestamp"],
                    data.get("note", ""),
                    data.get("receipt_path"),
                ),
            )
            return int(cur.lastrowid)

    def get_transaction(self, transaction_id: int) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
            return dict(row) if row else None

    def update_transaction(self, transaction_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            old = conn.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
            if not old:
                return None
            conn.execute(
                """
                UPDATE transactions
                SET amount=?, category=?, type=?, payment_mode=?, timestamp=?, note=?, receipt_path=?
                WHERE id=?
                """,
                (
                    float(data["amount"]),
                    data["category"],
                    data["type"],
                    data["payment_mode"],
                    data["timestamp"],
                    data.get("note", ""),
                    data.get("receipt_path"),
                    transaction_id,
                ),
            )
            return dict(old)

    def delete_transaction(self, transaction_id: int) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
            if not row:
                return None
            conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            return dict(row)

    def list_transactions(self, limit: int = 500) -> list[dict[str, Any]]:
        with db_session(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY datetime(timestamp) DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_balance_transfer(self, data: dict[str, Any]) -> int:
        with db_session(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO balance_transfers(amount, from_mode, to_mode, timestamp, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    float(data["amount"]),
                    data["from_mode"],
                    data["to_mode"],
                    data["timestamp"],
                    data.get("note", ""),
                ),
            )
            return int(cur.lastrowid)

    def get_balance_transfer(self, transfer_id: int) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            row = conn.execute("SELECT * FROM balance_transfers WHERE id=?", (transfer_id,)).fetchone()
            return dict(row) if row else None

    def update_balance_transfer(self, transfer_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            old = conn.execute("SELECT * FROM balance_transfers WHERE id=?", (transfer_id,)).fetchone()
            if not old:
                return None
            conn.execute(
                """
                UPDATE balance_transfers
                SET amount=?, from_mode=?, to_mode=?, timestamp=?, note=?
                WHERE id=?
                """,
                (float(data["amount"]), data["from_mode"], data["to_mode"], data["timestamp"], data.get("note", ""), transfer_id),
            )
            return dict(old)

    def list_balance_transfers(self, limit: int = 500) -> list[dict[str, Any]]:
        with db_session(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM balance_transfers ORDER BY datetime(timestamp) DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def accounts(self, active_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM accounts"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY kind, name"
        with db_session(self.db_path) as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def add_account(self, name: str, kind: str = "Online", color: str = "#22d3ee") -> None:
        with db_session(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO accounts(name, kind, color) VALUES (?, ?, ?)",
                (name.strip(), kind, color),
            )

    def update_account(self, account_id: int, name: str, kind: str, color: str, is_active: bool = True) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            old = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
            if not old:
                return None
            old_name = old["name"]
            conn.execute(
                "UPDATE accounts SET name=?, kind=?, color=?, is_active=? WHERE id=?",
                (name.strip(), kind, color, 1 if is_active else 0, account_id),
            )
            if old_name != name.strip():
                conn.execute("UPDATE transactions SET payment_mode=? WHERE payment_mode=?", (name.strip(), old_name))
                conn.execute("UPDATE balance_transfers SET from_mode=? WHERE from_mode=?", (name.strip(), old_name))
                conn.execute("UPDATE balance_transfers SET to_mode=? WHERE to_mode=?", (name.strip(), old_name))
            return dict(old)

    def delete_account(self, account_id: int) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            old = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
            if not old:
                return None
            if old["name"] == "Cash":
                raise ValueError("Cash account cannot be deleted")
            used_txn = conn.execute("SELECT COUNT(*) FROM transactions WHERE payment_mode=?", (old["name"],)).fetchone()[0]
            used_from = conn.execute("SELECT COUNT(*) FROM balance_transfers WHERE from_mode=? OR to_mode=?", (old["name"], old["name"])).fetchone()[0]
            if used_txn or used_from:
                raise ValueError("Account has ledger activity and cannot be deleted")
            conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
            return dict(old)

    def categories(self) -> list[dict[str, Any]]:
        with db_session(self.db_path) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM categories ORDER BY kind, name").fetchall()]

    def add_category(self, name: str, kind: str, color: str) -> None:
        with db_session(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO categories(name, kind, color) VALUES (?, ?, ?)",
                (name.strip(), kind, color),
            )

    def update_category(self, category_id: int, name: str, kind: str, color: str) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            old = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
            if not old:
                return None
            conn.execute(
                "UPDATE categories SET name=?, kind=?, color=? WHERE id=?",
                (name.strip(), kind, color, category_id),
            )
            return dict(old)

    def delete_category(self, category_id: int) -> dict[str, Any] | None:
        with db_session(self.db_path) as conn:
            old = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
            if not old:
                return None
            in_use = conn.execute("SELECT COUNT(*) FROM transactions WHERE category=?", (old["name"],)).fetchone()[0]
            if in_use:
                raise ValueError("Category is used by transactions and cannot be deleted")
            conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
            return dict(old)

    def upsert_setting(self, key: str, value: Any) -> None:
        with db_session(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_settings(key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value)),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with db_session(self.db_path) as conn:
            row = conn.execute("SELECT value FROM user_settings WHERE key=?", (key,)).fetchone()
            if not row:
                return default
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return default

    def delete_setting(self, key: str) -> None:
        with db_session(self.db_path) as conn:
            conn.execute("DELETE FROM user_settings WHERE key=?", (key,))

    def add_loan(self, table: str, data: dict[str, Any]) -> int:
        if table not in {"loans_given", "loans_taken"}:
            raise ValueError("Invalid loan table")
        party_field = "counterparty" if table == "loans_given" else "lender"
        with db_session(self.db_path) as conn:
            cur = conn.execute(
                f"""
                INSERT INTO {table}({party_field}, principal, interest_rate, repaid, due_date, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data["party"],
                    float(data["principal"]),
                    float(data.get("interest_rate", 0)),
                    float(data.get("repaid", 0)),
                    data.get("due_date"),
                    data.get("note", ""),
                ),
            )
            return int(cur.lastrowid)

    def get_loan(self, table: str, loan_id: int) -> dict[str, Any] | None:
        if table not in {"loans_given", "loans_taken"}:
            raise ValueError("Invalid loan table")
        with db_session(self.db_path) as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (loan_id,)).fetchone()
            return dict(row) if row else None

    def update_loan(self, table: str, loan_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        if table not in {"loans_given", "loans_taken"}:
            raise ValueError("Invalid loan table")
        party_field = "counterparty" if table == "loans_given" else "lender"
        with db_session(self.db_path) as conn:
            old = conn.execute(f"SELECT * FROM {table} WHERE id=?", (loan_id,)).fetchone()
            if not old:
                return None
            conn.execute(
                f"""
                UPDATE {table}
                SET {party_field}=?, principal=?, interest_rate=?, repaid=?, due_date=?, note=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    data["party"],
                    float(data["principal"]),
                    float(data.get("interest_rate", 0)),
                    float(data.get("repaid", 0)),
                    data.get("due_date"),
                    data.get("note", ""),
                    loan_id,
                ),
            )
            return dict(old)

    def delete_loan(self, table: str, loan_id: int) -> dict[str, Any] | None:
        if table not in {"loans_given", "loans_taken"}:
            raise ValueError("Invalid loan table")
        with db_session(self.db_path) as conn:
            old = conn.execute(f"SELECT * FROM {table} WHERE id=?", (loan_id,)).fetchone()
            if not old:
                return None
            conn.execute(f"DELETE FROM {table} WHERE id=?", (loan_id,))
            return dict(old)

    def repay_loan(self, table: str, loan_id: int, amount: float) -> dict[str, Any] | None:
        if table not in {"loans_given", "loans_taken"}:
            raise ValueError("Invalid loan table")
        with db_session(self.db_path) as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (loan_id,)).fetchone()
            if not row:
                return None
            conn.execute(
                f"UPDATE {table} SET repaid=repaid+?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (float(amount), loan_id),
            )
            return dict(row)

    def list_loans(self, table: str) -> list[dict[str, Any]]:
        if table not in {"loans_given", "loans_taken"}:
            raise ValueError("Invalid loan table")
        with db_session(self.db_path) as conn:
            return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY due_date IS NULL, due_date").fetchall()]

    def seed_demo_if_empty(self) -> None:
        with db_session(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            if count:
                return
            now = datetime.now()
            sample = [
                (85000, "Salary", "Income", "Online", now.replace(day=1).isoformat(timespec="seconds"), "Monthly salary", None),
                (12000, "Rent", "Expense", "Online", now.replace(day=3).isoformat(timespec="seconds"), "Apartment rent", None),
                (5200, "Food", "Expense", "Cash", now.replace(day=5).isoformat(timespec="seconds"), "Groceries", None),
                (3600, "Transport", "Expense", "Online", now.replace(day=8).isoformat(timespec="seconds"), "Metro and cab", None),
                (9000, "Business", "Income", "Cash", now.replace(day=12).isoformat(timespec="seconds"), "Consulting", None),
            ]
            conn.executemany(
                "INSERT INTO transactions(amount, category, type, payment_mode, timestamp, note, receipt_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                sample,
            )
            conn.execute(
                "INSERT INTO balance_transfers(amount, from_mode, to_mode, timestamp, note) VALUES (?, ?, ?, ?, ?)",
                (2500, "Online", "Cash", now.replace(day=14).isoformat(timespec="seconds"), "ATM withdrawal"),
            )
