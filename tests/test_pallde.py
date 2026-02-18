# Initialize PaddleOCR instance with mkldnn disabled
from paddleocr import PaddleOCR
from sympy import true

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False
)

# Run OCR inference
result = ocr.ocr(
    "./data/archive/2017/de/public transport/118NP8.pdf",
    cls=True
)

# Visualize and save
# Print results
if result:
    for block in result:
        if block:
            for line in block:
                text = line[1][0]
                confidence = line[1][1]
                print(f"[{confidence:.2f}] {text}")