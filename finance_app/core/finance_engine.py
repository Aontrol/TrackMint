from __future__ import annotations

from datetime import datetime
from typing import Any


def compute_balances(transactions: list[dict[str, Any]], transfers: list[dict[str, Any]] | None = None) -> dict[str, float]:
    transfers = transfers or []
    accounts: dict[str, float] = {}
    for txn in transactions:
        account = txn["payment_mode"]
        accounts.setdefault(account, 0.0)
        accounts[account] += txn["amount"] if txn["type"] == "Income" else -txn["amount"]
    for transfer in transfers:
        amount = float(transfer["amount"])
        accounts.setdefault(transfer["from_mode"], 0.0)
        accounts.setdefault(transfer["to_mode"], 0.0)
        accounts[transfer["from_mode"]] -= amount
        accounts[transfer["to_mode"]] += amount
    cash = accounts.get("Cash", 0.0)
    online = sum(value for account, value in accounts.items() if account != "Cash")
    return {"cash": cash, "online": online, "total": cash + online, "accounts": accounts}


def monthly_profit_loss(transactions: list[dict[str, Any]], when: datetime | None = None) -> float:
    when = when or datetime.now()
    income = expense = 0.0
    for txn in transactions:
        ts = datetime.fromisoformat(txn["timestamp"])
        if ts.year == when.year and ts.month == when.month:
            if txn["type"] == "Income":
                income += txn["amount"]
            else:
                expense += txn["amount"]
    return income - expense


def savings_rate(transactions: list[dict[str, Any]], when: datetime | None = None) -> float:
    when = when or datetime.now()
    income = expense = 0.0
    for txn in transactions:
        ts = datetime.fromisoformat(txn["timestamp"])
        if ts.year == when.year and ts.month == when.month:
            if txn["type"] == "Income":
                income += txn["amount"]
            else:
                expense += txn["amount"]
    if income <= 0:
        return 0.0
    return max(0.0, ((income - expense) / income) * 100)


def loan_remaining(loan: dict[str, Any]) -> float:
    principal = float(loan.get("principal", 0))
    interest = principal * (float(loan.get("interest_rate", 0)) / 100)
    return max(0.0, principal + interest - float(loan.get("repaid", 0)))


def loan_exposure(loans_given: list[dict[str, Any]], loans_taken: list[dict[str, Any]]) -> float:
    return sum(loan_remaining(loan) for loan in loans_given + loans_taken)
