from __future__ import annotations

import os
from shutil import which

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
except Exception:  # pragma: no cover
    pytesseract = None
    TesseractNotFoundError = RuntimeError

from nlp.service import extract_candidate_words

COMMON_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def _resolve_tesseract_command() -> str | None:
    if pytesseract is None:
        return None

    configured = getattr(pytesseract.pytesseract, "tesseract_cmd", "")
    if configured and os.path.exists(configured):
        return configured

    discovered = which("tesseract")
    if discovered:
        pytesseract.pytesseract.tesseract_cmd = discovered
        return discovered

    for candidate in COMMON_TESSERACT_PATHS:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate

    return None


def _ocr_image(image):
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(grayscale, (5, 5), 0)
    thresholded = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    configs = ["--oem 3 --psm 6", "--oem 3 --psm 11"]
    extracted = []
    for source in [thresholded, grayscale]:
        for config in configs:
            text = pytesseract.image_to_string(source, config=config)
            if text and text.strip():
                extracted.append(text.strip())

    combined = "\n".join(dict.fromkeys(extracted)).strip()
    return combined


def extract_text_from_image(path: str):
    if cv2 is None or pytesseract is None:
        return {
            "text": "",
            "words": [],
            "warning": "OpenCV or pytesseract is not installed. Install both to enable image mode.",
        }

    if _resolve_tesseract_command() is None:
        return {
            "text": "",
            "words": [],
            "warning": "Tesseract OCR is not installed on this system. Install Tesseract and restart the app to use Image Mode.",
        }

    image = cv2.imread(path)
    if image is None:
        return {"text": "", "words": [], "warning": "Unable to read the uploaded image."}

    try:
        text = _ocr_image(image)
    except TesseractNotFoundError:
        return {
            "text": "",
            "words": [],
            "warning": "Tesseract OCR executable was not found. Add Tesseract to PATH or install it in the default Windows location.",
        }
    except Exception:
        return {
            "text": "",
            "words": [],
            "warning": "OCR could not analyze this image. Try a sharper image with clearer printed text.",
        }

    words = extract_candidate_words(text)
    warning = None if text else "No readable text was detected. Try a clearer, well-lit image with larger printed words."
    return {"text": text, "words": words, "warning": warning}


def extract_text_from_pdf(path: str):
    if fitz is None:
        return {"text": "", "warning": "PyMuPDF is not installed. Install fitz/PyMuPDF to enable PDF mode."}

    try:
        doc = fitz.open(path)
        pages = [page.get_text() for page in doc]
        text = "\n".join(pages)
        return {"text": text, "warning": None}
    except Exception:
        return {"text": "", "warning": "Unable to extract text from the PDF file."}


def process_live_frame_words(text: str):
    return extract_candidate_words(text)
