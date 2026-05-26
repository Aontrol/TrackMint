from __future__ import annotations

import base64
import getpass
import hashlib
import logging
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from finance_app.utils.paths import key_file_path


LOGGER = logging.getLogger(__name__)


class EncryptionService:
    """Per-user Fernet encryption with locally obfuscated key-at-rest."""

    def __init__(self, key_path: Path | None = None) -> None:
        self.key_path = key_path or key_file_path()
        self._fernet = Fernet(self._load_or_create_key())

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        try:
            return self._fernet.decrypt(data)
        except InvalidToken as exc:
            raise ValueError("Encrypted payload failed integrity validation") from exc

    def encrypt_file(self, source: Path, destination: Path) -> None:
        destination.write_bytes(self.encrypt_bytes(source.read_bytes()))

    def decrypt_file(self, source: Path, destination: Path) -> None:
        destination.write_bytes(self.decrypt_bytes(source.read_bytes()))

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            try:
                return self._unprotect(self.key_path.read_bytes())
            except Exception:  # noqa: BLE001
                LOGGER.exception("Stored key unreadable, creating a new local key")
        key = Fernet.generate_key()
        self.key_path.write_bytes(self._protect(key))
        return key

    def _machine_secret(self) -> bytes:
        raw = f"{getpass.getuser()}::{self.key_path.parent}".encode("utf-8")
        digest = hashlib.sha256(raw).digest()
        return base64.urlsafe_b64encode(digest)

    def _protect(self, key: bytes) -> bytes:
        return Fernet(self._machine_secret()).encrypt(key)

    def _unprotect(self, protected: bytes) -> bytes:
        return Fernet(self._machine_secret()).decrypt(protected)
