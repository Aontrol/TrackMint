from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from finance_app.db.connection import db_session
from finance_app.utils.paths import audit_db_path


class AuditLogger:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or audit_db_path()

    def log(self, action_type: str, old_value: Any = None, new_value: Any = None, source: str = "desktop") -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        old_json = json.dumps(old_value, default=str, sort_keys=True) if old_value is not None else None
        new_json = json.dumps(new_value, default=str, sort_keys=True) if new_value is not None else None
        with db_session(self.db_path) as conn:
            previous = conn.execute("SELECT hash FROM audit_logs ORDER BY id DESC LIMIT 1").fetchone()
            previous_hash = previous["hash"] if previous else "GENESIS"
            digest = hashlib.sha256(
                f"{timestamp}|{action_type}|{old_json}|{new_json}|{source}|{previous_hash}".encode("utf-8")
            ).hexdigest()
            conn.execute(
                """
                INSERT INTO audit_logs(timestamp, action_type, old_value, new_value, source, hash, previous_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, action_type, old_json, new_json, source, digest, previous_hash),
            )
