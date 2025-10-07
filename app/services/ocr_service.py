import pytesseract
from PIL import Image
import io
from fastapi import HTTPException, status

def perform_ocr(content: bytes) -> str:
    """Uses Tesseract to perform OCR on an image."""
    try:
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tesseract OCR Error: {e}"
        )