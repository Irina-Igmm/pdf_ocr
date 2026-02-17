import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_ocr_text_de():
    return """Starbucks Coffee
AmRest Coffee Deutschland
Sp. z o.o. & Co. KG
Grimmaische Strasse 14
4109 Leipzig

103845
Chk 1649  02Jan'19 16:02

To Go
1 CaffeLatte                      4.29
  + cLowFatMilkCAMV
1 CaffeMocha                      4.99
  + cLowFatMilkCAMV

Bar                               50.00

0.28 MwSt. Fo 7%                   4.29
Netto                              4.01
0.80 MwSt. 19%                     4.99
Netto                              4.19

Subtotal                           9.28
Zahlung                            9.28
Rueckgeld                         40.72

Steuernummer 2/1849/2293
"""


@pytest.fixture
def sample_ocr_text_uk():
    return """Caffe Nero
782 Edinburgh Airport Gate 12
VAT: 795871659

1327 Barista ?

1 Salted Caramel Cheesecake        2.95
1 Chai Latte                       3.30
1 Latte Grande                     3.05

Credit Card MPG               GBP 9.30

1.06 VAT 20 %                     6.35
Net Total:                     GBP 5.29
Subtotal                       GBP 9.30
Payment                        GBP 9.30
Change Due                     GBP 0.00
"""
