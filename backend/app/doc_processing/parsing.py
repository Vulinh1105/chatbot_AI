"""
doc_processing.parsing
=======================
Kết hợp parser cho PDF, DOCX và TXT vào một entrypoint duy nhất:
`parse_document()`.

Lưu ý quan trọng về codebase này: file lưu trên đĩa (Document.file_path,
xem app/services/document_service.py) được đặt tên theo `str(document.id)`
và KHÔNG có phần mở rộng. Vì vậy loại file phải được xác định qua
`Document.original_filename` (tên lúc upload), không phải qua đuôi của
file vật lý trên đĩa.

Output là list "parsed block" - input trực tiếp cho chunking.py:
    {"document_id": int, "page": int, "text": str}

Cài đặt: pip install pymupdf python-docx
"""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz  # PyMuPDF - "import fitz" cũ đã deprecated
from docx import Document as DocxDocument

from app.model.document import Document

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class UnsupportedFileTypeError(ValueError):
    """Raised khi original_filename có đuôi mà parser chưa hỗ trợ."""


def _parse_pdf(file_path: Path, document_id: int) -> list[dict]:
    blocks: list[dict] = []
    doc = fitz.open(file_path)
    try:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue  # trang trống hoặc trang scan không có text layer
            blocks.append({
                "document_id": document_id,
                "page": page_number,
                "text": text,
            })
    finally:
        doc.close()
    return blocks


def _parse_docx(file_path: Path, document_id: int, group_size: int = 10) -> list[dict]:
    """DOCX không có khái niệm 'trang' khi đọc bằng python-docx, nên gộp
    mỗi `group_size` đoạn văn thành 1 pseudo-page để giữ field 'page'
    đồng nhất với PDF."""
    docx_doc = DocxDocument(file_path)
    paragraphs = [p.text.strip() for p in docx_doc.paragraphs if p.text.strip()]

    blocks: list[dict] = []
    for i in range(0, len(paragraphs), group_size):
        group_text = "\n".join(paragraphs[i:i + group_size])
        blocks.append({
            "document_id": document_id,
            "page": i // group_size + 1,
            "text": group_text,
        })
    return blocks


def _parse_txt(file_path: Path, document_id: int) -> list[dict]:
    text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    return [{
        "document_id": document_id,
        "page": 1,
        "text": text,
    }]


_PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".txt": _parse_txt,
}


def parse_document(file_path: Path | str, original_filename: str, document_id: int) -> list[dict]:
    """
    Entrypoint chính - dùng chung cho PDF/DOCX/TXT.

    Args:
        file_path: đường dẫn file thật trên đĩa (Document.file_path - KHÔNG có đuôi).
        original_filename: tên file gốc lúc upload (Document.original_filename -
            dùng để xác định loại file).
        document_id: Document.id trong DB.

    Returns:
        list[dict]: list "parsed block" {document_id, page, text}

    Raises:
        UnsupportedFileTypeError: nếu đuôi file không nằm trong SUPPORTED_EXTENSIONS.
    """
    ext = Path(original_filename).suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise UnsupportedFileTypeError(
            f"parsing.py chưa hỗ trợ đuôi file: {ext!r} (original_filename={original_filename!r}). "
            f"Đã hỗ trợ: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return parser(Path(file_path), document_id)


def parse_document_model(document: Document) -> list[dict]:
    """Tiện ích: parse trực tiếp từ 1 ORM `Document` object (lấy từ DB) thay vì
    truyền tay 3 field. Dùng trong service layer khi đã query được document."""
    return parse_document(document.file_path, document.original_filename, document.id)


if __name__ == "__main__":
    # Demo nhanh - đổi đường dẫn cho khớp 1 file thật trên máy bạn.
    demo_blocks = parse_document("sample_files/HR_Policy.pdf", "HR_Policy.pdf", document_id=1)
    print(f"Đã parse {len(demo_blocks)} block")
