from __future__ import annotations

import logging
from tkinter import messagebox

from finance_app.analytics.engine import AnalyticsEngine
from finance_app.core.audit import AuditLogger
from finance_app.db.connection import DatabaseManager
from finance_app.db.repository import FinanceRepository
from finance_app.ocr.receipt_scanner import ReceiptScanner
from finance_app.reports.pdf_exporter import PDFExporter
from finance_app.security.encryption import EncryptionService
from finance_app.security.pin import PinAuthService
from finance_app.services.backup_service import BackupService
from finance_app.ui.dashboard import Dashboard
from finance_app.ui.login import LoginWindow


LOGGER = logging.getLogger(__name__)


class FinanceApplication:
    def __init__(self) -> None:
        self.db = DatabaseManager()
        self.db.initialize()
        self.repo = FinanceRepository()
        self.audit = AuditLogger()
        self.auth = PinAuthService(self.repo, self.audit)
        self.encryption = EncryptionService()
        self.analytics = AnalyticsEngine()
        self.backup = BackupService(self.encryption, self.audit)
        self.scanner = ReceiptScanner()
        self.exporter = PDFExporter(self.analytics)

    def run(self) -> None:
        try:
            if self.auth.should_require_login():
                login = LoginWindow(self.auth, self.backup)
                login.mainloop()
                if not login.authenticated:
                    return
            root = Dashboard(self.repo, self.audit, self.analytics, self.backup, self.scanner, self.exporter, self.auth)
            root.mainloop()
        except Exception as exc:  # noqa: BLE001 - final crash barrier.
            LOGGER.exception("Application recovered from fatal UI error")
            try:
                messagebox.showerror("TrackMint recovered", f"The app prevented a crash and shut down safely:\n{exc}")
            except Exception:
                pass
