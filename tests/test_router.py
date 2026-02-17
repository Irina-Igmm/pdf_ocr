from unittest.mock import patch

from app.schemas.receipt import (
    Item,
    ReceiptResponse,
    ServiceProvider,
    TransactionDetails,
)


MOCK_RESPONSE = ReceiptResponse(
    ServiceProvider=ServiceProvider(Name="Test Store"),
    TransactionDetails=TransactionDetails(
        Items=[Item(Item="Coffee", Quantity=1, Price=3.50)],
        Currency="EUR",
        TotalAmount=3.50,
    ),
)


class TestProcessPdfEndpoint:
    def test_rejects_non_pdf(self, client):
        response = client.post(
            "/process_pdf",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_rejects_empty_file(self, client):
        response = client.post(
            "/process_pdf",
            files={"file": ("test.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400

    @patch("app.routers.receipt.get_parser")
    @patch("app.routers.receipt.extract_text", return_value="Some OCR text")
    @patch("app.routers.receipt.pdf_to_images", return_value=[])
    def test_regex_strategy(self, mock_pdf, mock_ocr, mock_factory, client):
        mock_parser = mock_factory.return_value
        mock_parser.parse.return_value = MOCK_RESPONSE

        response = client.post(
            "/process_pdf?strategy=regex",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ServiceProvider"]["Name"] == "Test Store"

    @patch("app.routers.receipt.get_parser")
    @patch("app.routers.receipt.extract_text", return_value="Some OCR text")
    @patch("app.routers.receipt.pdf_to_images", return_value=[])
    def test_llm_strategy(self, mock_pdf, mock_ocr, mock_factory, client):
        mock_parser = mock_factory.return_value
        mock_parser.parse.return_value = MOCK_RESPONSE

        response = client.post(
            "/process_pdf?strategy=llm",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert response.status_code == 200

    @patch("app.routers.receipt.extract_text", return_value="")
    @patch("app.routers.receipt.pdf_to_images", return_value=[])
    def test_no_text_extracted(self, mock_pdf, mock_ocr, client):
        response = client.post(
            "/process_pdf",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert response.status_code == 422
