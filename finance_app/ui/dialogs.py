from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any, Callable


class TransactionDialog(tk.Toplevel):
    def __init__(self, parent, categories: list[dict[str, Any]], on_save: Callable[[dict[str, Any]], None], defaults: dict[str, Any] | None = None, accounts: list[str] | None = None):
        super().__init__(parent)
        self.title("Transaction")
        self.configure(bg="#111827")
        self.resizable(False, False)
        self.on_save = on_save
        self.categories = categories
        self.accounts = accounts or ["Cash", "Online"]
        defaults = defaults or {}
        self.vars = {
            "amount": tk.StringVar(value=str(defaults.get("amount", ""))),
            "category": tk.StringVar(value=defaults.get("category", categories[0]["name"] if categories else "Other")),
            "type": tk.StringVar(value=defaults.get("type", "Expense")),
            "payment_mode": tk.StringVar(value=defaults.get("payment_mode", self.accounts[0] if self.accounts else "Cash")),
            "timestamp": tk.StringVar(value=defaults.get("timestamp", datetime.now().isoformat(timespec="seconds"))),
            "note": tk.StringVar(value=defaults.get("note", "")),
            "receipt_path": tk.StringVar(value=defaults.get("receipt_path", "")),
        }
        self._build()
        self.grab_set()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=18, style="Panel.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        fields = [
            ("Amount", ttk.Entry(frame, textvariable=self.vars["amount"])),
            ("Category", ttk.Combobox(frame, textvariable=self.vars["category"], values=[c["name"] for c in self.categories], state="readonly")),
            ("Type", ttk.Combobox(frame, textvariable=self.vars["type"], values=["Income", "Expense"], state="readonly")),
            ("Account", ttk.Combobox(frame, textvariable=self.vars["payment_mode"], values=self.accounts, state="readonly")),
            ("Timestamp", ttk.Entry(frame, textvariable=self.vars["timestamp"])),
            ("Note", ttk.Entry(frame, textvariable=self.vars["note"])),
        ]
        for row, (label, widget) in enumerate(fields):
            ttk.Label(frame, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=6)
            widget.grid(row=row, column=1, sticky="ew", pady=6, padx=(14, 0))
        frame.columnconfigure(1, minsize=280)
        ttk.Button(frame, text="Save", style="Accent.TButton", command=self._save).grid(row=len(fields), column=1, sticky="e", pady=(14, 0))

    def _save(self) -> None:
        try:
            amount = float(self.vars["amount"].get())
            if amount < 0:
                raise ValueError
            datetime.fromisoformat(self.vars["timestamp"].get())
        except ValueError:
            messagebox.showwarning("Invalid transaction", "Enter a valid amount and ISO timestamp.")
            return
        data = {key: var.get() for key, var in self.vars.items()}
        data["amount"] = amount
        self.on_save(data)
        self.destroy()


class LoanDialog(tk.Toplevel):
    def __init__(self, parent, mode: str, on_save: Callable[[str, dict[str, Any]], None], defaults: dict[str, Any] | None = None):
        super().__init__(parent)
        self.title("Loan")
        self.configure(bg="#111827")
        self.resizable(False, False)
        self.mode = mode
        self.on_save = on_save
        defaults = defaults or {}
        self.vars = {
            "party": tk.StringVar(value=defaults.get("party") or defaults.get("counterparty") or defaults.get("lender") or ""),
            "principal": tk.StringVar(value=str(defaults.get("principal", ""))),
            "interest_rate": tk.StringVar(value=str(defaults.get("interest_rate", "0"))),
            "repaid": tk.StringVar(value=str(defaults.get("repaid", "0"))),
            "due_date": tk.StringVar(value=defaults.get("due_date") or ""),
            "note": tk.StringVar(value=defaults.get("note") or ""),
        }
        self._build()
        self.grab_set()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=18, style="Panel.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        labels = ["Counterparty / Lender", "Principal", "Interest %", "Already Repaid", "Due Date YYYY-MM-DD", "Note"]
        for row, key in enumerate(self.vars):
            ttk.Label(frame, text=labels[row], style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=6)
            ttk.Entry(frame, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", pady=6, padx=(14, 0))
        ttk.Button(frame, text="Save", style="Accent.TButton", command=self._save).grid(row=len(labels), column=1, sticky="e", pady=(14, 0))

    def _save(self) -> None:
        try:
            principal = float(self.vars["principal"].get())
            interest = float(self.vars["interest_rate"].get() or 0)
            repaid = float(self.vars["repaid"].get() or 0)
        except ValueError:
            messagebox.showwarning("Invalid loan", "Enter valid numeric loan values.")
            return
        data = {key: var.get() for key, var in self.vars.items()}
        data.update({"principal": principal, "interest_rate": interest, "repaid": repaid})
        self.on_save(self.mode, data)
        self.destroy()


class CategoryDialog(tk.Toplevel):
    def __init__(self, parent, on_save: Callable[[dict[str, Any]], None], defaults: dict[str, Any] | None = None):
        super().__init__(parent)
        self.title("Category")
        self.configure(bg="#111827")
        self.resizable(False, False)
        self.on_save = on_save
        defaults = defaults or {}
        self.vars = {
            "name": tk.StringVar(value=defaults.get("name", "")),
            "kind": tk.StringVar(value=defaults.get("kind", "Expense")),
            "color": tk.StringVar(value=defaults.get("color", "#22d3ee")),
        }
        frame = ttk.Frame(self, padding=18, style="Panel.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="Name", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.vars["name"]).grid(row=0, column=1, sticky="ew", pady=6, padx=(14, 0))
        ttk.Label(frame, text="Type", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(frame, textvariable=self.vars["kind"], values=["Income", "Expense"], state="readonly").grid(row=1, column=1, sticky="ew", pady=6, padx=(14, 0))
        ttk.Label(frame, text="Color", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        color_row = ttk.Frame(frame, style="Panel.TFrame")
        color_row.grid(row=2, column=1, sticky="ew", pady=6, padx=(14, 0))
        color_row.columnconfigure(1, weight=1)
        self.color_preview = tk.Label(color_row, text="", width=4, height=1, bg=self.vars["color"].get(), relief="flat")
        self.color_preview.grid(row=0, column=0, sticky="w")
        ttk.Button(color_row, text="Choose Color", command=self._choose_color).grid(row=0, column=1, sticky="w", padx=(10, 0))
        frame.columnconfigure(1, minsize=260)
        ttk.Button(frame, text="Save", style="Accent.TButton", command=self._save).grid(row=3, column=1, sticky="e", pady=(14, 0))
        self.grab_set()

    def _choose_color(self) -> None:
        _rgb, color = colorchooser.askcolor(parent=self, color=self.vars["color"].get(), title="Choose category color")
        if color:
            self.vars["color"].set(color)
            self.color_preview.configure(bg=color)

    def _save(self) -> None:
        data = {key: var.get().strip() for key, var in self.vars.items()}
        if not data["name"]:
            messagebox.showwarning("Invalid category", "Category name is required.")
            return
        if not data["color"].startswith("#") or len(data["color"]) not in {4, 7}:
            messagebox.showwarning("Invalid color", "Use a hex color like #22d3ee.")
            return
        self.on_save(data)
        self.destroy()


class RepaymentDialog(tk.Toplevel):
    def __init__(self, parent, on_save: Callable[[dict[str, Any]], None], accounts: list[str]):
        super().__init__(parent)
        self.title("Record Repayment")
        self.configure(bg="#111827")
        self.resizable(False, False)
        self.on_save = on_save
        self.vars = {
            "amount": tk.StringVar(),
            "payment_mode": tk.StringVar(value=accounts[0] if accounts else "Cash"),
            "note": tk.StringVar(),
        }
        frame = ttk.Frame(self, padding=18, style="Panel.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        fields = [
            ("Payment Amount", ttk.Entry(frame, textvariable=self.vars["amount"])),
            ("Account", ttk.Combobox(frame, textvariable=self.vars["payment_mode"], values=accounts, state="readonly")),
            ("Note", ttk.Entry(frame, textvariable=self.vars["note"])),
        ]
        for row, (label, widget) in enumerate(fields):
            ttk.Label(frame, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=6)
            widget.grid(row=row, column=1, sticky="ew", pady=6, padx=(14, 0))
        ttk.Button(frame, text="Record", style="Accent.TButton", command=self._save).grid(row=3, column=1, sticky="e", pady=(14, 0))
        frame.columnconfigure(1, minsize=220)
        self.grab_set()

    def _save(self) -> None:
        try:
            amount = float(self.vars["amount"].get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid repayment", "Enter a valid positive amount.")
            return
        self.on_save({"amount": amount, "payment_mode": self.vars["payment_mode"].get(), "note": self.vars["note"].get()})
        self.destroy()


class TransferDialog(tk.Toplevel):
    def __init__(self, parent, on_save: Callable[[dict[str, Any]], None], defaults: dict[str, Any], accounts: list[str]):
        super().__init__(parent)
        self.title("Edit Transfer")
        self.configure(bg="#111827")
        self.resizable(False, False)
        self.on_save = on_save
        self.vars = {
            "amount": tk.StringVar(value=str(defaults.get("amount", ""))),
            "from_mode": tk.StringVar(value=defaults.get("from_mode", accounts[0] if accounts else "Cash")),
            "to_mode": tk.StringVar(value=defaults.get("to_mode", accounts[1] if len(accounts) > 1 else "Cash")),
            "note": tk.StringVar(value=defaults.get("note", "")),
        }
        frame = ttk.Frame(self, padding=18, style="Panel.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        fields = [
            ("Amount", ttk.Entry(frame, textvariable=self.vars["amount"])),
            ("From", ttk.Combobox(frame, textvariable=self.vars["from_mode"], values=accounts, state="readonly")),
            ("To", ttk.Combobox(frame, textvariable=self.vars["to_mode"], values=accounts, state="readonly")),
            ("Note", ttk.Entry(frame, textvariable=self.vars["note"])),
        ]
        for row, (label, widget) in enumerate(fields):
            ttk.Label(frame, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=6)
            widget.grid(row=row, column=1, sticky="ew", pady=6, padx=(14, 0))
        frame.columnconfigure(1, minsize=260)
        ttk.Button(frame, text="Save", style="Accent.TButton", command=self._save).grid(row=4, column=1, sticky="e", pady=(14, 0))
        self.grab_set()

    def _save(self) -> None:
        try:
            amount = float(self.vars["amount"].get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid transfer", "Enter a valid positive amount.")
            return
        data = {key: var.get() for key, var in self.vars.items()}
        if data["from_mode"] == data["to_mode"]:
            messagebox.showwarning("Invalid transfer", "Cash and Online transfer sides must be different.")
            return
        data["amount"] = amount
        self.on_save(data)
        self.destroy()


class AccountDialog(tk.Toplevel):
    def __init__(self, parent, on_save: Callable[[dict[str, Any]], None], defaults: dict[str, Any] | None = None):
        super().__init__(parent)
        self.title("Account")
        self.configure(bg="#111827")
        self.resizable(False, False)
        self.on_save = on_save
        defaults = defaults or {}
        self.vars = {
            "name": tk.StringVar(value=defaults.get("name", "")),
            "kind": tk.StringVar(value=defaults.get("kind", "Online")),
            "color": tk.StringVar(value=defaults.get("color", "#22d3ee")),
        }
        frame = ttk.Frame(self, padding=18, style="Panel.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="Account Name", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.vars["name"]).grid(row=0, column=1, sticky="ew", pady=6, padx=(14, 0))
        ttk.Label(frame, text="Type", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(frame, textvariable=self.vars["kind"], values=["Cash", "Online"], state="readonly").grid(row=1, column=1, sticky="ew", pady=6, padx=(14, 0))
        ttk.Label(frame, text="Color", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        color_row = ttk.Frame(frame, style="Panel.TFrame")
        color_row.grid(row=2, column=1, sticky="ew", pady=6, padx=(14, 0))
        self.color_preview = tk.Label(color_row, text="", width=4, bg=self.vars["color"].get())
        self.color_preview.grid(row=0, column=0)
        ttk.Button(color_row, text="Choose Color", command=self._choose_color).grid(row=0, column=1, padx=(10, 0))
        ttk.Button(frame, text="Save", style="Accent.TButton", command=self._save).grid(row=3, column=1, sticky="e", pady=(14, 0))
        frame.columnconfigure(1, minsize=260)
        self.grab_set()

    def _choose_color(self) -> None:
        _rgb, color = colorchooser.askcolor(parent=self, color=self.vars["color"].get(), title="Choose account color")
        if color:
            self.vars["color"].set(color)
            self.color_preview.configure(bg=color)

    def _save(self) -> None:
        data = {key: var.get().strip() for key, var in self.vars.items()}
        if not data["name"]:
            messagebox.showwarning("Invalid account", "Account name is required.")
            return
        self.on_save(data)
        self.destroy()


def ask_image(parent) -> str:
    return filedialog.askopenfilename(parent=parent, title="Select receipt", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")])


def ask_report_path(parent) -> str:
    return filedialog.asksaveasfilename(parent=parent, title="Export PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
