from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Any

from finance_app.core.audit import AuditLogger
from finance_app.db.repository import FinanceRepository


class PinAuthService:
    SETTING_KEY = "local_pin_auth"
    ENABLED_KEY = "local_pin_enabled"
    ITERATIONS = 260_000

    def __init__(self, repo: FinanceRepository, audit: AuditLogger) -> None:
        self.repo = repo
        self.audit = audit

    def is_pin_configured(self) -> bool:
        return bool(self.repo.get_setting(self.SETTING_KEY))

    def is_pin_enabled(self) -> bool:
        return bool(self.repo.get_setting(self.ENABLED_KEY, self.is_pin_configured()))

    def should_require_login(self) -> bool:
        return self.is_pin_enabled()

    def enable_pin(self, pin: str) -> None:
        self.set_pin(pin)
        self.repo.upsert_setting(self.ENABLED_KEY, True)
        self.audit.log("pin_enabled", new_value={"enabled": True}, source="admin")

    def disable_pin(self) -> None:
        self.repo.upsert_setting(self.ENABLED_KEY, False)
        self.audit.log("pin_disabled", new_value={"enabled": False}, source="admin")

    def set_pin(self, pin: str) -> None:
        self._validate_pin_shape(pin)
        salt = os.urandom(16)
        digest = self._derive(pin, salt)
        self.repo.upsert_setting(
            self.SETTING_KEY,
            {
                "salt": base64.b64encode(salt).decode("ascii"),
                "digest": base64.b64encode(digest).decode("ascii"),
                "iterations": self.ITERATIONS,
            },
        )
        self.audit.log("pin_set", new_value={"configured": True}, source="local_login")

    def verify_pin(self, pin: str) -> bool:
        stored: dict[str, Any] | None = self.repo.get_setting(self.SETTING_KEY)
        if not stored:
            return False
        try:
            salt = base64.b64decode(stored["salt"])
            expected = base64.b64decode(stored["digest"])
            iterations = int(stored.get("iterations", self.ITERATIONS))
            actual = self._derive(pin, salt, iterations)
            ok = hmac.compare_digest(actual, expected)
        except Exception:  # noqa: BLE001
            ok = False
        self.audit.log("login", new_value={"status": "success" if ok else "failed"}, source="local_pin")
        return ok

    def _derive(self, pin: str, salt: bytes, iterations: int | None = None) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations or self.ITERATIONS)

    def _validate_pin_shape(self, pin: str) -> None:
        if not pin.isdigit() or len(pin) < 4 or len(pin) > 8:
            raise ValueError("PIN must be 4 to 8 digits")
