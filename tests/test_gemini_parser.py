from unittest.mock import patch

from PIL import Image

from app.services.gemini_parser import GeminiReceiptParser


def _make_image(w=100, h=100) -> Image.Image:
    return Image.new("RGB", (w, h), color="white")


VALID_JSON = """{
  "ServiceProvider": {"Name": "Test Shop", "Address": "123 Main St", "VATNumber": null},
  "TransactionDetails": {
    "Items": [{"Item": "Coffee", "Quantity": 1, "Price": 3.50}],
    "Currency": "EUR",
    "TotalAmount": 3.50,
    "VAT": null
  }
}"""


class TestGeminiReceiptParser:
    @patch("app.services.gemini_parser.chat_completion", return_value=VALID_JSON)
    @patch("app.services.gemini_parser.extract_text", return_value="Coffee 3.50")
    def test_parse_valid_response(self, _mock_ocr, _mock_chat):
        parser = GeminiReceiptParser()
        result = parser.parse([_make_image()])

        assert result.service_provider.name == "Test Shop"
        assert result.service_provider.address == "123 Main St"
        assert result.transaction_details.total_amount == 3.50
        assert result.transaction_details.currency == "EUR"
        assert len(result.transaction_details.items) == 1
        assert result.transaction_details.items[0].item == "Coffee"

    @patch("app.services.gemini_parser.chat_completion", return_value="This is not valid JSON")
    @patch("app.services.gemini_parser.extract_text", return_value="Coffee 3.50")
    def test_parse_invalid_json_fallback(self, _mock_ocr, _mock_chat):
        parser = GeminiReceiptParser()
        result = parser.parse([_make_image()])

        assert result.service_provider.name == "Unknown"

    @patch("app.services.gemini_parser.chat_completion", return_value=f"```json\n{VALID_JSON}\n```")
    @patch("app.services.gemini_parser.extract_text", return_value="Coffee 3.50")
    def test_parse_markdown_fenced_json(self, _mock_ocr, _mock_chat):
        parser = GeminiReceiptParser()
        result = parser.parse([_make_image()])

        assert result.service_provider.name == "Test Shop"
        assert result.transaction_details.total_amount == 3.50

    @patch("app.services.gemini_parser.extract_text", return_value="")
    def test_parse_empty_ocr_fallback(self, _mock_ocr):
        parser = GeminiReceiptParser()
        result = parser.parse([_make_image()])

        assert result.service_provider.name == "Unknown"
