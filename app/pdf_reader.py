"""Pulls plain text out of a typed/dictated PDF (not a scanned photo)."""

from pypdf import PdfReader


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)
