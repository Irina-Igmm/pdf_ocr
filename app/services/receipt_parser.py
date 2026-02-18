import re

from app.schemas.receipt import (
    Item,
    ReceiptResponse,
    ServiceProvider,
    TransactionDetails,
)


class RegexReceiptParser:
    """Parse raw OCR text into structured receipt data using regex heuristics."""

    def parse(self, raw_text: str) -> ReceiptResponse:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        provider = self._extract_provider(lines, raw_text)
        items = self._extract_items(lines)
        total = self._extract_total(lines)
        currency = self._extract_currency(raw_text)
        vat_info = self._extract_vat(raw_text)

        return ReceiptResponse(
            ServiceProvider=provider,
            TransactionDetails=TransactionDetails(
                Items=items,
                Currency=currency,
                TotalAmount=total,
                VAT=vat_info,
            ),
        )

    def _extract_provider(self, lines: list[str], raw_text: str) -> ServiceProvider:
        name = lines[0] if lines else "Unknown"
        address = self._find_address(lines[:10])
        vat_number = self._find_vat_number(raw_text)
        return ServiceProvider(Name=name, Address=address, VATNumber=vat_number)

    def _find_address(self, top_lines: list[str]) -> str | None:
        address_parts = []
        for line in top_lines[1:]:
            if re.search(r"\d{4,5}", line) and re.search(r"[A-Za-zÀ-ÿ]", line):
                address_parts.append(line)
            elif re.search(
                r"(str|straße|street|road|avenue|ave|blvd|platz|weg)",
                line,
                re.IGNORECASE,
            ):
                address_parts.append(line)
        return ", ".join(address_parts) if address_parts else None

    def _find_vat_number(self, text: str) -> str | None:
        patterns = [
            r"(?:USt[-.\s]?(?:Id)?[-.\s]?(?:Nr)?|VAT|TVA|MwSt)[\s.:]*([A-Z]{0,2}\s?\d[\d\s./-]{5,})",
            r"((?:DE|FR|CH|AT|GB|IT)\s?\d{9,12})",
            r"(?:Tax\s*(?:ID|No|Number))[\s.:]*(\S+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_items(self, lines: list[str]) -> list[Item]:
        items: list[Item] = []
        item_pattern = re.compile(
            r"^(.+?)\s+(\d+)\s*[xX×]?\s+(\d+[.,]\d{2})\s*$"
        )
        price_suffix_pattern = re.compile(
            r"^(.+?)\s+(\d+[.,]\d{2})\s*[A-Z]?\s*$"
        )

        for line in lines:
            match = item_pattern.match(line)
            if match:
                name = match.group(1).strip()
                qty = int(match.group(2))
                price = _parse_price(match.group(3))
                items.append(Item(Item=name, Quantity=qty, Price=price))
                continue

            match = price_suffix_pattern.match(line)
            if match:
                name = match.group(1).strip()
                price = _parse_price(match.group(2))
                if not _is_total_line(name):
                    items.append(Item(Item=name, Quantity=1, Price=price))

        return items

    def _extract_total(self, lines: list[str]) -> float | None:
        total_pattern = re.compile(
            r"(?:total|summe|gesamt|amount|betrag|somme|zu zahlen|bar)\s*[:\s]*(\d+[.,]\d{2})",
            re.IGNORECASE,
        )
        for line in reversed(lines):
            match = total_pattern.search(line)
            if match:
                return _parse_price(match.group(1))
        return None

    def _extract_currency(self, text: str) -> str | None:
        currency_map = {
            "EUR": r"EUR|€",
            "USD": r"USD|\$",
            "GBP": r"GBP|£",
            "CHF": r"CHF",
            "CAD": r"CAD|CA\$",
            "CNY": r"CNY|¥|RMB",
            "SEK": r"SEK|\bkr\b",
            "CZK": r"CZK|Kč",
            "PLN": r"PLN|zł",
        }
        for code, pattern in currency_map.items():
            if re.search(pattern, text):
                return code

        # Language-based heuristics: German keywords → EUR
        if re.search(
            r"\bMwSt\b|\bSumme\b|\bGesamt\b|\bBrutto\b|\bNetto\b"
            r"|\bRechnung\b|\bSteuer(?:nummer)?\b|\bZahlung\b",
            text,
            re.IGNORECASE,
        ):
            return "EUR"

        # French keywords → EUR
        if re.search(
            r"\bTVA\b|\bTTC\b|\b[Mm]ontant\b",
            text,
        ):
            return "EUR"

        return None

    def _extract_vat(self, text: str) -> str | None:
        patterns = [
            r"(?:MwSt|VAT|TVA|USt)\s*[:\s]*(\d+[.,]?\d*)\s*%",
            r"(\d+[.,]?\d*)\s*%\s*(?:MwSt|VAT|TVA|USt)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1).replace(',', '.')}%"
        return None


def _parse_price(price_str: str) -> float:
    return float(price_str.replace(",", "."))


def _is_total_line(name: str) -> bool:
    return bool(
        re.search(
            r"(total|summe|gesamt|amount|betrag|somme|zu zahlen|bar)",
            name,
            re.IGNORECASE,
        )
    )


# Backward-compatible alias
def parse_receipt(raw_text: str) -> ReceiptResponse:
    return RegexReceiptParser().parse(raw_text)
