import json
import logging
import re

from app.schemas.receipt import (
    ReceiptResponse,
    ServiceProvider,
    TransactionDetails,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Currency normalisation map
# ---------------------------------------------------------------------------
CURRENCY_ALIASES: dict[str, str] = {
    # Symbols → ISO codes
    "€": "EUR", "£": "GBP", "$": "USD", "¥": "JPY", "CHF": "CHF",
    "kr": "SEK", "Kč": "CZK", "zł": "PLN", "kn": "HRK", "Ft": "HUF",
    "lei": "RON", "лв": "BGN", "₹": "INR", "R$": "BRL", "₽": "RUB",
    # Common text variants
    "euro": "EUR", "euros": "EUR", "eur": "EUR",
    "dollar": "USD", "dollars": "USD", "usd": "USD",
    "pound": "GBP", "pounds": "GBP", "gbp": "GBP",
    "yen": "JPY", "jpy": "JPY",
    "franc": "CHF", "francs": "CHF",
    "krona": "SEK", "kronor": "SEK", "sek": "SEK",
    "koruna": "CZK", "czk": "CZK",
    "zloty": "PLN", "pln": "PLN",
    "kuna": "HRK", "hrk": "HRK",
}


def _normalise_currency(value: str | None) -> str | None:
    """Normalise a currency string to its ISO 4217 code."""
    if not value:
        return value
    stripped = value.strip()
    # Already a 3-letter ISO code?
    if re.fullmatch(r"[A-Z]{3}", stripped):
        return stripped
    # Lookup in alias map (case-insensitive for text, exact for symbols)
    if stripped in CURRENCY_ALIASES:
        return CURRENCY_ALIASES[stripped]
    lower = stripped.lower()
    for alias, code in CURRENCY_ALIASES.items():
        if alias.lower() == lower:
            return code
    return stripped.upper()[:3] if stripped else value


def _validate_amounts(response: ReceiptResponse) -> ReceiptResponse:
    """Post-process amounts: round prices to 2 decimals, validate total."""
    td = response.transaction_details

    # Round item prices
    for item in td.items:
        item.price = round(item.price, 2)

    # Round total
    if td.total_amount is not None:
        td.total_amount = round(td.total_amount, 2)

    # Cross-check: if items exist, compare sum vs declared total
    if td.items and td.total_amount is not None:
        computed_total = round(sum(i.price * i.quantity for i in td.items), 2)
        diff = abs(computed_total - td.total_amount)
        if diff > 0.01:
            logger.debug(
                "Total mismatch: computed=%.2f vs declared=%.2f (diff=%.2f) "
                "— keeping declared total.",
                computed_total,
                td.total_amount,
                diff,
            )

    return response


def postprocess(response: ReceiptResponse) -> ReceiptResponse:
    """Apply all post-processing steps to a parsed receipt."""
    # Normalise currency
    response.transaction_details.currency = _normalise_currency(
        response.transaction_details.currency
    )
    # Validate amounts
    response = _validate_amounts(response)
    return response


def parse_json_response(response: str) -> ReceiptResponse:
    """Parse an LLM JSON output into a ReceiptResponse, with fallback."""
    try:
        json_str = response.strip()

        # Strip closed <think>…</think> reasoning blocks (e.g. Qwen3 models)
        json_str = re.sub(
            r"<think>.*?</think>", "", json_str, flags=re.DOTALL
        ).strip()

        # Handle unclosed <think> blocks (truncated or missing </think>)
        if "<think>" in json_str:
            think_pos = json_str.index("<think>")
            brace_pos = json_str.find("{", think_pos)
            if brace_pos != -1:
                json_str = json_str[brace_pos:]
            else:
                json_str = ""

        # Strip markdown code fences
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]

        # Locate the JSON object if there is leading text
        if json_str and not json_str.lstrip().startswith("{"):
            brace_start = json_str.find("{")
            if brace_start != -1:
                json_str = json_str[brace_start:]
            else:
                json_str = ""

        # Strip trailing content after the last }
        if json_str:
            brace_end = json_str.rfind("}")
            if brace_end != -1:
                json_str = json_str[: brace_end + 1]

        if not json_str.strip():
            raise ValueError("No JSON content found in LLM response")

        data = json.loads(json_str)
        result = ReceiptResponse.model_validate(data)
        return postprocess(result)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(
            "LLM output could not be parsed: %s — raw: %s",
            e, response[:500],
        )
        return ReceiptResponse(
            ServiceProvider=ServiceProvider(Name="Unknown"),
            TransactionDetails=TransactionDetails(),
        )


# ---------------------------------------------------------------------------
# Prompt with few-shot examples
# ---------------------------------------------------------------------------
RECEIPT_SCHEMA_PROMPT = """\
You are a receipt parser. Extract structured data as JSON.
Return ONLY a valid JSON object with this exact schema:
{
  "ServiceProvider": {
    "Name": "string",
    "Address": "string or null",
    "VATNumber": "string or null"
  },
  "TransactionDetails": {
    "Items": [{"Item": "string", "Quantity": integer, "Price": float}],
    "Currency": "string (ISO 4217, e.g. EUR, USD, GBP)",
    "TotalAmount": float or null,
    "VAT": "string or null"
  }
}

Here are two examples of correct outputs:

Example 1 — German supermarket receipt:
{
  "ServiceProvider": {
    "Name": "REWE Markt GmbH",
    "Address": "Domstr. 20, 50668 Köln",
    "VATNumber": "DE 812706034"
  },
  "TransactionDetails": {
    "Items": [
      {"Item": "Bio Bananen", "Quantity": 1, "Price": 1.29},
      {"Item": "Vollmilch 3.5%", "Quantity": 2, "Price": 0.89}
    ],
    "Currency": "EUR",
    "TotalAmount": 3.07,
    "VAT": "7% MwSt: 0.20"
  }
}

Example 2 — US restaurant receipt:
{
  "ServiceProvider": {
    "Name": "Shake Shack",
    "Address": "691 8th Avenue, New York, NY 10036",
    "VATNumber": null
  },
  "TransactionDetails": {
    "Items": [
      {"Item": "ShackBurger", "Quantity": 1, "Price": 6.89},
      {"Item": "Cheese Fries", "Quantity": 1, "Price": 4.19},
      {"Item": "Lemonade", "Quantity": 2, "Price": 3.29}
    ],
    "Currency": "USD",
    "TotalAmount": 17.66,
    "VAT": "Tax: $1.47"
  }
}

Important rules:
- Return ONLY the raw JSON object, NO markdown fences, NO ```json blocks, NO explanation
- Use ISO 4217 currency codes (EUR, USD, GBP, CHF, SEK, CZK, PLN, etc.)
- Price is the UNIT price, not total per line
- Quantity must be an integer (default to 1 if unknown)
- TotalAmount should be the final amount paid
- VATNumber is the tax registration number of the business, NOT the VAT rate
- VAT field contains the tax rate or amount details
- Your response must start with { and end with } — nothing else.
- Do NOT include any reasoning, thinking, or <think> blocks. Output ONLY the JSON object."""
