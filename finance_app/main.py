from __future__ import annotations

import logging
import sys
from pathlib import Path

from finance_app.core.app import FinanceApplication
from finance_app.utils.paths import ensure_app_dirs, logs_dir


def configure_logging() -> None:
    ensure_app_dirs()
    log_file = logs_dir() / "trackmint.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    configure_logging()
    app = FinanceApplication()
    app.run()


if __name__ == "__main__":
    main()
