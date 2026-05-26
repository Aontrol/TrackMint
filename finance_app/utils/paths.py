from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "TrackMint"


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def config_dir() -> Path:
    return app_data_dir() / "config"


def logs_dir() -> Path:
    return app_data_dir() / "logs"


def backup_dir() -> Path:
    return app_data_dir() / "backups"


def ensure_app_dirs() -> None:
    for path in (app_data_dir(), config_dir(), logs_dir(), backup_dir()):
        path.mkdir(parents=True, exist_ok=True)


def finance_db_path() -> Path:
    ensure_app_dirs()
    return app_data_dir() / "finance.db"


def audit_db_path() -> Path:
    ensure_app_dirs()
    return app_data_dir() / "audit_logs.db"


def key_file_path() -> Path:
    ensure_app_dirs()
    return config_dir() / "user_key.bin"
