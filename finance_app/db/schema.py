from __future__ import annotations


FINANCE_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'Expense',
    color TEXT NOT NULL DEFAULT '#22d3ee',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK(kind IN ('Cash', 'Online')),
    color TEXT NOT NULL DEFAULT '#22d3ee',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL CHECK(amount >= 0),
    category TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
    payment_mode TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    receipt_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS balance_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL CHECK(amount > 0),
    from_mode TEXT NOT NULL,
    to_mode TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(from_mode <> to_mode)
);

CREATE TABLE IF NOT EXISTS loans_given (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    counterparty TEXT NOT NULL,
    principal REAL NOT NULL CHECK(principal >= 0),
    interest_rate REAL NOT NULL DEFAULT 0,
    repaid REAL NOT NULL DEFAULT 0 CHECK(repaid >= 0),
    due_date TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loans_taken (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender TEXT NOT NULL,
    principal REAL NOT NULL CHECK(principal >= 0),
    interest_rate REAL NOT NULL DEFAULT 0,
    repaid REAL NOT NULL DEFAULT 0 CHECK(repaid >= 0),
    due_date TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


AUDIT_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    source TEXT NOT NULL,
    hash TEXT NOT NULL,
    previous_hash TEXT NOT NULL
);
"""


DEFAULT_CATEGORIES = [
    ("Salary", "Income", "#22c55e"),
    ("Business", "Income", "#14b8a6"),
    ("Investments", "Income", "#a855f7"),
    ("Food", "Expense", "#f97316"),
    ("Rent", "Expense", "#38bdf8"),
    ("Utilities", "Expense", "#eab308"),
    ("Transport", "Expense", "#ec4899"),
    ("Healthcare", "Expense", "#ef4444"),
    ("Shopping", "Expense", "#8b5cf6"),
    ("Education", "Expense", "#06b6d4"),
    ("Loan Recovery", "Income", "#22c55e"),
    ("Loan Repayment", "Expense", "#f87171"),
    ("Other", "Expense", "#94a3b8"),
]


DEFAULT_ACCOUNTS = [
    ("Cash", "Cash", "#22c55e"),
    ("Online", "Online", "#22d3ee"),
]
