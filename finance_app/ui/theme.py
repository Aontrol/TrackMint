from __future__ import annotations

import tkinter as tk
from tkinter import ttk


BG = "#0b1120"
PANEL = "#111827"
PANEL_2 = "#172033"
PANEL_3 = "#202b3f"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
CYAN = "#22d3ee"
GREEN = "#22c55e"
PURPLE = "#a78bfa"
RED = "#f87171"
YELLOW = "#facc15"


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG)
    root.option_add("*Background", BG)
    root.option_add("*Foreground", TEXT)
    root.option_add("*Entry.Background", PANEL_2)
    root.option_add("*Entry.Foreground", TEXT)
    root.option_add("*Entry.InsertBackground", TEXT)
    root.option_add("*Text.Background", PANEL)
    root.option_add("*Text.Foreground", TEXT)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=BG,
        foreground=TEXT,
        fieldbackground=PANEL_2,
        bordercolor=PANEL_2,
        lightcolor=PANEL_2,
        darkcolor=PANEL_2,
        troughcolor=PANEL,
        selectbackground="#155e75",
        selectforeground=TEXT,
    )
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("Surface.TFrame", background=PANEL_2)
    style.configure("Sidebar.TFrame", background="#090f1c")
    style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
    style.configure("Surface.TLabel", background=PANEL_2, foreground=TEXT)
    style.configure("Sidebar.TLabel", background="#090f1c", foreground=TEXT)
    style.configure("Section.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 14))
    style.configure("CardTitle.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("CardValue.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 17))
    style.configure("Tiny.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 8))
    style.configure("TButton", background=PANEL_2, foreground=TEXT, borderwidth=0, focusthickness=0, padding=(12, 8))
    style.map("TButton", background=[("active", PANEL_3)], foreground=[("active", TEXT)])
    style.configure("Accent.TButton", background=CYAN, foreground="#06121f")
    style.map("Accent.TButton", background=[("active", "#67e8f9")], foreground=[("active", "#06121f")])
    style.configure("Nav.TButton", background="#090f1c", foreground=MUTED, anchor="w", padding=(16, 11))
    style.map("Nav.TButton", background=[("active", PANEL_2)], foreground=[("active", TEXT)])
    style.configure("TCheckbutton", background=PANEL, foreground=TEXT, focuscolor=PANEL)
    style.map("TCheckbutton", background=[("active", PANEL)], foreground=[("active", TEXT)])
    style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=30, borderwidth=0)
    style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT, font=("Segoe UI Semibold", 9))
    style.map("Treeview", background=[("selected", "#155e75")])
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 9), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", PANEL_2)], foreground=[("selected", TEXT)])
    style.configure(
        "TEntry",
        background=PANEL_2,
        fieldbackground=PANEL_2,
        foreground=TEXT,
        insertcolor=TEXT,
        bordercolor="#334155",
        padding=8,
    )
    style.map(
        "TEntry",
        fieldbackground=[("readonly", PANEL_2), ("disabled", PANEL), ("focus", PANEL_2)],
        foreground=[("disabled", MUTED), ("readonly", TEXT), ("focus", TEXT)],
    )
    style.configure(
        "TCombobox",
        background=PANEL_2,
        fieldbackground=PANEL_2,
        foreground=TEXT,
        arrowcolor=TEXT,
        bordercolor="#334155",
        padding=8,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", PANEL_2), ("disabled", PANEL)],
        foreground=[("readonly", TEXT), ("disabled", MUTED)],
        selectbackground=[("readonly", PANEL_2)],
        selectforeground=[("readonly", TEXT)],
    )
    style.configure("Vertical.TScrollbar", background=PANEL_2, troughcolor=PANEL, arrowcolor=TEXT, bordercolor=PANEL)
