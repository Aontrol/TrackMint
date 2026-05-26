from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from finance_app.core.finance_engine import loan_exposure


class AnalyticsEngine:
    def summary(self, transactions: list[dict[str, Any]], loans_given: list[dict[str, Any]], loans_taken: list[dict[str, Any]]) -> dict[str, Any]:
        income = sum(t["amount"] for t in transactions if t["type"] == "Income")
        expense = sum(t["amount"] for t in transactions if t["type"] == "Expense")
        exposure = loan_exposure(loans_given, loans_taken)
        savings_efficiency = 0.0 if income <= 0 else max(0.0, (income - expense) / income * 100)
        risk_score = min(100, round((exposure / max(income, 1)) * 35, 1))
        return {
            "total_income": income,
            "total_expense": expense,
            "net_savings": income - expense,
            "loan_exposure": exposure,
            "risk_score": risk_score,
            "savings_efficiency": savings_efficiency,
            "top_categories": self.top_spending_categories(transactions),
            "avg_daily_expense": self.average_daily_expense(transactions),
            "burn_rate": self.monthly_burn_rate(transactions),
            "cashflow_volatility": self.cashflow_volatility(transactions),
        }

    def month_options(self, transactions: list[dict[str, Any]]) -> list[str]:
        months = sorted({datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") for t in transactions}, reverse=True)
        return ["All Months"] + months

    def filter_month(self, transactions: list[dict[str, Any]], month: str) -> list[dict[str, Any]]:
        if not month or month == "All Months":
            return transactions
        return [t for t in transactions if datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") == month]

    def monthly_snapshot(self, transactions: list[dict[str, Any]], month: str) -> dict[str, float]:
        scoped = self.filter_month(transactions, month)
        income = sum(t["amount"] for t in scoped if t["type"] == "Income")
        expense = sum(t["amount"] for t in scoped if t["type"] == "Expense")
        net = income - expense
        savings_rate = 0.0 if income <= 0 else max(0.0, net / income * 100)
        return {"income": income, "expense": expense, "net": net, "savings_rate": savings_rate}

    def average_daily_expense(self, transactions: list[dict[str, Any]]) -> float:
        expense_transactions = [t for t in transactions if t["type"] == "Expense"]
        if not expense_transactions:
            return 0.0
        days = {datetime.fromisoformat(t["timestamp"]).date() for t in expense_transactions}
        return sum(t["amount"] for t in expense_transactions) / max(len(days), 1)

    def monthly_burn_rate(self, transactions: list[dict[str, Any]]) -> float:
        months = {datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") for t in transactions}
        if not months:
            return 0.0
        expense = sum(t["amount"] for t in transactions if t["type"] == "Expense")
        return expense / len(months)

    def cashflow_volatility(self, transactions: list[dict[str, Any]]) -> float:
        monthly = []
        for month in sorted({datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") for t in transactions}):
            snap = self.monthly_snapshot(transactions, month)
            monthly.append(snap["net"])
        if len(monthly) < 2:
            return 0.0
        avg = sum(monthly) / len(monthly)
        variance = sum((value - avg) ** 2 for value in monthly) / len(monthly)
        return variance ** 0.5

    def insight_lines(
        self,
        transactions: list[dict[str, Any]],
        loans_given: list[dict[str, Any]],
        loans_taken: list[dict[str, Any]],
    ) -> list[str]:
        summary = self.summary(transactions, loans_given, loans_taken)
        lines = []
        if summary["savings_efficiency"] >= 35:
            lines.append("Savings efficiency is strong; surplus generation is healthy.")
        elif summary["savings_efficiency"] >= 15:
            lines.append("Savings efficiency is moderate; discretionary spend needs review.")
        else:
            lines.append("Savings efficiency is weak; expense controls should be tightened.")
        if summary["risk_score"] >= 60:
            lines.append("Loan exposure is elevated relative to income.")
        elif summary["risk_score"] >= 25:
            lines.append("Loan exposure is manageable but should be monitored.")
        else:
            lines.append("Loan exposure is currently low.")
        if summary["top_categories"]:
            category, amount = summary["top_categories"][0]
            lines.append(f"Highest spend concentration is {category} at INR {amount:,.0f}.")
        lines.append(f"Estimated monthly burn rate is INR {summary['burn_rate']:,.0f}.")
        return lines

    def balance_series(self, transactions: list[dict[str, Any]]) -> tuple[list[str], list[float]]:
        running = 0.0
        labels: list[str] = []
        values: list[float] = []
        for txn in sorted(transactions, key=lambda t: t["timestamp"]):
            running += txn["amount"] if txn["type"] == "Income" else -txn["amount"]
            labels.append(datetime.fromisoformat(txn["timestamp"]).strftime("%d %b"))
            values.append(running)
        return labels[-30:], values[-30:]

    def income_expense_by_month(self, transactions: list[dict[str, Any]]) -> tuple[list[str], list[float], list[float]]:
        buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"Income": 0.0, "Expense": 0.0})
        for txn in transactions:
            key = datetime.fromisoformat(txn["timestamp"]).strftime("%Y-%m")
            buckets[key][txn["type"]] += txn["amount"]
        labels = sorted(buckets)[-6:]
        return labels, [buckets[m]["Income"] for m in labels], [buckets[m]["Expense"] for m in labels]

    def mode_split(self, transactions: list[dict[str, Any]]) -> dict[str, float]:
        split = {"Cash": 0.0, "Online": 0.0}
        for txn in transactions:
            delta = txn["amount"] if txn["type"] == "Income" else -txn["amount"]
            split[txn["payment_mode"]] += delta
        return split

    def category_heat(self, transactions: list[dict[str, Any]]) -> tuple[list[str], list[str], list[list[float]]]:
        month_keys = sorted({datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") for t in transactions})[-6:]
        months = [datetime.strptime(month, "%Y-%m").strftime("%b") for month in month_keys] or ["Now"]
        categories = sorted({t["category"] for t in transactions if t["type"] == "Expense"})[:8] or ["None"]
        matrix = []
        for category in categories:
            row = []
            for month_key in month_keys or [""]:
                row.append(
                    sum(
                        t["amount"]
                        for t in transactions
                        if t["type"] == "Expense"
                        and t["category"] == category
                        and datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m") == month_key
                    )
                )
            matrix.append(row)
        return months, categories, matrix

    def top_spending_categories(self, transactions: list[dict[str, Any]], limit: int = 5) -> list[tuple[str, float]]:
        totals: dict[str, float] = defaultdict(float)
        for txn in transactions:
            if txn["type"] == "Expense":
                totals[txn["category"]] += txn["amount"]
        return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
