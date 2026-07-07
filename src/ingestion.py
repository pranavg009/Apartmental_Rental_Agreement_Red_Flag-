"""
ingestion.py
Loads agreement text from .txt, .pdf, or .docx files.
Falls back gracefully if optional libraries (pdfplumber, python-docx) are not installed.
"""
import os


def load_text(file_path: str) -> str:
    """Load raw text from a supported file type based on its extension."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        return _load_txt(file_path)
    elif ext == ".pdf":
        return _load_pdf(file_path)
    elif ext == ".docx":
        return _load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .txt, .pdf, .docx")


def _load_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _load_pdf(file_path: str) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError(
            "pdfplumber is required to read PDF files. Install with: pip install pdfplumber"
        ) from e

    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    return "\n".join(text_chunks)


def _load_docx(file_path: str) -> str:
    try:
        import docx
    except ImportError as e:
        raise ImportError(
            "python-docx is required to read DOCX files. Install with: pip install python-docx"
        ) from e

    document = docx.Document(file_path)
    return "\n".join(p.text for p in document.paragraphs)


def load_text_from_string(raw_text: str) -> str:
    """Pass-through helper for text pasted directly into the UI (no file)."""
    return raw_text
