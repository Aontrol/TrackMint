from __future__ import annotations

import logging
import random
import tkinter as tk
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from finance_app.analytics.engine import AnalyticsEngine
from finance_app.core.audit import AuditLogger
from finance_app.core.finance_engine import compute_balances, loan_exposure, loan_remaining, monthly_profit_loss, savings_rate
from finance_app.db.repository import FinanceRepository
from finance_app.ocr.receipt_scanner import ReceiptScanner
from finance_app.reports.pdf_exporter import PDFExporter
from finance_app.security.pin import PinAuthService
from finance_app.services.backup_service import BackupService
from finance_app.ui.dialogs import AccountDialog, CategoryDialog, LoanDialog, RepaymentDialog, TransactionDialog, TransferDialog, ask_image, ask_report_path
from finance_app.ui.theme import BG, CYAN, GREEN, MUTED, PANEL, PANEL_2, PURPLE, RED, TEXT, YELLOW, apply_theme
from finance_app.utils.safe import safe_call


LOGGER = logging.getLogger(__name__)


class Dashboard(tk.Tk):
    def __init__(
        self,
        repo: FinanceRepository,
        audit: AuditLogger,
        analytics: AnalyticsEngine,
        backup_service: BackupService,
        scanner: ReceiptScanner,
        exporter: PDFExporter,
        auth: PinAuthService,
    ) -> None:
        super().__init__()
        apply_theme(self)
        self.repo = repo
        self.audit = audit
        self.analytics = analytics
        self.backup_service = backup_service
        self.scanner = scanner
        self.exporter = exporter
        self.auth = auth
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="trackmint")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.title("TrackMint Finance Workstation")
        self.geometry("1440x900")
        self.minsize(1180, 760)
        self._pulse = 0.0
        self._cards: dict[str, ttk.Label] = {}
        self._card_deltas: dict[str, ttk.Label] = {}
        self._chart_canvases: list[FigureCanvasTkAgg] = []
        self._pages: dict[str, ttk.Frame] = {}
        self._current_page = "Dashboard"
        self.month_filter = tk.StringVar(value="All Months")
        self.status_text = tk.StringVar(value="Ready")
        self.txn_form_vars = {
            "amount": tk.StringVar(),
            "category": tk.StringVar(value="Other"),
            "type": tk.StringVar(value="Expense"),
            "payment_mode": tk.StringVar(value="Cash"),
            "note": tk.StringVar(),
            "receipt_path": tk.StringVar(),
        }
        self.transfer_form_vars = {
            "amount": tk.StringVar(),
            "from_mode": tk.StringVar(value="Cash"),
            "to_mode": tk.StringVar(value="Online"),
            "note": tk.StringVar(),
        }
        self.admin_pin_enabled = tk.BooleanVar(value=self.auth.is_pin_enabled())
        self.admin_pin = tk.StringVar()
        self.admin_pin_confirm = tk.StringVar()
        self._build()
        self.refresh()
        self.after(6500, self._live_tick)
        self.after(50, self._show_front)

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_sidebar()
        self.workspace = ttk.Frame(self, padding=(18, 14))
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.columnconfigure(0, weight=1)
        self.workspace.rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_pages()

    def _show_front(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_sidebar(self) -> None:
        sidebar = ttk.Frame(self, padding=(14, 18), width=230, style="Sidebar.TFrame")
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="TrackMint", style="Sidebar.TLabel", font=("Segoe UI Semibold", 21), foreground=CYAN).pack(anchor="w")
        ttk.Label(sidebar, text="Finance Workstation", style="Sidebar.TLabel", foreground=MUTED).pack(anchor="w", pady=(0, 28))
        for page in ("Dashboard", "Transactions", "Balance", "Loans", "Admin"):
            ttk.Button(sidebar, text=page, style="Nav.TButton", command=lambda name=page: self.show_page(name)).pack(fill="x", pady=4)
        ttk.Frame(sidebar, height=1, style="Surface.TFrame").pack(fill="x", pady=22)
        #ttk.Label(sidebar, text="Developed By Abhirama Mankalale", style="Sidebar.TLabel", foreground=MUTED, wraplength=190).pack(anchor="w")
        ttk.Label(sidebar, textvariable=self.status_text, style="Sidebar.TLabel", foreground=GREEN, wraplength=190).pack(side="bottom", anchor="w", pady=(16, 0))

    def _build_topbar(self) -> None:
        topbar = ttk.Frame(self.workspace)
        topbar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        topbar.columnconfigure(0, weight=1)
        ttk.Label(topbar, text="Finance Overview", font=("Segoe UI Semibold", 19), foreground=TEXT).grid(row=0, column=0, sticky="w")
        ttk.Label(topbar, text=datetime.now().strftime("%A, %d %B %Y"), style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        actions = ttk.Frame(topbar)
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        for text, command, style in [
            ("Add Transaction", self.focus_transaction_entry, "TButton"),
            ("Manage Balance", lambda: self.show_page("Balance"), "TButton"),
            ("Scan Receipt", self.scan_receipt, "TButton"),
            ("Backup", self.backup_local, "TButton"),
            ("Restore", self.restore_backup, "TButton"),
            ("Export PDF", self.export_pdf, "TButton"),
        ]:
            ttk.Button(actions, text=text, style=style, command=command).pack(side="left", padx=4)

    def _build_pages(self) -> None:
        holder = ttk.Frame(self.workspace)
        holder.grid(row=1, column=0, sticky="nsew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        for name in ("Dashboard", "Transactions", "Balance", "Loans", "Admin"):
            page = ttk.Frame(holder)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[name] = page
        self._build_dashboard_page(self._pages["Dashboard"])
        self._build_transactions_page(self._pages["Transactions"])
        self._build_balance_page(self._pages["Balance"])
        self._build_loans_page(self._pages["Loans"])
        self._build_admin_page(self._pages["Admin"])
        self.show_page("Dashboard")

    def _build_dashboard_page(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=3)
        page.columnconfigure(1, weight=1)
        page.rowconfigure(2, weight=1)
        cards = ttk.Frame(page)
        cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for index in range(6):
            cards.columnconfigure(index, weight=1, uniform="cards")
        for index, title in enumerate(["Total Balance", "Cash Balance", "Online Balance", "Monthly P/L", "Loan Exposure", "Savings Rate"]):
            card = ttk.Frame(cards, padding=14, style="Panel.TFrame")
            card.grid(row=0, column=index, sticky="nsew", padx=5)
            ttk.Label(card, text=title.upper(), style="CardTitle.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="--", style="CardValue.TLabel")
            value.pack(anchor="w", pady=(8, 2))
            delta = ttk.Label(card, text="Updated", style="Tiny.TLabel")
            delta.pack(anchor="w")
            self._cards[title] = value
            self._card_deltas[title] = delta

        analytics_strip = ttk.Frame(page)
        analytics_strip.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        analytics_strip.columnconfigure((0, 1, 2, 3), weight=1, uniform="analytics")
        self.analysis_labels: dict[str, ttk.Label] = {}
        for idx, label in enumerate(["Total Income", "Total Expense", "Burn Rate", "Risk Score"]):
            box = ttk.Frame(analytics_strip, padding=12, style="Surface.TFrame")
            box.grid(row=0, column=idx, sticky="nsew", padx=5)
            ttk.Label(box, text=label, style="Surface.TLabel", foreground=MUTED).pack(anchor="w")
            value = ttk.Label(box, text="--", style="Surface.TLabel", font=("Segoe UI Semibold", 15))
            value.pack(anchor="w", pady=(6, 0))
            self.analysis_labels[label] = value

        charts = ttk.Frame(page)
        charts.grid(row=2, column=0, sticky="nsew")
        charts.columnconfigure((0, 1), weight=1)
        charts.rowconfigure((0, 1), weight=1)
        self.balance_fig = self._chart(charts, 0, 0)
        self.bar_fig = self._chart(charts, 0, 1)
        self.pie_fig = self._chart(charts, 1, 0)
        self.heat_fig = self._chart(charts, 1, 1)

        side = ttk.Frame(page, padding=14, style="Panel.TFrame")
        side.grid(row=2, column=1, sticky="nsew", padx=(12, 0))
        side.columnconfigure(0, weight=1)
        ttk.Label(side, text="Insights", style="Panel.TLabel", font=("Segoe UI Semibold", 14)).grid(row=0, column=0, sticky="w")
        self.insights = tk.Text(side, height=8, wrap="word", bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
        self.insights.grid(row=1, column=0, sticky="ew", pady=(10, 16))
        self.insights.configure(state="disabled")
        ttk.Label(side, text="Top Spending Categories", style="Panel.TLabel", foreground=MUTED).grid(row=2, column=0, sticky="w")
        self.category_tree = ttk.Treeview(side, columns=("category", "amount"), show="headings", height=6)
        self.category_tree.heading("category", text="Category")
        self.category_tree.heading("amount", text="Spend")
        self.category_tree.column("category", width=130)
        self.category_tree.column("amount", width=100, anchor="e")
        self.category_tree.grid(row=3, column=0, sticky="ew", pady=(8, 16))
        ttk.Label(side, text="Monthly Snapshot", style="Panel.TLabel", foreground=MUTED).grid(row=4, column=0, sticky="w")
        self.snapshot_tree = ttk.Treeview(side, columns=("metric", "value"), show="headings", height=5)
        self.snapshot_tree.heading("metric", text="Metric")
        self.snapshot_tree.heading("value", text="Value")
        self.snapshot_tree.column("metric", width=130)
        self.snapshot_tree.column("value", width=110, anchor="e")
        self.snapshot_tree.grid(row=5, column=0, sticky="ew", pady=(8, 0))

    def _build_transactions_page(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        page.rowconfigure(3, weight=1)
        header = ttk.Frame(page)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Transactions", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.month_combo = ttk.Combobox(header, textvariable=self.month_filter, state="readonly", width=18)
        self.month_combo.grid(row=0, column=2, sticky="e", padx=(10, 0))
        self.month_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        ttk.Button(header, text="Add", style="Accent.TButton", command=self.focus_transaction_entry).grid(row=0, column=3, padx=(8, 0))
        ttk.Button(header, text="Edit", command=self.edit_selected_transaction).grid(row=0, column=4, padx=(8, 0))
        ttk.Button(header, text="Delete", command=self.delete_selected_transaction).grid(row=0, column=5, padx=(8, 0))

        self.month_summary = ttk.Frame(page)
        self.month_summary.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.month_summary.columnconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform="month")
        self.month_summary_labels: dict[str, ttk.Label] = {}
        for idx, title in enumerate(["Income", "Expense", "Net", "Cash Net", "Online Net", "Savings Rate"]):
            card = ttk.Frame(self.month_summary, padding=12, style="Surface.TFrame")
            card.grid(row=0, column=idx, sticky="ew", padx=5)
            ttk.Label(card, text=title, style="Surface.TLabel", foreground=MUTED).pack(anchor="w")
            value = ttk.Label(card, text="--", style="Surface.TLabel", font=("Segoe UI Semibold", 14))
            value.pack(anchor="w", pady=(4, 0))
            self.month_summary_labels[title] = value

        entry = ttk.Frame(page, padding=12, style="Panel.TFrame")
        entry.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        entry.columnconfigure(1, weight=1)
        ttk.Label(entry, text="Quick Entry", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.amount_entry = ttk.Entry(entry, textvariable=self.txn_form_vars["amount"], width=14)
        self.amount_entry.grid(row=0, column=1, sticky="ew", padx=4)
        self.category_combo = ttk.Combobox(entry, textvariable=self.txn_form_vars["category"], state="readonly", width=16)
        self.category_combo.grid(row=0, column=2, padx=4)
        ttk.Combobox(entry, textvariable=self.txn_form_vars["type"], values=["Income", "Expense"], state="readonly", width=10).grid(row=0, column=3, padx=4)
        self.transaction_account_combo = ttk.Combobox(entry, textvariable=self.txn_form_vars["payment_mode"], state="readonly", width=16)
        self.transaction_account_combo.grid(row=0, column=4, padx=4)
        ttk.Entry(entry, textvariable=self.txn_form_vars["note"], width=24).grid(row=0, column=5, sticky="ew", padx=4)
        ttk.Button(entry, text="Save", style="Accent.TButton", command=self.save_inline_transaction).grid(row=0, column=6, padx=(8, 0))

        columns = ("timestamp", "type", "mode", "category", "amount", "note")
        self.txn_tree = ttk.Treeview(page, columns=columns, show="tree headings")
        self.txn_tree.heading("#0", text="Month")
        self.txn_tree.column("#0", width=150, anchor="w")
        for col in columns:
            self.txn_tree.heading(col, text=col.title())
            self.txn_tree.column(col, width=125 if col != "note" else 360, anchor="w")
        self.txn_tree.grid(row=3, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=self.txn_tree.yview)
        scrollbar.grid(row=3, column=1, sticky="ns")
        self.txn_tree.configure(yscrollcommand=scrollbar.set)
        ttk.Label(page, text="Select a transaction row to edit or delete.", style="Muted.TLabel").grid(row=4, column=0, sticky="w", pady=(8, 0))

    def _build_balance_page(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        page.columnconfigure(1, weight=2)
        page.rowconfigure(2, weight=1)
        ttk.Label(page, text="Balance Management", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        cards = ttk.Frame(page)
        cards.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        cards.columnconfigure((0, 1, 2), weight=1, uniform="balance")
        self.balance_labels: dict[str, ttk.Label] = {}
        for idx, title in enumerate(["Cash Balance", "Online Balance", "Total Balance"]):
            card = ttk.Frame(cards, padding=16, style="Panel.TFrame")
            card.grid(row=0, column=idx, sticky="ew", padx=5)
            ttk.Label(card, text=title.upper(), style="CardTitle.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="--", style="CardValue.TLabel")
            value.pack(anchor="w", pady=(8, 0))
            self.balance_labels[title] = value

        transfer = ttk.Frame(page, padding=16, style="Panel.TFrame")
        transfer.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        transfer.columnconfigure(1, weight=1)
        ttk.Label(transfer, text="Move Funds", style="Panel.TLabel", font=("Segoe UI Semibold", 13)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self.transfer_from_combo = ttk.Combobox(transfer, textvariable=self.transfer_form_vars["from_mode"], values=self._account_names(), state="readonly")
        self.transfer_to_combo = ttk.Combobox(transfer, textvariable=self.transfer_form_vars["to_mode"], values=self._account_names(), state="readonly")
        fields = [
            ("Amount", ttk.Entry(transfer, textvariable=self.transfer_form_vars["amount"])),
            ("From", self.transfer_from_combo),
            ("To", self.transfer_to_combo),
            ("Note", ttk.Entry(transfer, textvariable=self.transfer_form_vars["note"])),
        ]
        for row, (label, widget) in enumerate(fields, start=1):
            ttk.Label(transfer, text=label, style="Panel.TLabel", foreground=MUTED).grid(row=row, column=0, sticky="w", pady=7)
            widget.grid(row=row, column=1, sticky="ew", pady=7, padx=(12, 0))
        ttk.Button(transfer, text="Record Transfer", style="Accent.TButton", command=self.save_balance_transfer).grid(row=5, column=1, sticky="e", pady=(14, 0))
        ttk.Label(
            transfer,
            text="Transfers adjust Cash and Online balances without changing total wealth, income, or expenses.",
            style="Panel.TLabel",
            foreground=MUTED,
            wraplength=330,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(18, 0))

        history_frame = ttk.Frame(page, padding=12, style="Panel.TFrame")
        history_frame.grid(row=2, column=1, sticky="nsew")
        history_frame.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)
        ttk.Label(history_frame, text="Transfer Ledger", style="Panel.TLabel", font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.transfer_tree = ttk.Treeview(history_frame, columns=("timestamp", "from", "to", "amount", "note"), show="headings")
        for col in self.transfer_tree["columns"]:
            self.transfer_tree.heading(col, text=col.title())
            self.transfer_tree.column(col, width=130 if col != "note" else 260, anchor="w")
        self.transfer_tree.grid(row=1, column=0, sticky="nsew")
        ttk.Button(history_frame, text="Edit Selected Transfer", command=self.edit_selected_transfer).grid(row=2, column=0, sticky="w", pady=(10, 0))

        account_frame = ttk.Frame(page, padding=12, style="Panel.TFrame")
        account_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        account_frame.columnconfigure(0, weight=1)
        ttk.Label(account_frame, text="Account Balances", style="Panel.TLabel", font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.account_balance_tree = ttk.Treeview(account_frame, columns=("account", "type", "balance"), show="headings", height=5)
        for col, title in {"account": "Account", "type": "Type", "balance": "Balance"}.items():
            self.account_balance_tree.heading(col, text=title)
            self.account_balance_tree.column(col, width=180, anchor="w")
        self.account_balance_tree.grid(row=1, column=0, sticky="ew")

    def _build_loans_page(self, page: ttk.Frame) -> None:
        page.rowconfigure(1, weight=1)
        page.columnconfigure((0, 1), weight=1)
        controls = ttk.Frame(page)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(controls, text="Loan Book", style="Section.TLabel").pack(side="left")
        ttk.Button(controls, text="Add Loan Given", command=lambda: LoanDialog(self, "loans_given", self.save_loan)).pack(side="right", padx=5)
        ttk.Button(controls, text="Add Loan Taken", command=lambda: LoanDialog(self, "loans_taken", self.save_loan)).pack(side="right", padx=5)
        self.loan_trees: dict[str, ttk.Treeview] = {}
        for idx, (table, title) in enumerate([("loans_given", "Loans Given"), ("loans_taken", "Loans Taken")]):
            frame = ttk.Frame(page, padding=12, style="Panel.TFrame")
            frame.grid(row=1, column=idx, sticky="nsew", padx=6)
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)
            panel_header = ttk.Frame(frame, style="Panel.TFrame")
            panel_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            panel_header.columnconfigure(0, weight=1)
            ttk.Label(panel_header, text=title, style="Panel.TLabel", font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
            ttk.Button(panel_header, text="Edit", command=lambda t=table: self.edit_selected_loan(t)).grid(row=0, column=1, padx=(8, 0))
            ttk.Button(panel_header, text="Payment", command=lambda t=table: self.record_selected_loan_payment(t)).grid(row=0, column=2, padx=(8, 0))
            ttk.Button(panel_header, text="Delete", command=lambda t=table: self.delete_selected_loan(t)).grid(row=0, column=3, padx=(8, 0))
            tree = ttk.Treeview(frame, columns=("party", "principal", "rate", "repaid", "due", "remaining"), show="headings")
            widths = {"party": 180, "principal": 115, "rate": 80, "repaid": 115, "due": 120, "remaining": 125}
            headings = {"party": "Party", "principal": "Principal", "rate": "Rate", "repaid": "Paid", "due": "Due Date", "remaining": "Remaining"}
            for col in tree["columns"]:
                tree.heading(col, text=headings[col])
                tree.column(col, width=widths[col], anchor="w", stretch=True)
            tree.grid(row=1, column=0, sticky="nsew")
            yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            yscroll.grid(row=1, column=1, sticky="ns")
            tree.configure(yscrollcommand=yscroll.set)
            self.loan_trees[table] = tree

    def _build_admin_page(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        page.columnconfigure(1, weight=2)
        page.rowconfigure(1, weight=1)
        header = ttk.Frame(page)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Admin Panel", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Add Category", style="TButton", command=self.add_category_dialog).grid(row=0, column=1, sticky="e")
        ttk.Button(header, text="Add Account", command=self.add_account_dialog).grid(row=0, column=2, sticky="e", padx=(8, 0))

        security = ttk.Frame(page, padding=16, style="Panel.TFrame")
        security.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        security.columnconfigure(1, weight=1)
        ttk.Label(security, text="Access Control", style="Panel.TLabel", font=("Segoe UI Semibold", 14)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Checkbutton(security, text="Require PIN on startup", variable=self.admin_pin_enabled, command=self.apply_pin_setting).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(security, text="New PIN", style="Panel.TLabel", foreground=MUTED).grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(security, textvariable=self.admin_pin, show="*", justify="center").grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=6)
        ttk.Label(security, text="Confirm PIN", style="Panel.TLabel", foreground=MUTED).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(security, textvariable=self.admin_pin_confirm, show="*", justify="center").grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=6)
        ttk.Button(security, text="Save PIN", style="Accent.TButton", command=self.save_admin_pin).grid(row=4, column=1, sticky="e", pady=(12, 0))
        ttk.Label(
            security,
            text="PIN protection is optional. When enabled, the app asks for the local PIN before opening.",
            style="Panel.TLabel",
            foreground=MUTED,
            wraplength=330,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(18, 0))

        reset_panel = ttk.Frame(security, padding=(0, 20, 0, 0), style="Panel.TFrame")
        reset_panel.grid(row=6, column=0, columnspan=2, sticky="ew")
        reset_panel.columnconfigure(0, weight=1)
        ttk.Label(reset_panel, text="Reset Application", style="Panel.TLabel", font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
        ttk.Label(
            reset_panel,
            text="Create an encrypted backup, then clear all local finance data and PIN settings.",
            style="Panel.TLabel",
            foreground=MUTED,
            wraplength=330,
        ).grid(row=1, column=0, sticky="w", pady=(6, 10))
        ttk.Button(reset_panel, text="Backup and Reset", command=self.reset_application).grid(row=2, column=0, sticky="ew")

        style = ttk.Style()
        style.configure("Developer.TLabel", foreground="red")

        ttk.Label(
            page,
            text="Developer : Abhirama Mankalale",
            style="Developer.TLabel",
        ).grid(row=2, column=0, columnspan=2, sticky="sw", pady=(20, 5), padx=10)

        right = ttk.Frame(page)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        page.rowconfigure(2, weight=0)

        accounts = ttk.Frame(right, padding=12, style="Panel.TFrame")
        accounts.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        accounts.rowconfigure(1, weight=1)
        accounts.columnconfigure(0, weight=1)
        ttk.Label(accounts, text="Accounts", style="Panel.TLabel", font=("Segoe UI Semibold", 14)).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.account_manage_tree = ttk.Treeview(accounts, columns=("name", "kind", "color"), show="headings")
        for col, title in {"name": "Account", "kind": "Type", "color": "Color"}.items():
            self.account_manage_tree.heading(col, text=title)
            self.account_manage_tree.column(col, width=160, anchor="w", stretch=True)
        self.account_manage_tree.grid(row=1, column=0, sticky="nsew")
        account_footer = ttk.Frame(accounts, padding=(0, 10), style="Panel.TFrame")
        account_footer.grid(row=2, column=0, sticky="ew")
        ttk.Button(account_footer, text="Edit Selected", command=self.edit_selected_account).pack(side="left")
        ttk.Button(account_footer, text="Delete Selected", command=self.delete_selected_account).pack(side="left", padx=8)

        categories = ttk.Frame(right, padding=12, style="Panel.TFrame")
        categories.grid(row=1, column=0, sticky="nsew")
        categories.rowconfigure(1, weight=1)
        categories.columnconfigure(0, weight=1)
        ttk.Label(categories, text="Categories", style="Panel.TLabel", font=("Segoe UI Semibold", 14)).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.category_manage_tree = ttk.Treeview(categories, columns=("name", "kind", "color"), show="headings")
        headings = {"name": "Category", "kind": "Type", "color": "Color"}
        widths = {"name": 280, "kind": 140, "color": 120}
        for col in self.category_manage_tree["columns"]:
            self.category_manage_tree.heading(col, text=headings[col])
            self.category_manage_tree.column(col, width=widths[col], anchor="w", stretch=True)
        self.category_manage_tree.grid(row=1, column=0, sticky="nsew")
        footer = ttk.Frame(categories, padding=(0, 12), style="Panel.TFrame")
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Button(footer, text="Edit Selected", command=self.edit_selected_category).pack(side="left")
        ttk.Button(footer, text="Delete Selected", command=self.delete_selected_category).pack(side="left", padx=8)

    def _account_names(self) -> list[str]:
        names = [account["name"] for account in self.repo.accounts()]
        return names or ["Cash"]

    def show_page(self, page_name: str) -> None:
        self._current_page = page_name
        self._pages[page_name].tkraise()

    def _chart(self, parent, row: int, col: int) -> Figure:
        fig = Figure(figsize=(5.2, 3.0), dpi=100, facecolor=PANEL)
        fig.subplots_adjust(left=0.12, right=0.96, top=0.86, bottom=0.2)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        self._chart_canvases.append(canvas)
        return fig

    @safe_call(alert=True)
    def refresh(self) -> None:
        transactions = self.repo.list_transactions()
        transfers = self.repo.list_balance_transfers()
        loans_given = self.repo.list_loans("loans_given")
        loans_taken = self.repo.list_loans("loans_taken")
        self._update_month_options(transactions)
        self._update_category_options()
        self._update_account_options()
        balances = compute_balances(transactions, transfers)
        summary = self.analytics.summary(transactions, loans_given, loans_taken)
        self._cards["Total Balance"].configure(text=self._money(balances["total"]))
        self._cards["Cash Balance"].configure(text=self._money(balances["cash"]))
        self._cards["Online Balance"].configure(text=self._money(balances["online"]))
        self._cards["Monthly P/L"].configure(text=self._money(monthly_profit_loss(transactions)))
        self._cards["Loan Exposure"].configure(text=self._money(loan_exposure(loans_given, loans_taken)))
        self._cards["Savings Rate"].configure(text=f"{savings_rate(transactions):.1f}%")
        self._card_deltas["Total Balance"].configure(text="Cash + Online")
        self._card_deltas["Cash Balance"].configure(text="Cash ledger")
        self._card_deltas["Online Balance"].configure(text="Online ledger")
        self._card_deltas["Monthly P/L"].configure(text="Current month")
        self._card_deltas["Loan Exposure"].configure(text="Open loans")
        self._card_deltas["Savings Rate"].configure(text="Current month")
        self.analysis_labels["Total Income"].configure(text=self._money(summary["total_income"]))
        self.analysis_labels["Total Expense"].configure(text=self._money(summary["total_expense"]))
        self.analysis_labels["Burn Rate"].configure(text=self._money(summary["burn_rate"]))
        self.analysis_labels["Risk Score"].configure(text=f"{summary['risk_score']} / 100")
        self._render_insights(transactions, loans_given, loans_taken)
        self._render_charts(transactions, transfers)
        self._render_transactions(transactions, transfers)
        self._render_balance(balances, transfers)
        self._render_loans(loans_given, loans_taken)
        self._render_categories()
        self._render_accounts(balances)
        self.status_text.set(f"Last refresh {datetime.now().strftime('%H:%M:%S')}")

    def _update_month_options(self, transactions: list[dict[str, Any]]) -> None:
        options = self.analytics.month_options(transactions)
        self.month_combo.configure(values=options)
        if self.month_filter.get() not in options:
            self.month_filter.set(options[0])

    def _update_category_options(self) -> None:
        categories = [category["name"] for category in self.repo.categories()]
        self.category_combo.configure(values=categories)
        if self.txn_form_vars["category"].get() not in categories and categories:
            self.txn_form_vars["category"].set(categories[0])
        self.admin_pin_enabled.set(self.auth.is_pin_enabled())

    def _update_account_options(self) -> None:
        accounts = self._account_names()
        self.transaction_account_combo.configure(values=accounts)
        self.transfer_from_combo.configure(values=accounts)
        self.transfer_to_combo.configure(values=accounts)
        if self.txn_form_vars["payment_mode"].get() not in accounts:
            self.txn_form_vars["payment_mode"].set(accounts[0])
        if self.transfer_form_vars["from_mode"].get() not in accounts:
            self.transfer_form_vars["from_mode"].set(accounts[0])
        if self.transfer_form_vars["to_mode"].get() not in accounts:
            self.transfer_form_vars["to_mode"].set(accounts[min(1, len(accounts) - 1)])

    def _render_insights(self, transactions: list[dict[str, Any]], loans_given: list[dict[str, Any]], loans_taken: list[dict[str, Any]]) -> None:
        self.insights.configure(state="normal")
        self.insights.delete("1.0", "end")
        for line in self.analytics.insight_lines(transactions, loans_given, loans_taken):
            self.insights.insert("end", f"- {line}\n")
        self.insights.configure(state="disabled")
        self.category_tree.delete(*self.category_tree.get_children())
        for category, amount in self.analytics.top_spending_categories(transactions):
            self.category_tree.insert("", "end", values=(category, self._money(amount)))
        self.snapshot_tree.delete(*self.snapshot_tree.get_children())
        snap = self.analytics.monthly_snapshot(transactions, datetime.now().strftime("%Y-%m"))
        for metric, value in [
            ("Income", self._money(snap["income"])),
            ("Expense", self._money(snap["expense"])),
            ("Net Savings", self._money(snap["net"])),
            ("Savings Rate", f"{snap['savings_rate']:.1f}%"),
            ("Volatility", self._money(self.analytics.cashflow_volatility(transactions))),
        ]:
            self.snapshot_tree.insert("", "end", values=(metric, value))

    def _render_charts(self, transactions: list[dict[str, Any]], transfers: list[dict[str, Any]]) -> None:
        for fig in (self.balance_fig, self.bar_fig, self.pie_fig, self.heat_fig):
            fig.clear()
        labels, values = self.analytics.balance_series(transactions)
        ax = self.balance_fig.add_subplot(111)
        self._style_ax(ax, "Net Worth Trend")
        if values:
            live = values[-1] + random.uniform(-180, 180) * self._pulse
            ax.plot(labels, values[:-1] + [live], color=CYAN, linewidth=2.4)
            ax.fill_between(labels, values[:-1] + [live], color=CYAN, alpha=0.11)
            ax.tick_params(axis="x", rotation=35)

        months, income, expense = self.analytics.income_expense_by_month(transactions)
        ax = self.bar_fig.add_subplot(111)
        self._style_ax(ax, "Monthly Income vs Expense")
        x = range(len(months))
        ax.bar([i - 0.18 for i in x], income, width=0.35, color=GREEN, label="Income")
        ax.bar([i + 0.18 for i in x], expense, width=0.35, color=RED, label="Expense")
        ax.set_xticks(list(x), months)
        ax.legend(facecolor=PANEL, edgecolor=PANEL_2, labelcolor=TEXT, fontsize=8)

        split = compute_balances(transactions, transfers)
        ax = self.pie_fig.add_subplot(111)
        ax.set_title("Liquidity Split", color=TEXT, fontsize=11)
        vals = [max(0.0, split["cash"]), max(0.0, split["online"])]
        if sum(vals) > 0:
            ax.pie(vals, labels=["Cash", "Online"], colors=[PURPLE, CYAN], textprops={"color": TEXT, "fontsize": 8}, autopct="%1.0f%%")
        ax.set_facecolor(PANEL)

        months, categories, matrix = self.analytics.category_heat(transactions)
        ax = self.heat_fig.add_subplot(111)
        self._style_ax(ax, "Spending Concentration")
        image = ax.imshow(matrix, cmap="magma", aspect="auto")
        ax.set_xticks(range(len(months)), months)
        ax.set_yticks(range(len(categories)), categories)
        image.set_clim(vmin=0)

        for canvas in self._chart_canvases:
            canvas.draw_idle()

    def _style_ax(self, ax, title: str) -> None:
        ax.set_facecolor(PANEL)
        ax.set_title(title, color=TEXT, fontsize=11)
        ax.tick_params(colors=MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#243047")
        ax.grid(True, color="#1f2937", linewidth=0.6, alpha=0.9)

    def _render_transactions(self, transactions: list[dict[str, Any]], transfers: list[dict[str, Any]]) -> None:
        scoped = self.analytics.filter_month(transactions, self.month_filter.get())
        scoped_transfers = self._filter_transfers_by_month(transfers, self.month_filter.get())
        snap = self.analytics.monthly_snapshot(transactions, self.month_filter.get())
        balance_snap = compute_balances(scoped, scoped_transfers)
        self.month_summary_labels["Income"].configure(text=self._money(snap["income"]))
        self.month_summary_labels["Expense"].configure(text=self._money(snap["expense"]))
        self.month_summary_labels["Net"].configure(text=self._money(snap["net"]))
        self.month_summary_labels["Cash Net"].configure(text=self._money(balance_snap["cash"]))
        self.month_summary_labels["Online Net"].configure(text=self._money(balance_snap["online"]))
        self.month_summary_labels["Savings Rate"].configure(text=f"{snap['savings_rate']:.1f}%")
        self.txn_tree.delete(*self.txn_tree.get_children())
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for txn in scoped:
            groups[datetime.fromisoformat(txn["timestamp"]).strftime("%B %Y")].append(txn)
        for month in sorted(groups, key=lambda m: datetime.strptime(m, "%B %Y"), reverse=True):
            rows = groups[month]
            income = sum(t["amount"] for t in rows if t["type"] == "Income")
            expense = sum(t["amount"] for t in rows if t["type"] == "Expense")
            parent = self.txn_tree.insert("", "end", text=month, values=("", "", "", "", self._money(income - expense), f"{len(rows)} entries"), open=True)
            for txn in rows:
                self.txn_tree.insert(
                    parent,
                    "end",
                    iid=f"txn-{txn['id']}",
                    text="",
                    values=(txn["timestamp"], txn["type"], txn["payment_mode"], txn["category"], self._money(txn["amount"]), txn["note"]),
                )

    def _filter_transfers_by_month(self, transfers: list[dict[str, Any]], month: str) -> list[dict[str, Any]]:
        if not month or month == "All Months":
            return transfers
        return [t for t in transfers if datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") == month]

    def _render_balance(self, balances: dict[str, float], transfers: list[dict[str, Any]]) -> None:
        self.balance_labels["Cash Balance"].configure(text=self._money(balances["cash"]))
        self.balance_labels["Online Balance"].configure(text=self._money(balances["online"]))
        self.balance_labels["Total Balance"].configure(text=self._money(balances["total"]))
        self.transfer_tree.delete(*self.transfer_tree.get_children())
        for transfer in transfers[:250]:
            self.transfer_tree.insert(
                "",
                "end",
                iid=f"transfer-{transfer['id']}",
                values=(
                    transfer["timestamp"],
                    transfer["from_mode"],
                    transfer["to_mode"],
                    self._money(transfer["amount"]),
                    transfer["note"],
                ),
            )

    def _render_accounts(self, balances: dict[str, Any]) -> None:
        if hasattr(self, "account_balance_tree"):
            self.account_balance_tree.delete(*self.account_balance_tree.get_children())
            account_balances = balances.get("accounts", {})
            for account in self.repo.accounts():
                self.account_balance_tree.insert("", "end", values=(account["name"], account["kind"], self._money(account_balances.get(account["name"], 0.0))))
        self.account_manage_tree.delete(*self.account_manage_tree.get_children())
        for account in self.repo.accounts(active_only=False):
            tag = f"account-color-{account['id']}"
            self.account_manage_tree.tag_configure(tag, foreground=account["color"])
            self.account_manage_tree.insert("", "end", iid=f"account-{account['id']}", values=(account["name"], account["kind"], "Selected"), tags=(tag,))

    def _render_loans(self, loans_given: list[dict[str, Any]], loans_taken: list[dict[str, Any]]) -> None:
        for table, rows in [("loans_given", loans_given), ("loans_taken", loans_taken)]:
            tree = self.loan_trees[table]
            tree.delete(*tree.get_children())
            for loan in rows:
                party = loan.get("counterparty") or loan.get("lender")
                tree.insert("", "end", iid=f"{table}-{loan['id']}", values=(party, self._money(loan["principal"]), f"{loan['interest_rate']}%", self._money(loan["repaid"]), loan.get("due_date") or "-", self._money(loan_remaining(loan))))

    def _render_categories(self) -> None:
        self.category_manage_tree.delete(*self.category_manage_tree.get_children())
        for category in self.repo.categories():
            tag = f"category-color-{category['id']}"
            self.category_manage_tree.tag_configure(tag, foreground=category["color"])
            self.category_manage_tree.insert("", "end", iid=f"category-{category['id']}", values=(category["name"], category["kind"], "Selected"), tags=(tag,))

    def _live_tick(self) -> None:
        self._pulse = 1.0 - self._pulse
        self.refresh()
        self.after(6500, self._live_tick)

    def focus_transaction_entry(self) -> None:
        self.show_page("Transactions")
        self.amount_entry.focus_set()

    def open_transaction_dialog(self, defaults: dict[str, Any] | None = None) -> None:
        defaults = defaults or {}
        for key, var in self.txn_form_vars.items():
            if key in defaults:
                var.set(str(defaults[key]))
        self.focus_transaction_entry()

    def _selected_transaction_id(self) -> int | None:
        selected = self.txn_tree.selection()
        if not selected:
            return None
        item_id = selected[0]
        if not item_id.startswith("txn-"):
            messagebox.showinfo("Select a transaction", "Choose an individual transaction row, not a month group.")
            return None
        return int(item_id.replace("txn-", ""))

    @safe_call(alert=True)
    def save_inline_transaction(self) -> None:
        try:
            amount = float(self.txn_form_vars["amount"].get())
            if amount < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid transaction", "Enter a valid positive amount.")
            return
        data = {
            "amount": amount,
            "category": self.txn_form_vars["category"].get(),
            "type": self.txn_form_vars["type"].get(),
            "payment_mode": self.txn_form_vars["payment_mode"].get(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "note": self.txn_form_vars["note"].get(),
            "receipt_path": self.txn_form_vars["receipt_path"].get() or None,
        }
        self.save_transaction(data)
        self.txn_form_vars["amount"].set("")
        self.txn_form_vars["note"].set("")
        self.txn_form_vars["receipt_path"].set("")
        self.amount_entry.focus_set()

    @safe_call(alert=True)
    def save_balance_transfer(self) -> None:
        try:
            amount = float(self.transfer_form_vars["amount"].get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid transfer", "Enter a valid positive amount.")
            return
        from_mode = self.transfer_form_vars["from_mode"].get()
        to_mode = self.transfer_form_vars["to_mode"].get()
        if from_mode == to_mode:
            messagebox.showwarning("Invalid transfer", "Cash and Online transfer sides must be different.")
            return
        balances = compute_balances(self.repo.list_transactions(), self.repo.list_balance_transfers())
        available = balances.get("accounts", {}).get(from_mode, 0.0)
        if amount > available:
            messagebox.showwarning("Insufficient balance", f"{from_mode} balance is only {self._money(available)}.")
            return
        data = {
            "amount": amount,
            "from_mode": from_mode,
            "to_mode": to_mode,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "note": self.transfer_form_vars["note"].get(),
        }
        transfer_id = self.repo.add_balance_transfer(data)
        self.audit.log("balance_transfer", new_value={**data, "id": transfer_id}, source="desktop")
        self.transfer_form_vars["amount"].set("")
        self.transfer_form_vars["note"].set("")
        self.refresh()

    @safe_call(alert=True)
    def save_transaction(self, data: dict[str, Any]) -> None:
        txn_id = self.repo.add_transaction(data)
        self.audit.log("add_transaction", new_value={**data, "id": txn_id}, source="desktop")
        self.refresh()

    @safe_call(alert=True)
    def delete_selected_transaction(self) -> None:
        txn_id = self._selected_transaction_id()
        if txn_id is None:
            return
        old = self.repo.delete_transaction(txn_id)
        if old:
            self.audit.log("delete_transaction", old_value=old, source="desktop")
        self.refresh()

    def edit_selected_transaction(self) -> None:
        txn_id = self._selected_transaction_id()
        if txn_id is None:
            return
        current = self.repo.get_transaction(txn_id)
        if not current:
            return

        def save(data: dict[str, Any]) -> None:
            old = self.repo.update_transaction(txn_id, data)
            self.audit.log("edit_transaction", old_value=old, new_value={**data, "id": txn_id}, source="desktop")
            self.refresh()

        TransactionDialog(self, self.repo.categories(), save, current, self._account_names())

    @safe_call(alert=True)
    def save_loan(self, table: str, data: dict[str, Any]) -> None:
        loan_id = self.repo.add_loan(table, data)
        self.audit.log("loan_changes", new_value={**data, "id": loan_id, "table": table}, source="desktop")
        self.refresh()

    def _selected_loan_id(self, table: str) -> int | None:
        selected = self.loan_trees[table].selection()
        if not selected:
            messagebox.showinfo("Select a loan", "Choose a loan row first.")
            return None
        item_id = str(selected[0])
        return int(item_id.replace(f"{table}-", ""))

    def edit_selected_loan(self, table: str) -> None:
        loan_id = self._selected_loan_id(table)
        if loan_id is None:
            return
        current = self.repo.get_loan(table, loan_id)
        if not current:
            return
        current["party"] = current.get("counterparty") or current.get("lender") or ""

        def save(mode: str, data: dict[str, Any]) -> None:
            old = self.repo.update_loan(mode, loan_id, data)
            self.audit.log("edit_loan", old_value=old, new_value={**data, "id": loan_id, "table": mode}, source="desktop")
            self.refresh()

        LoanDialog(self, table, save, current)

    def record_selected_loan_payment(self, table: str) -> None:
        loan_id = self._selected_loan_id(table)
        if loan_id is None:
            return

        def save(payment: dict[str, Any]) -> None:
            amount = payment["amount"]
            old = self.repo.repay_loan(table, loan_id, amount)
            category = "Loan Recovery" if table == "loans_given" else "Loan Repayment"
            txn_type = "Income" if table == "loans_given" else "Expense"
            self.repo.add_category(category, txn_type, "#22c55e" if txn_type == "Income" else "#f87171")
            txn = {
                "amount": amount,
                "category": category,
                "type": txn_type,
                "payment_mode": payment["payment_mode"],
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "note": payment.get("note") or f"{category} for loan #{loan_id}",
                "receipt_path": None,
            }
            txn_id = self.repo.add_transaction(txn)
            self.audit.log(
                "loan_payment",
                old_value=old,
                new_value={"id": loan_id, "table": table, "amount": amount, "transaction_id": txn_id, "payment_mode": payment["payment_mode"]},
                source="desktop",
            )
            self.refresh()

        RepaymentDialog(self, save, self._account_names())

    def delete_selected_loan(self, table: str) -> None:
        loan_id = self._selected_loan_id(table)
        if loan_id is None:
            return
        if not messagebox.askyesno("Delete loan", "Delete the selected loan record?"):
            return
        old = self.repo.delete_loan(table, loan_id)
        self.audit.log("delete_loan", old_value=old, source="desktop")
        self.refresh()

    def add_category_dialog(self) -> None:
        def save(data: dict[str, Any]) -> None:
            self.repo.add_category(data["name"], data["kind"], data["color"])
            self.audit.log("category_add", new_value=data, source="desktop")
            self.refresh()

        CategoryDialog(self, save)

    def apply_pin_setting(self) -> None:
        if self.admin_pin_enabled.get():
            if self.auth.is_pin_configured():
                self.repo.upsert_setting(self.auth.ENABLED_KEY, True)
                self.audit.log("pin_enabled", new_value={"enabled": True}, source="admin")
                self.status_text.set("PIN enabled")
                return
            messagebox.showinfo("Create PIN", "Enter and confirm a PIN, then choose Save PIN.")
            self.admin_pin_enabled.set(False)
            return
        self.auth.disable_pin()
        self.status_text.set("PIN disabled")

    def save_admin_pin(self) -> None:
        pin = self.admin_pin.get().strip()
        confirm = self.admin_pin_confirm.get().strip()
        if pin != confirm:
            messagebox.showwarning("PIN mismatch", "The PIN confirmation does not match.")
            return
        try:
            self.auth.enable_pin(pin)
        except ValueError as exc:
            messagebox.showwarning("Invalid PIN", str(exc))
            return
        self.admin_pin.set("")
        self.admin_pin_confirm.set("")
        self.admin_pin_enabled.set(True)
        self.status_text.set("PIN updated")
        messagebox.showinfo("PIN saved", "PIN protection is enabled for the next launch.")

    def reset_application(self) -> None:
        if not messagebox.askyesno(
            "Backup and reset",
            "TrackMint will create an encrypted backup, then clear all local finance data and PIN settings. Continue?",
        ):
            return
        confirm = simpledialog.askstring("Confirm reset", "Type RESET to continue:", parent=self)
        if confirm != "RESET":
            return

        def done(backup: Path) -> None:
            self.admin_pin.set("")
            self.admin_pin_confirm.set("")
            self.admin_pin_enabled.set(False)
            self.refresh()
            self.show_page("Dashboard")
            messagebox.showinfo("Reset complete", f"Encrypted backup created before reset:\n{backup}")

        self._run_background("Reset", self.backup_service.reset_application, done)

    def edit_selected_category(self) -> None:
        selected = self.category_manage_tree.selection()
        if not selected:
            return
        category_id = int(str(selected[0]).replace("category-", ""))
        categories = {category["id"]: category for category in self.repo.categories()}
        current = categories.get(category_id)
        if not current:
            return

        def save(data: dict[str, Any]) -> None:
            old = self.repo.update_category(category_id, data["name"], data["kind"], data["color"])
            self.audit.log("category_edit", old_value=old, new_value={**data, "id": category_id}, source="desktop")
            self.refresh()

        CategoryDialog(self, save, current)

    def delete_selected_category(self) -> None:
        selected = self.category_manage_tree.selection()
        if not selected:
            return
        category_id = int(str(selected[0]).replace("category-", ""))
        try:
            old = self.repo.delete_category(category_id)
        except ValueError as exc:
            messagebox.showwarning("Category in use", str(exc))
            return
        self.audit.log("category_delete", old_value=old, source="desktop")
        self.refresh()

    def add_account_dialog(self) -> None:
        def save(data: dict[str, Any]) -> None:
            self.repo.add_account(data["name"], data["kind"], data["color"])
            self.audit.log("account_add", new_value=data, source="desktop")
            self.refresh()

        AccountDialog(self, save)

    def edit_selected_account(self) -> None:
        selected = self.account_manage_tree.selection()
        if not selected:
            return
        account_id = int(str(selected[0]).replace("account-", ""))
        accounts = {account["id"]: account for account in self.repo.accounts(active_only=False)}
        current = accounts.get(account_id)
        if not current:
            return

        def save(data: dict[str, Any]) -> None:
            old = self.repo.update_account(account_id, data["name"], data["kind"], data["color"], True)
            self.audit.log("account_edit", old_value=old, new_value={**data, "id": account_id}, source="desktop")
            self.refresh()

        AccountDialog(self, save, current)

    def delete_selected_account(self) -> None:
        selected = self.account_manage_tree.selection()
        if not selected:
            return
        account_id = int(str(selected[0]).replace("account-", ""))
        try:
            old = self.repo.delete_account(account_id)
        except ValueError as exc:
            messagebox.showwarning("Account in use", str(exc))
            return
        self.audit.log("account_delete", old_value=old, source="desktop")
        self.refresh()

    def edit_selected_transfer(self) -> None:
        selected = self.transfer_tree.selection()
        if not selected:
            return
        transfer_id = int(str(selected[0]).replace("transfer-", ""))
        current = self.repo.get_balance_transfer(transfer_id)
        if not current:
            return
        def save(data: dict[str, Any]) -> None:
            data = {
                **data,
                "timestamp": current["timestamp"],
            }
            old = self.repo.update_balance_transfer(transfer_id, data)
            self.audit.log("edit_balance_transfer", old_value=old, new_value={**data, "id": transfer_id}, source="desktop")
            self.refresh()

        TransferDialog(self, save, current, self._account_names())

    def backup_local(self) -> None:
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Save encrypted backup",
            defaultextension=".enc",
            initialfile=f"finance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc",
            filetypes=[("Encrypted backup", "*.enc"), ("All files", "*.*")],
        )
        if not target:
            return
        self._run_background(
            "Encrypted backup",
            lambda: self.backup_service.encrypted_local_backup(Path(target)),
            lambda p: messagebox.showinfo("Backup complete", f"Encrypted backup created:\n{p}"),
        )

    def restore_backup(self) -> None:
        source = filedialog.askopenfilename(
            parent=self,
            title="Restore encrypted backup",
            filetypes=[("Encrypted backup", "*.enc"), ("All files", "*.*")],
        )
        if not source:
            return
        if not messagebox.askyesno("Restore backup", "Restore will replace the current finance database. Continue?"):
            return
        self._run_background(
            "Restore backup",
            lambda: self.backup_service.restore_encrypted_backup(Path(source)),
            lambda _result: messagebox.showinfo("Restore complete", "Backup restored. The dashboard has been refreshed."),
        )

    def export_pdf(self) -> None:
        target = ask_report_path(self)
        if not target:
            return

        def job() -> Path:
            return self.exporter.export_monthly_report(
                Path(target),
                self.repo.list_transactions(),
                self.repo.list_loans("loans_given"),
                self.repo.list_loans("loans_taken"),
                self.repo.list_balance_transfers(),
            )

        self._run_background("PDF export", job, lambda path: messagebox.showinfo("Report exported", f"PDF report saved:\n{path}"))

    def scan_receipt(self) -> None:
        image = ask_image(self)
        if not image:
            return

        def job():
            return self.scanner.scan(Path(image))

        def done(result) -> None:
            if not result or result.amount is None:
                messagebox.showwarning("OCR fallback", "Could not extract a reliable amount. Please enter details manually.")
                self.open_transaction_dialog({"receipt_path": image, "note": "Receipt OCR fallback"})
                return
            self.open_transaction_dialog(
                {
                    "amount": result.amount,
                    "category": "Food",
                    "type": "Expense",
                    "payment_mode": self._account_names()[0],
                    "note": result.merchant or "Receipt import",
                    "receipt_path": image,
                }
            )

        self._run_background("Receipt OCR", job, done)

    def _run_background(self, label: str, func, on_success) -> None:
        self.status_text.set(f"{label} running...")
        future = self.executor.submit(func)

        def poll() -> None:
            if not future.done():
                self.after(150, poll)
                return
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("%s failed", label)
                self.status_text.set(f"{label} failed safely")
                messagebox.showwarning(f"{label} unavailable", f"{label} could not complete safely:\n{exc}")
                return
            self.status_text.set(f"{label} complete")
            on_success(result)
            self.refresh()

        poll()

    def _money(self, value: float) -> str:
        return f"INR {value:,.2f}"

    def _close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()
