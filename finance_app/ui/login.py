from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from finance_app.security.pin import PinAuthService
from finance_app.services.backup_service import BackupService
from finance_app.ui.theme import CYAN, MUTED, PANEL, PANEL_2, TEXT, apply_theme


class LoginWindow(tk.Tk):
    def __init__(self, auth: PinAuthService, backup_service: BackupService) -> None:
        super().__init__()
        apply_theme(self)
        self.auth = auth
        self.backup_service = backup_service
        self.authenticated = False
        self.title("TrackMint Secure Login")
        self.pin = tk.StringVar()
        self.confirm_pin = tk.StringVar()
        self._setup_mode = self.auth.is_pin_enabled() and not self.auth.is_pin_configured()
        self.geometry("560x500" if self._setup_mode else "560x430")
        self.minsize(500, 460 if self._setup_mode else 390)
        self.resizable(True, True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._build()
        self.bind("<Return>", lambda _event: self._submit())
        self.after(50, self._show_front)

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        shell = ttk.Frame(outer, padding=30, style="Panel.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(8, weight=1)

        brand = ttk.Frame(shell, style="Panel.TFrame")
        brand.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        brand.columnconfigure(0, weight=1)
        ttk.Label(brand, text="TrackMint", style="Panel.TLabel", font=("Segoe UI Semibold", 26), foreground=CYAN).grid(row=0, column=0, sticky="w")
        ttk.Label(brand, text="Private finance workspace", style="Panel.TLabel", foreground=MUTED).grid(row=1, column=0, sticky="w", pady=(2, 0))

        subtitle = "Create a local access PIN" if self._setup_mode else "Enter your local access PIN"
        ttk.Label(shell, text=subtitle, style="Panel.TLabel", font=("Segoe UI Semibold", 14), foreground=TEXT).grid(row=1, column=0, sticky="w", pady=(0, 16))

        ttk.Label(shell, text="PIN", style="Panel.TLabel", font=("Segoe UI Semibold", 10)).grid(row=2, column=0, sticky="w")
        self.pin_entry = ttk.Entry(shell, textvariable=self.pin, show="*", justify="center", font=("Segoe UI", 18))
        self.pin_entry.grid(row=3, column=0, sticky="ew", pady=(7, 18), ipady=4)
        self.pin_entry.focus_set()

        if self._setup_mode:
            ttk.Label(shell, text="Confirm PIN", style="Panel.TLabel", font=("Segoe UI Semibold", 10)).grid(row=4, column=0, sticky="w")
            ttk.Entry(shell, textvariable=self.confirm_pin, show="*", justify="center", font=("Segoe UI", 18)).grid(row=5, column=0, sticky="ew", pady=(7, 18), ipady=4)
            button_row = 6
            help_row = 7
        else:
            button_row = 4
            help_row = 5

        ttk.Button(shell, text="Unlock" if not self._setup_mode else "Create PIN", style="Accent.TButton", command=self._submit).grid(row=button_row, column=0, sticky="ew", pady=(4, 18), ipady=4)
        if not self._setup_mode:
            ttk.Button(shell, text="Forgot PIN / Reset App", command=self._forgot_pin_reset).grid(row=button_row + 1, column=0, sticky="ew", pady=(0, 14))
            help_row = button_row + 2
        ttk.Label(
            shell,
            text="PIN protection is local to this device. Reset creates an encrypted backup before starting fresh.",
            style="Panel.TLabel",
            foreground=MUTED,
            wraplength=420,
            justify="left",
        ).grid(row=help_row, column=0, sticky="sew", pady=(4, 0))

    def _show_front(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self.pin_entry.focus_set()

    def _submit(self) -> None:
        pin = self.pin.get().strip()
        if self._setup_mode:
            if pin != self.confirm_pin.get().strip():
                messagebox.showwarning("PIN mismatch", "The PIN confirmation does not match.")
                return
            try:
                self.auth.set_pin(pin)
            except ValueError as exc:
                messagebox.showwarning("Invalid PIN", str(exc))
                return
            self.authenticated = True
            self.destroy()
            return

        if self.auth.verify_pin(pin):
            self.authenticated = True
            self.destroy()
            return
        self.pin.set("")
        messagebox.showwarning("Login failed", "Incorrect PIN.")

    def _forgot_pin_reset(self) -> None:
        if not messagebox.askyesno(
            "Reset TrackMint",
            "This will create an encrypted backup, clear all local data, remove the PIN, and start fresh. Continue?",
        ):
            return
        confirm = simpledialog.askstring("Confirm reset", "Type RESET to continue:", parent=self)
        if confirm != "RESET":
            return
        try:
            backup = self.backup_service.reset_application()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Reset failed", f"Reset could not be completed safely:\n{exc}")
            return
        messagebox.showinfo("Reset complete", f"Encrypted backup created before reset:\n{backup}")
        self.authenticated = True
        self.destroy()
