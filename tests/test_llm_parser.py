import json

from app.services.json_utils import parse_json_response as _parse_json_response


class TestParseJsonResponse:
    def test_valid_json(self):
        response = json.dumps(
            {
                "ServiceProvider": {
                    "Name": "Test Store",
                    "Address": "123 Main St",
                    "VATNumber": None,
                },
                "TransactionDetails": {
                    "Items": [{"Item": "Coffee", "Quantity": 1, "Price": 3.50}],
                    "Currency": "EUR",
                    "TotalAmount": 3.50,
                    "VAT": "19%",
                },
            }
        )
        result = _parse_json_response(response)
        assert result.service_provider.name == "Test Store"
        assert len(result.transaction_details.items) == 1
        assert result.transaction_details.total_amount == 3.50

    def test_json_in_markdown_fences(self):
        response = '```json\n{"ServiceProvider": {"Name": "Shop"}, "TransactionDetails": {"Items": []}}\n```'
        result = _parse_json_response(response)
        assert result.service_provider.name == "Shop"

    def test_invalid_json_fallback(self):
        response = "This is not JSON at all, sorry!"
        result = _parse_json_response(response)
        assert result.service_provider.name == "Unknown"
        assert result.transaction_details.items == []

    def test_partial_json_fallback(self):
        response = '{"ServiceProvider": {"Name": "Shop"}'  # missing closing
        result = _parse_json_response(response)
        # Should fallback gracefully
        assert result.service_provider.name is not None
