"""
doc_processing.ingestion
=========================
Tầng "ingestion" - đứng giữa chức năng upload file ĐÃ CÓ SẴN
(app/api/v1/endpoints/document.py + app/services/document_service.py, do G4
triển khai) và tầng parsing/chunking của G2.

Trách nhiệm (ứng với phần "validate" của T06 và bước đầu vào của pipeline T11):
    1. Lấy record `Document` từ DB - TÁI SỬ DỤNG DocumentRepository của G4
       (KHÔNG viết lại query riêng) để chỉ có 1 cách duy nhất đọc Document
       trong toàn hệ thống, tránh 2 nhóm code lệch nhau.
    2. Validate file trên đĩa: tồn tại, đúng định dạng hỗ trợ, không rỗng.
    3. Gọi parsing.parse_document_model() để lấy parsed blocks.
    4. Ném lỗi rõ ràng, có ngữ cảnh (document_id, filename) để pipeline.py
       ghi log/status chính xác thay vì để lộ stacktrace chung chung ra ngoài.

Module này KHÔNG phụ thuộc FastAPI (không import Request/HTTPException) để
có thể tái sử dụng ở script CLI, cron job hoặc test độc lập, không chỉ trong
1 request HTTP.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Thêm thư mục `backend` vào sys.path khi chạy script trực tiếp (python backend/app/doc_processing/ingestion.py)
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.doc_processing.parsing import (
    SUPPORTED_EXTENSIONS,
    ParsingError,
    UnsupportedFileTypeError,
    parse_document,
)
from app.model.document import Document
from app.repository.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Lỗi tầng ingestion - lỗi nghiệp vụ xảy ra TRƯỚC khi parse (không tìm
    thấy document, file rỗng, file vật lý bị thiếu...)."""


class DocumentNotFoundError(IngestionError):
    """Không tìm thấy Document trong DB với id tương ứng."""


class DocumentFileMissingError(IngestionError):
    """Record Document tồn tại trong DB nhưng file vật lý trên đĩa bị thiếu
    (đã bị xoá thủ công, lỗi storage, đồng bộ chậm giữa nhiều instance...)."""


class EmptyDocumentError(IngestionError):
    """Parse thành công về mặt kỹ thuật nhưng không trích được bất kỳ đoạn
    text nào (file trống, hoặc PDF toàn trang scan/ảnh không có text layer -
    cần OCR, ngoài phạm vi MVP theo Kick-off Guide)."""


# ---------------------------------------------------------------------------
# Bước 1: lấy Document từ DB
# ---------------------------------------------------------------------------

async def get_document_or_raise(document_id: int, db: AsyncSession) -> Document:
    """Lấy Document theo id, tái sử dụng DocumentRepository
    (app/repository/document_repository.py) mà G4 đã viết cho endpoint
    upload, thay vì tự viết `select(Document)...` riêng ở đây."""
    repo = DocumentRepository(db)
    document = await repo.get_by_id(document_id)
    if document is None:
        raise DocumentNotFoundError(f"Không tìm thấy tài liệu với document_id={document_id} trong DB.")
    return document


# ---------------------------------------------------------------------------
# Bước 2: validate file trên đĩa TRƯỚC khi đưa vào parser
# ---------------------------------------------------------------------------

def validate_document_file(document: Document) -> Path:
    """Kiểm tra file vật lý hợp lệ trước khi gọi parser, tránh để lỗi xảy ra
    sâu bên trong PyMuPDF/python-docx với thông báo khó hiểu cho người debug.

    Trả về Path đã kiểm tra hợp lệ, sẵn sàng truyền cho parsing.parse_document().
    """
    file_path = Path(document.file_path)
    storage_path = Path(settings.documents_dir).resolve() / str(document.owner_id) / str(document.id)
    paths_to_try = [storage_path]
    if file_path != storage_path:
        paths_to_try.append(file_path)

    resolved_path = next((path for path in paths_to_try if path.is_file()), None)
    if resolved_path is None:
        for path in paths_to_try:
            legacy_path = path.with_suffix(Path(document.original_filename).suffix.lower())
            if legacy_path.is_file():
                resolved_path = legacy_path
                break
            candidates = list(path.parent.glob(f"{path.name}.*"))
            if len(candidates) == 1:
                resolved_path = candidates[0]
                break

    if resolved_path is None:
        raise DocumentFileMissingError(
            f"Document id={document.id} ('{document.original_filename}') có record "
            f"trong DB nhưng KHÔNG tìm thấy file trong storage '{storage_path.parent}'."
        )
    file_path = resolved_path

    ext = Path(document.original_filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Document id={document.id} có đuôi file '{ext}' chưa được G2 hỗ trợ parse. "
            f"Đã hỗ trợ: {sorted(SUPPORTED_EXTENSIONS)}. Lưu ý: endpoint upload "
            f"(app/api/v1/endpoints/document.py) đã được đồng bộ ALLOWED_FILE_EXTENSIONS "
            f"theo parsing.SUPPORTED_EXTENSIONS nên trường hợp này chỉ nên xảy ra với "
            f"dữ liệu cũ tạo trước khi tích hợp."
        )

    if document.size_bytes <= 0:
        raise EmptyDocumentError(f"Document id={document.id} có kích thước 0 byte - không có nội dung để xử lý.")

    return file_path


# ---------------------------------------------------------------------------
# Bước 3: metadata cho chunk (T10 - Metadata & Document Versioning)
# ---------------------------------------------------------------------------

def build_document_meta(document: Document) -> dict:
    """Chuẩn hoá metadata gắn vào từng chunk theo chuẩn chunk schema trong
    Kick-off Guide (document_name, department, access_level, version).

    Document model hiện tại (app/model/document.py) CHƯA có field
    department/access_level/version - RBAC (UC-10) và version history
    (UC-17) chưa được model hoá, thuộc phạm vi T10/T20 (G2 phối hợp G4).
    Dùng `getattr(..., default)` để hàm này hoạt động đúng NGAY BÂY GIỜ với
    model hiện tại, và tự động "nhận" field mới nếu G4 bổ sung cột tương ứng
    vào bảng documents sau này - không cần sửa lại parsing/chunking/pipeline.
    """
    return {
        "document_name": document.original_filename,
        "department": getattr(document, "department", None),
        "access_level": getattr(document, "access_level", "internal"),
        "version": getattr(document, "version", 1),
    }


# ---------------------------------------------------------------------------
# Entrypoint chính - dùng bởi pipeline.py (T11)
# ---------------------------------------------------------------------------

async def ingest_document(document_id: int, db: AsyncSession) -> tuple[Document, list[dict]]:
    """
    Entrypoint chính của tầng ingestion.

    Args:
        document_id: id của Document cần ingest (đã được upload trước đó
            qua POST /api/v1/documents/).
        db: AsyncSession hiện tại. LƯU Ý QUAN TRỌNG: khi gọi từ FastAPI
            BackgroundTasks, PHẢI dùng session MỚI mở qua
            app.database.AsyncSessionLocal(), KHÔNG dùng lại session của
            request gốc vì session đó đã bị đóng ngay sau khi response được
            trả về (xem pipeline.run_pipeline_background).

    Returns:
        (document, parsed_blocks): document ORM object (để lấy thêm metadata
        như owner_id nếu cần) và list parsed block sẵn sàng cho chunking.py.

    Raises:
        DocumentNotFoundError, DocumentFileMissingError, UnsupportedFileTypeError,
        EmptyDocumentError, ParsingError.
    """
    document = await get_document_or_raise(document_id, db)
    file_path = validate_document_file(document)

    logger.info(
        "Ingestion: bắt đầu xử lý document_id=%s file='%s' owner_id=%s path='%s'",
        document.id, document.original_filename, document.owner_id, file_path,
    )

    try:
        parse_name = document.original_filename
        if Path(document.file_path).suffix == "" and file_path.suffix:
            parse_name = file_path.name
        parsed_blocks = parse_document(file_path, parse_name, document.id)
    except (ParsingError, UnsupportedFileTypeError):
        raise
    except Exception as exc:  # bắt mọi lỗi không lường trước phát sinh từ thư viện parser
        raise ParsingError(
            f"Lỗi không xác định khi parse document_id={document.id} "
            f"('{document.original_filename}'): {exc}"
        ) from exc

    if not parsed_blocks:
        raise EmptyDocumentError(
            f"Document id={document.id} ('{document.original_filename}') được parse "
            f"thành công nhưng không có nội dung text nào (có thể là PDF scan/ảnh "
            f"chưa OCR, hoặc file trống)."
        )

    logger.info("Ingestion: document_id=%s parse xong, %s block.", document.id, len(parsed_blocks))
    return document, parsed_blocks


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO)
    print(
        "ingestion.py không có chế độ chạy độc lập với tài liệu thử nghiệm. "
        "Hãy dùng API upload hoặc chạy: "
        "python \"backend/app/doc_processing/test code/test_ingestion.py\" --owner-id <id>"
    )
