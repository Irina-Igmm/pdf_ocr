# Initialize PaddleOCR instance with mkldnn disabled
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False
)

# Run OCR inference
result = ocr.predict(
    input="./data/archive/2017/de/public transport/118NP8.pdf"
)

# Visualize and save
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")