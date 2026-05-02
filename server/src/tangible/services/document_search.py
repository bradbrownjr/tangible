"""Best-effort document text extraction for search indexing."""

from __future__ import annotations

from pathlib import Path

_MAX_CHARS = 20_000


def _normalize(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:_MAX_CHARS]


def _extract_text_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            parts.append(page_text)
    return "\n".join(parts)


def _extract_image_ocr(path: Path) -> str:
    from PIL import Image

    try:
        import pytesseract
    except Exception:
        return ""

    with Image.open(path) as img:
        try:
            text = pytesseract.image_to_string(img)
        except Exception:
            return ""
    return text or ""


def _extract_docx_text(path: Path) -> str:
    import zipfile
    from xml.etree import ElementTree

    with zipfile.ZipFile(path) as zf, zf.open("word/document.xml") as f:
        xml_bytes = f.read()
    root = ElementTree.fromstring(xml_bytes)
    texts: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
    return " ".join(texts)


def extract_search_text(path: Path, mime_type: str, filename: str) -> str | None:
    """Extract searchable text from a document.

    Extraction is best-effort; failures should never block upload.
    """
    mime = (mime_type or "").lower()
    name = (filename or "").lower()

    try:
        if mime.startswith("text/"):
            text = _extract_text_plain(path)
            normalized = _normalize(text)
            return normalized or None

        if mime == "application/pdf" or name.endswith(".pdf"):
            text = _extract_pdf_text(path)
            normalized = _normalize(text)
            return normalized or None

        if mime.startswith("image/"):
            text = _extract_image_ocr(path)
            normalized = _normalize(text)
            return normalized or None

        if (
            mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or name.endswith(".docx")
        ):
            text = _extract_docx_text(path)
            normalized = _normalize(text)
            return normalized or None
    except Exception:
        return None

    return None
