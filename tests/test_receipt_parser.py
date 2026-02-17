from app.services.receipt_parser import RegexReceiptParser


class TestRegexReceiptParser:
    def setup_method(self):
        self.parser = RegexReceiptParser()

    def test_parse_german_receipt(self, sample_ocr_text_de):
        result = self.parser.parse(sample_ocr_text_de)

        assert result.service_provider.name == "Starbucks Coffee"
        assert result.transaction_details.currency == "EUR"

    def test_parse_uk_receipt(self, sample_ocr_text_uk):
        result = self.parser.parse(sample_ocr_text_uk)

        assert result.service_provider.name == "Caffe Nero"
        assert result.service_provider.vat_number is not None
        assert "795871659" in result.service_provider.vat_number
        assert result.transaction_details.currency == "GBP"
        assert result.transaction_details.vat == "20%"

    def test_parse_empty_text(self):
        result = self.parser.parse("")
        assert result.service_provider.name == "Unknown"
        assert result.transaction_details.items == []
        assert result.transaction_details.total_amount is None

    def test_extract_currency_eur(self):
        assert self.parser._extract_currency("Total 9.28 EUR") == "EUR"
        assert self.parser._extract_currency("Summe 5,00€") == "EUR"

    def test_extract_currency_usd(self):
        assert self.parser._extract_currency("Total: $12.50") == "USD"

    def test_extract_currency_gbp(self):
        assert self.parser._extract_currency("GBP 9.30") == "GBP"

    def test_extract_currency_none(self):
        assert self.parser._extract_currency("no currency here") is None

    def test_extract_vat_percentage(self):
        assert self.parser._extract_vat("MwSt 19%") == "19%"
        assert self.parser._extract_vat("VAT 20 %") == "20%"
        assert self.parser._extract_vat("TVA 5,5%") == "5.5%"

    def test_extract_vat_none(self):
        assert self.parser._extract_vat("no vat info here") is None

    def test_find_vat_number(self):
        assert self.parser._find_vat_number("VAT: 795871659") is not None
        assert self.parser._find_vat_number("USt-IdNr: DE123456789") is not None
        assert self.parser._find_vat_number("no vat number") is None

    def test_address_detection(self):
        lines = [
            "Store Name",
            "Grimmaische Strasse 14",
            "04109 Leipzig",
        ]
        address = self.parser._find_address(lines)
        assert address is not None
        assert "04109" in address or "Strasse" in address.lower() or "strasse" in address.lower()
