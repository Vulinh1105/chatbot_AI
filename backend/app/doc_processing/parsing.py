"""
doc_processing.parsing
=======================
Module T07 (PDF Parser) + T08 (DOCX/TXT Parser) GỘP CHUNG thành 1 file, 1
entrypoint duy nhất: `parse_document()`. Lý do gộp: pipeline.py/ingestion.py
chỉ cần gọi 1 hàm, không phải if/else theo loại file ở tầng trên -> giảm
điểm có thể phát sinh lỗi khi các nhóm khác (G3, G4) tích hợp vào.

Tích hợp với phần code đã có sẵn (G4 - app/services/document_service.py):
    File vật lý lưu trên đĩa được đặt tên theo `str(document.id)` và KHÔNG
    có phần mở rộng (xem DocumentService.create_document). Vì vậy loại file
    PHẢI được xác định qua `Document.original_filename` (tên lúc upload),
    KHÔNG được xác định qua đuôi của file vật lý trên đĩa.

Input : đường dẫn file trên đĩa + tên file gốc lúc upload + document_id.
Output: list "parsed block" - input trực tiếp cho chunking.py:
    {"document_id": int, "page": int, "text": str}

Cài đặt: pip install pymupdf python-docx (đã có trong
app/doc_processing/requirements.txt).
"""

from __future__ import annotations

import logging
import sys
import unicodedata
from pathlib import Path

# Thêm thư mục `backend` vào sys.path khi chạy script trực tiếp (python backend/app/doc_processing/parsing.py)
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import pymupdf as fitz  # PyMuPDF - "import fitz" kiểu cũ đã deprecated
from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError

from app.model.document import Document

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cấu hình dùng chung toàn hệ thống
# ---------------------------------------------------------------------------

# 3 định dạng MVP hỗ trợ theo Kick-off Guide & SRS (PDF/DOCX/TXT).
# ĐÂY LÀ "single source of truth" cho toàn bộ backend: ingestion.py và
# endpoint upload (app/api/v1/endpoints/document.py) đều import biến này
# thay vì tự khai báo lại danh sách đuôi file - tránh tình trạng lệch nhau
# (ví dụ: endpoint cho phép .csv nhưng parser chưa hỗ trợ -> lỗi runtime khi
# indexing, chỉ phát hiện ra sau khi user đã upload xong).
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})


class ParsingError(Exception):
    """Lỗi phát sinh khi trích xuất text từ file (file hỏng, corrupt, thư viện lỗi...)."""


class UnsupportedFileTypeError(ParsingError):
    """Raised khi original_filename có đuôi mà parser chưa hỗ trợ."""


# ---------------------------------------------------------------------------
# Tiện ích nội bộ
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Chuẩn hoá text thô trước khi đưa sang chunking.py:
    - Chuẩn hoá Unicode NFC (tránh ký tự tiếng Việt tổ hợp bị tách thành
      nhiều code point, làm sai độ dài chunk ở bước sau).
    - Đưa CRLF/CR về LF, gộp nhiều dòng trống liên tiếp thành tối đa 1 dòng.
    - Trim khoảng trắng đầu/cuối.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in text.split("\n")]
    cleaned_lines: list[str] = []
    blank_streak = 0
    for line in lines:
        if line == "":
            blank_streak += 1
            if blank_streak > 1:
                continue
        else:
            blank_streak = 0
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _parse_pdf(file_path: Path, document_id: int) -> list[dict]:
    """T07 - PDF Parser: trích text theo từng trang, GIỮ số trang (page) làm
    evidence hiển thị citation (North Star trong Kick-off Guide: "Không có
    evidence phù hợp -> không bịa câu trả lời")."""
    try:
        doc = fitz.open(file_path)
    except Exception as exc:  # PyMuPDF ném nhiều loại lỗi khác nhau khi file hỏng
        raise ParsingError(f"Không thể mở file PDF '{file_path.name}': {exc}") from exc

    blocks: list[dict] = []
    try:
        for page_number, page in enumerate(doc, start=1):
            text = _clean_text(page.get_text("text"))
            if not text:
                # Trang trống hoặc trang scan (ảnh) không có text layer.
                # KHÔNG raise lỗi ở đây vì các trang khác trong cùng file vẫn
                # có thể hợp lệ - chỉ log cảnh báo để G1 (evaluation) biết
                # tài liệu này có thể cần OCR sau này (ngoài phạm vi MVP).
                logger.warning(
                    "PDF '%s' trang %s không trích được text (có thể là trang scan/ảnh).",
                    file_path.name, page_number,
                )
                continue
            blocks.append({
                "document_id": document_id,
                "page": page_number,
                "text": text,
            })
    finally:
        doc.close()
    return blocks


def _parse_docx(file_path: Path, document_id: int, group_size: int = 10) -> list[dict]:
    """T08 - DOCX Parser: python-docx không có khái niệm 'trang' (trang phụ
    thuộc engine render của Word, không tồn tại trong file .docx), nên gộp
    mỗi `group_size` đoạn văn thành 1 "pseudo-page" để field 'page' luôn
    đồng nhất với PDF/TXT ở tầng chunking/citation phía sau."""
    if group_size <= 0:
        raise ValueError("group_size phải lớn hơn 0 để chia văn bản DOCX thành các pseudo-page hợp lệ.")

    try:
        docx_doc = DocxDocument(file_path)
    except PackageNotFoundError as exc:
        raise ParsingError(f"File DOCX '{file_path.name}' bị hỏng hoặc sai định dạng: {exc}") from exc
    except Exception as exc:
        raise ParsingError(f"Không thể đọc file DOCX '{file_path.name}': {exc}") from exc

    paragraphs = [p.text for p in docx_doc.paragraphs if p.text.strip()]

    blocks: list[dict] = []
    for i in range(0, len(paragraphs), group_size):
        group_text = _clean_text("\n".join(paragraphs[i:i + group_size]))
        if not group_text:
            continue
        blocks.append({
            "document_id": document_id,
            "page": i // group_size + 1,
            "text": group_text,
        })
    return blocks


def _parse_txt(file_path: Path, document_id: int) -> list[dict]:
    """T08 - TXT Parser: đọc toàn bộ file. Thử UTF-8 trước, nếu lỗi encoding
    thì fallback sang latin-1 (errors="ignore") để 1 file lỗi encoding không
    làm crash toàn bộ pipeline khi xử lý hàng loạt tài liệu."""
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("File TXT '%s' không phải UTF-8, fallback sang latin-1.", file_path.name)
        raw_text = file_path.read_text(encoding="latin-1", errors="ignore")

    text = _clean_text(raw_text)
    if not text:
        return []
    return [{
        "document_id": document_id,
        "page": 1,
        "text": text,
    }]


# Bảng dispatch: mỗi đuôi file ứng với 1 parser cụ thể, nhưng người gọi bên
# ngoài (ingestion.py, pipeline.py) KHÔNG cần biết bảng này tồn tại - chỉ
# cần gọi duy nhất parse_document().
_PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".txt": _parse_txt,
}


# ---------------------------------------------------------------------------
# Entrypoint DUY NHẤT - nơi "gộp 2 kiểu parsing làm 1"
# ---------------------------------------------------------------------------

def parse_document(file_path: Path | str, original_filename: str, document_id: int) -> list[dict]:
    """
    Entrypoint chính - dùng chung cho cả PDF lẫn DOCX/TXT (T07 + T08 gộp
    thành 1 hàm). Đây là hàm DUY NHẤT mà ingestion.py/pipeline.py cần gọi.

    Args:
        file_path: đường dẫn file thật trên đĩa (Document.file_path - KHÔNG
            có đuôi mở rộng, xem lưu ý ở đầu file).
        original_filename: tên file gốc lúc upload (Document.original_filename)
            - dùng để xác định loại file cần parser nào.
        document_id: Document.id trong DB, gắn vào từng block để chunking.py
            và bước index sau này biết chunk thuộc tài liệu nào.

    Returns:
        list[dict]: danh sách "parsed block" {document_id, page, text}.

    Raises:
        FileNotFoundError: file vật lý không tồn tại trên đĩa.
        UnsupportedFileTypeError: đuôi file không nằm trong SUPPORTED_EXTENSIONS.
        ParsingError: file tồn tại, đúng định dạng nhưng bị hỏng/không đọc được.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy file vật lý cho document_id={document_id}: '{path}'. "
            f"Có thể file đã bị xoá khỏi storage hoặc DocumentService chưa ghi xong."
        )

    ext = ""
    for candidate in (original_filename, file_path):
        candidate_str = str(candidate).strip()
        if not candidate_str:
            continue
        suffix = Path(candidate_str).suffix.lower()
        if suffix:
            ext = suffix
            break

    parser = _PARSERS.get(ext)
    if parser is None:
        raise UnsupportedFileTypeError(
            f"parsing.py chưa hỗ trợ đuôi file: {ext!r} (original_filename={original_filename!r}). "
            f"Đã hỗ trợ: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    logger.info("Bắt đầu parse document_id=%s (%s)", document_id, original_filename)
    blocks = parser(path, document_id)
    logger.info("Parse xong document_id=%s: %s block.", document_id, len(blocks))
    return blocks


def parse_document_model(document: Document) -> list[dict]:
    """Tiện ích: parse trực tiếp từ 1 ORM `Document` object (lấy từ DB qua
    DocumentRepository của G4) thay vì phải truyền tay 3 field riêng lẻ.
    Dùng trong ingestion.py khi đã query được document."""
    return parse_document(document.file_path, document.original_filename, document.id)


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO)
    print(
        "parsing.py không có file demo mặc định. "
        "Hãy gọi parse_document() với đường dẫn file thật, "
        "hoặc chạy pipeline/test code/test_ingestion.py để test tài liệu trong storage."
    )
