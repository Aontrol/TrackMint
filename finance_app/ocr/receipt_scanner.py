from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReceiptResult:
    amount: float | None = None
    merchant: str | None = None
    date: str | None = None
    raw_text: str = ""


class ReceiptScanner:
    def scan(self, image_path: Path) -> ReceiptResult:
        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            raise RuntimeError("OCR dependencies are not installed") from exc

        text = pytesseract.image_to_string(Image.open(image_path))
        amount = self._extract_amount(text)
        date = self._extract_date(text)
        merchant = self._extract_merchant(text)
        return ReceiptResult(amount=amount, merchant=merchant, date=date, raw_text=text)

    def _extract_amount(self, text: str) -> float | None:
        candidates = []
        for match in re.finditer(r"(?:total|amount|paid|rs\.?|inr|₹)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.I):
            candidates.append(float(match.group(1).replace(",", "")))
        if not candidates:
            for match in re.finditer(r"([0-9,]+\.[0-9]{2})", text):
                candidates.append(float(match.group(1).replace(",", "")))
        return max(candidates) if candidates else None

    def _extract_date(self, text: str) -> str | None:
        match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        return match.group(1) if match else None

    def _extract_merchant(self, text: str) -> str | None:
        for line in text.splitlines():
            clean = line.strip()
            if len(clean) >= 3 and not re.search(r"\d{3,}", clean):
                return clean[:80]
        return None
