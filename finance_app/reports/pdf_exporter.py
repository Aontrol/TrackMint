from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from finance_app.analytics.engine import AnalyticsEngine
from finance_app.core.finance_engine import compute_balances, loan_remaining


class PDFExporter:
    def __init__(self, analytics: AnalyticsEngine) -> None:
        self.analytics = analytics

    def export_monthly_report(
        self,
        target: Path,
        transactions: list[dict[str, Any]],
        loans_given: list[dict[str, Any]],
        loans_taken: list[dict[str, Any]],
        transfers: list[dict[str, Any]] | None = None,
    ) -> Path:
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(target), pagesize=A4)
        story = [Paragraph("TrackMint Monthly Finance Report", styles["Title"])]
        story.append(Paragraph(datetime.now().strftime("%B %Y"), styles["Normal"]))
        story.append(Spacer(1, 18))

        summary = self.analytics.summary(transactions, loans_given, loans_taken)
        balances = compute_balances(transactions, transfers)
        rows = [
            ["Metric", "Value"],
            ["Total Income", self._money(summary["total_income"])],
            ["Total Expense", self._money(summary["total_expense"])],
            ["Net Savings", self._money(summary["net_savings"])],
            ["Cash Balance", self._money(balances["cash"])],
            ["Online Balance", self._money(balances["online"])],
            ["Loan Exposure", self._money(summary["loan_exposure"])],
            ["Risk Score", f"{summary['risk_score']} / 100"],
        ]
        story.append(self._table(rows))
        story.append(Spacer(1, 18))

        story.append(Paragraph("Top Spending Categories", styles["Heading2"]))
        cat_rows = [["Category", "Spend"]] + [[name, self._money(total)] for name, total in summary["top_categories"]]
        story.append(self._table(cat_rows or [["Category", "Spend"], ["None", "0"]]))
        story.append(Spacer(1, 18))

        story.append(Paragraph("Loan Report", styles["Heading2"]))
        loan_rows = [["Type", "Party", "Principal", "Remaining", "Due"]]
        for loan in loans_given:
            loan_rows.append(["Given", loan["counterparty"], self._money(loan["principal"]), self._money(loan_remaining(loan)), loan.get("due_date") or "-"])
        for loan in loans_taken:
            loan_rows.append(["Taken", loan["lender"], self._money(loan["principal"]), self._money(loan_remaining(loan)), loan.get("due_date") or "-"])
        story.append(self._table(loan_rows))
        doc.build(story)
        return target

    def _table(self, rows: list[list[Any]]) -> Table:
        table = Table(rows, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _money(self, value: float) -> str:
        return f"INR {value:,.2f}"
