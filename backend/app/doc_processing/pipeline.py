"""
doc_processing.pipeline
========================
T11 - End-to-End Indexing Pipeline: Parse -> Chunk -> (Embedding) -> Index,
kèm tracking status/log cho từng document.

Đây là "nhạc trưởng" nối:
    ingestion.py (validate + gọi parsing.py) -> chunking.py (cắt & lưu vào
    doc/chunks.json) -> (tuỳ chọn, an toàn) tầng embedding của G3
    (app/ai_agent/embeddings.py).

Nguyên tắc tích hợp liên nhóm để HẠN CHẾ LỖI: pipeline của G2 KHÔNG được sập
chỉ vì module của G3 (khác nhóm, có thể chưa cài đủ package hoặc chưa có
OPENAI_API_KEY) gặp lỗi. Việc gọi sang G3 luôn là "best-effort" - lazy
import + try/except riêng, tách biệt hoàn toàn khỏi kết quả chunking (vốn đã
được lưu an toàn vào chunks.json trước đó). Tương tự nguyên tắc "Frontend
không cần chờ backend" trong Kick-off Guide, ở đây G2 không cần chờ G3.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# Thêm thư mục `backend` vào sys.path khi chạy script trực tiếp (python backend/app/doc_processing/pipeline.py)
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.doc_processing import chunking, ingestion
from app.doc_processing.ingestion import IngestionError
from app.doc_processing.parsing import ParsingError

logger = logging.getLogger(__name__)

# File log trạng thái indexing, đặt cùng thư mục doc/ với chunks.json.
# Document model (G4) hiện CHƯA có cột `status` (xem app/model/document.py),
# nên G2 tự quản lý trạng thái ở đây để KHÔNG phải chờ G4 chạy Alembic
# migration mới demo được T11. Khi G4 bổ sung cột status cho bảng documents
# (T22 - Document Management API), có thể đồng bộ 2 bên hoặc thay hẳn bằng
# DB; file log này vẫn hữu ích để debug lỗi indexing trong lúc phát triển.
STATUS_LOG_FILE = chunking.OUTPUT_CHUNKING_DIR / "pipeline_status.json"
_STATUS_LOCK = threading.Lock()


class IndexingStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    CHUNKED = "chunked"    # G2 hoàn tất - đã có trong chunks.json
    EMBEDDING = "embedding"
    INDEXED = "indexed"    # G3 đã embedding xong - sẵn sàng semantic search
    FAILED = "failed"


@dataclass
class PipelineResult:
    document_id: int
    status: IndexingStatus
    chunk_count: int = 0
    strategy: str = "fixed_overlap"
    error: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "status": self.status.value,
            "chunk_count": self.chunk_count,
            "strategy": self.strategy,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


# ---------------------------------------------------------------------------
# Status log dạng file JSON - cùng cách tiếp cận với chunking.py (đơn giản,
# không cần thêm bảng DB mới để demo được T11 ngay từ tuần 3-4).
# ---------------------------------------------------------------------------

def _load_status_log() -> dict[str, dict]:
    if not STATUS_LOG_FILE.exists():
        return {}
    raw = STATUS_LOG_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("pipeline_status.json bị lỗi định dạng - reset log trạng thái.")
        return {}


def _save_status(result: PipelineResult) -> None:
    with _STATUS_LOCK:
        STATUS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log = _load_status_log()
        log[str(result.document_id)] = result.to_dict()
        tmp_path = STATUS_LOG_FILE.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(STATUS_LOG_FILE)


def get_status(document_id: int) -> dict | None:
    """Cho các nhóm khác (G4 - Document Management API T22, G5 - hiển thị
    trạng thái indexing T27) tra cứu trạng thái xử lý của 1 document mà
    không cần tự đọc/parse trực tiếp file JSON."""
    return _load_status_log().get(str(document_id))


# ---------------------------------------------------------------------------
# Pipeline chính
# ---------------------------------------------------------------------------

# Bật/tắt bước gọi sang embedding của G3 qua biến môi trường, MẶC ĐỊNH TẮT vì
# app/ai_agent/embeddings.py hiện cần OPENAI_API_KEY và các package
# (langchain, faiss) có thể chưa được cài / khác requirements.txt của G2.
_ENABLE_AUTO_EMBEDDING = os.getenv("ENABLE_AUTO_EMBEDDING", "false").lower() == "true"


async def run_pipeline_for_document(
    document_id: int,
    db: AsyncSession,
    strategy: str = "fixed_overlap",
) -> PipelineResult:
    """
    Chạy toàn bộ luồng Parse -> Chunk -> (Embedding) -> Index cho 1
    document, ghi log trạng thái ở từng bước để debug khi lỗi (T11 DoD:
    "logging lỗi rõ ràng").

    Đây là hàm nên được viết unit/integration test (T11 DoD: "1 lệnh/API
    đưa document đến searchable index").
    """
    result = PipelineResult(document_id=document_id, status=IndexingStatus.PENDING, strategy=strategy)
    _save_status(result)

    try:
        # --- Bước 1+2: ingestion (validate + parse), tái sử dụng ingestion.py ---
        result.status = IndexingStatus.PARSING
        _save_status(result)
        document, parsed_blocks = await ingestion.ingest_document(document_id, db)

        # --- Bước 3: chunking + lưu liên tục vào doc/chunks.json ---
        result.status = IndexingStatus.CHUNKING
        _save_status(result)
        document_meta = ingestion.build_document_meta(document)
        chunks, _ = chunking.chunk_and_save(
            parsed_blocks,
            document_id=document.id,
            strategy=strategy,
            document_meta=document_meta,
        )
        result.chunk_count = len(chunks)
        result.status = IndexingStatus.CHUNKED
        _save_status(result)

        # --- Bước 4 (tuỳ chọn, an toàn): bàn giao cho embedding layer của G3 ---
        if _ENABLE_AUTO_EMBEDDING:
            result.status = IndexingStatus.EMBEDDING
            _save_status(result)
            _try_trigger_embedding(chunks)
            result.status = IndexingStatus.INDEXED
        # Nếu không bật auto-embedding, CHUNKED vẫn là kết quả THÀNH CÔNG của
        # G2 - G3 có thể tự chạy embedding riêng (batch job) bằng cách đọc
        # thẳng chunks.json qua chunking.load_all_chunks(), không phụ thuộc
        # vào việc pipeline này có gọi trực tiếp sang ai_agent hay không.

        result.finished_at = datetime.now(timezone.utc).isoformat()
        _save_status(result)
        logger.info(
            "Pipeline OK: document_id=%s status=%s chunk_count=%s",
            document_id, result.status.value, result.chunk_count,
        )
        return result

    except (IngestionError, ParsingError) as exc:
        return _fail(result, exc)
    except Exception as exc:  # an toàn tối đa: không để lỗi lạ làm crash background task
        logger.exception("Lỗi không xác định khi chạy pipeline cho document_id=%s", document_id)
        return _fail(result, exc)


def _fail(result: PipelineResult, exc: Exception) -> PipelineResult:
    result.status = IndexingStatus.FAILED
    result.error = str(exc)
    result.finished_at = datetime.now(timezone.utc).isoformat()
    _save_status(result)
    logger.error("Pipeline FAILED: document_id=%s lỗi=%s", result.document_id, result.error)
    return result


def _try_trigger_embedding(chunks: list[dict]) -> None:
    """Gọi sang app/ai_agent/embeddings.py của G3 theo kiểu "best-effort":
    import TRỄ (lazy import) ngay bên trong hàm để module pipeline.py của G2
    KHÔNG bị lỗi ngay từ lúc import file nếu G3 chưa cài langchain/faiss
    hoặc chưa cấu hình OPENAI_API_KEY. Mọi lỗi ở bước này chỉ log cảnh báo,
    KHÔNG làm mất kết quả chunking đã lưu thành công ở bước 3."""
    try:
        from langchain_core.documents import Document as LangchainDocument

        from app.ai_agent.embeddings import create_vector_db

        docs = [
            LangchainDocument(
                page_content=c["content"],
                metadata={
                    "chunk_id": c["chunk_id"],
                    "document_id": c["document_id"],
                    "page": c["page"],
                    "department": c.get("department"),
                    "access_level": c.get("access_level"),
                },
            )
            for c in chunks
        ]
        create_vector_db(docs)
    except Exception as exc:  # cố ý bắt rộng - đây chỉ là bước tuỳ chọn, không phải core flow của G2
        logger.warning(
            "Không thể chạy embedding tự động (module G3 có thể chưa sẵn sàng): %s. "
            "Chunk vẫn đã được lưu an toàn vào doc/chunks.json.", exc,
        )


# ---------------------------------------------------------------------------
# Wrapper dùng cho FastAPI BackgroundTasks (xem tích hợp trong
# app/api/v1/endpoints/document.py - hàm upload_document/replace_document)
# ---------------------------------------------------------------------------

async def run_pipeline_background(document_id: int, strategy: str = "fixed_overlap") -> None:
    """
    Entrypoint dành riêng cho `BackgroundTasks.add_task(...)`.

    QUAN TRỌNG: session DB của request gốc (Depends(get_db)) sẽ bị đóng ngay
    sau khi response được trả về cho client - TRƯỚC KHI background task này
    kịp chạy xong. Vì vậy hàm này tự mở một AsyncSession MỚI qua
    `AsyncSessionLocal` (app/database.py) thay vì nhận session từ endpoint,
    tránh lỗi "This session is closed" rất khó debug khi chạy nền.
    """
    async with AsyncSessionLocal() as db:
        await run_pipeline_for_document(document_id, db, strategy=strategy)


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO)
    print(
        "pipeline.py không có document_id demo mặc định. "
        "Hãy chạy API upload hoặc test code/test_ingestion.py để xử lý tài liệu thật."
    )
