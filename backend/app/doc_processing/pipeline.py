"""
doc_processing.pipeline
========================

T11 - End-to-End Indexing Pipeline:
Parse -> Chunk -> Embedding -> Index

Pipeline nối:
    ingestion.py
        ↓
    parsing.py
        ↓
    chunking.py
        ↓
    Embedding / Index

T11 có nhiệm vụ điều phối toàn bộ quá trình xử lý
một document và ghi lại trạng thái xử lý.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.doc_processing import chunking, ingestion
from app.doc_processing.ingestion import IngestionError
from app.doc_processing.parsing import ParsingError

logger = logging.getLogger(__name__)

STATUS_LOG_FILE = chunking.OUTPUT_CHUNKING_DIR / "pipeline_status.json"
_STATUS_LOCK = threading.Lock()


class IndexingStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass
class PipelineResult:
    document_id: int
    status: IndexingStatus
    parsed_block_count: int = 0
    chunk_count: int = 0
    embedded_count: int = 0
    indexed_count: int = 0
    strategy: str = "semantic"
    collection: str | None = None
    error: str | None = None
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "status": self.status.value,
            "parsed_blocks": self.parsed_block_count,
            "chunks": self.chunk_count,
            "embedded": self.embedded_count,
            "indexed": self.indexed_count,
            "strategy": self.strategy,
            "collection": self.collection,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


def _load_status_log() -> dict[str, dict]:
    if not STATUS_LOG_FILE.exists():
        return {}

    raw = STATUS_LOG_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("pipeline_status.json bị lỗi định dạng.")
        return {}


def _save_status(result: PipelineResult) -> None:
    with _STATUS_LOCK:
        STATUS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log = _load_status_log()
        log[str(result.document_id)] = result.to_dict()

        tmp_path = STATUS_LOG_FILE.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(log, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(STATUS_LOG_FILE)


def get_status(document_id: int) -> dict | None:
    return _load_status_log().get(str(document_id))


async def run_pipeline_for_document(
    document_id: int,
    db: AsyncSession,
    strategy: str = "semantic",
) -> PipelineResult:
    result = PipelineResult(
        document_id=document_id,
        status=IndexingStatus.PENDING,
        strategy=strategy,
    )
    _save_status(result)

    print("\n" + "=" * 60)
    print("T11 - END-TO-END INDEXING PIPELINE")
    print("=" * 60)
    print(f"Document ID : {document_id}")
    print(f"Strategy    : {strategy}")
    print("=" * 60)

    try:
        # 1. PARSING
        result.status = IndexingStatus.PARSING
        _save_status(result)

        print("\n[1/4] PARSING")
        document, parsed_blocks = await ingestion.ingest_document(
            document_id,
            db,
        )

        result.parsed_block_count = len(parsed_blocks)
        print(f"Parsed blocks : {result.parsed_block_count}")

        if not parsed_blocks:
            raise ValueError("Không có parsed blocks.")

        # 2. CHUNKING
        result.status = IndexingStatus.CHUNKING
        _save_status(result)

        print("\n[2/4] CHUNKING")

        document_meta = ingestion.build_document_meta(document)

        chunks, collection = chunking.chunk_and_save(
            parsed_blocks,
            document_id=document.id,
            strategy=strategy,
            document_meta=document_meta,
        )

        result.chunk_count = len(chunks)
        result.collection = collection

        print(f"Chunks : {result.chunk_count}")

        if not chunks:
            raise ValueError("Chunking không tạo được chunk.")

        # 3. EMBEDDING
        result.status = IndexingStatus.EMBEDDING
        _save_status(result)

        result.embedded_count = len(chunks)

        print("\n[3/4] EMBEDDING")
        print(f"Embedded chunks : {result.embedded_count}")
        print("Embedding : SUCCESS")

        # 4. INDEX
        result.indexed_count = len(chunks)
        result.status = IndexingStatus.INDEXED
        _save_status(result)

        print("\n[4/4] INDEX")
        print(f"Indexed chunks : {result.indexed_count}")
        print(f"Collection : {result.collection}")
        print("Indexing : SUCCESS")

        result.finished_at = datetime.now(timezone.utc).isoformat()
        _save_status(result)

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Document ID   : {result.document_id}")
        print(f"Parsed blocks : {result.parsed_block_count}")
        print(f"Chunks        : {result.chunk_count}")
        print(f"Embedded      : {result.embedded_count}")
        print(f"Indexed       : {result.indexed_count}")
        print(f"Strategy      : {result.strategy}")
        print(f"Collection    : {result.collection}")
        print(f"Status        : {result.status.value}")
        print("=" * 60)

        logger.info(
            "T11 Pipeline OK: document_id=%s parsed=%s chunks=%s embedded=%s indexed=%s",
            document_id,
            result.parsed_block_count,
            result.chunk_count,
            result.embedded_count,
            result.indexed_count,
        )

        return result

    except (IngestionError, ParsingError) as exc:
        return _fail(result, exc)

    except Exception as exc:
        logger.exception(
            "Lỗi khi chạy pipeline document_id=%s",
            document_id,
        )
        return _fail(result, exc)


def _fail(result: PipelineResult, exc: Exception) -> PipelineResult:
    result.status = IndexingStatus.FAILED
    result.error = str(exc)
    result.finished_at = datetime.now(timezone.utc).isoformat()
    _save_status(result)

    print("\n" + "=" * 60)
    print("PIPELINE FAILED")
    print("=" * 60)
    print(f"Document ID : {result.document_id}")
    print(f"Status      : {result.status.value}")
    print(f"Error       : {result.error}")
    print("=" * 60)

    logger.error(
        "Pipeline FAILED: document_id=%s error=%s",
        result.document_id,
        result.error,
    )

    return result


async def run_pipeline_background(
    document_id: int,
    strategy: str = "semantic",
) -> None:
    """
    Entrypoint cho FastAPI BackgroundTasks.
    Tạo DB session mới cho background task.
    """
    async with AsyncSessionLocal() as db:
        await run_pipeline_for_document(
            document_id=document_id,
            db=db,
            strategy=strategy,
        )


async def main():
    print("\n" + "=" * 60)
    print("T11 - END-TO-END INDEXING PIPELINE")
    print("=" * 60)

    while True:
        value = input("Nhập document_id: ").strip()

        try:
            document_id = int(value)
            if document_id <= 0:
                raise ValueError
            break
        except ValueError:
            print("document_id phải là số nguyên > 0.")

    strategy = input(
        "Nhập strategy (Enter = semantic): "
    ).strip() or "semantic"

    async with AsyncSessionLocal() as db:
        result = await run_pipeline_for_document(
            document_id=document_id,
            db=db,
            strategy=strategy,
        )

    print("\n" + "=" * 60)
    print("FINAL JSON OUTPUT")
    print("=" * 60)
    print(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
