"""
PDF Text Extraction Module.

Uses PyMuPDF (fitz) to extract text-only content from PDF files.
Designed to handle 100+ page construction RFPs efficiently.
No image extraction — saves tokens when sending to LLM.
"""
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts all text from a PDF file, page by page.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        Concatenated text from all pages, separated by page markers.
    """
    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text.strip():
            text_parts.append(f"--- PAGE {page_num + 1} ---\n{page_text}")

    doc.close()
    return "\n\n".join(text_parts)


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts all text from a PDF provided as raw bytes (e.g. from file upload).

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages, separated by page markers.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text.strip():
            text_parts.append(f"--- PAGE {page_num + 1} ---\n{page_text}")

    doc.close()
    return "\n\n".join(text_parts)
