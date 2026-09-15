"""Register test files placed in backend/documents/test and index them.

Usage from the repository root:
    python "backend/app/doc_processing/test code/test_ingestion.py" --owner-id 3

In Docker:
    docker compose exec app python "/app/backend/app/doc_processing/test code/test_ingestion.py" --owner-id 3
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import mimetypes
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.doc_processing.chunking import load_all_chunks
from app.doc_processing.parsing import SUPPORTED_EXTENSIONS
from app.doc_processing.pipeline import run_pipeline_for_document
from app.model.document import Document

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index files dropped into backend/documents.")
    parser.add_argument("--owner-id", type=int, required=True, help="User id owning the dropped files.")
    return parser.parse_args()


async def _index_folder(owner_id: int) -> None:
    storage_root = Path(settings.documents_dir).resolve()
    test_dir = storage_root / "test"
    test_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        existing_paths = set(
            (await db.execute(select(Document.file_path))).scalars().all()
        )
        files = sorted(
            path for path in test_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        if not files:
            print(f"No supported files found in {test_dir}")
            print(f"total_chunks_in_store={len(load_all_chunks())}")
            return

        for source_path in files:
            source_path = source_path.resolve()
            if str(source_path) in existing_paths:
                print(f"SKIP {source_path.name}: already registered")
                continue

            document = Document(
                owner_id=owner_id,
                original_filename=source_path.name,
                content_type=mimetypes.guess_type(source_path.name)[0],
                size_bytes=source_path.stat().st_size,
                file_path=str(source_path),
            )
            db.add(document)
            await db.commit()
            await db.refresh(document)

            try:
                result = await run_pipeline_for_document(document.id, db)
                print(
                    f"{source_path.name}: document_id={document.id} "
                    f"status={result.status.value} chunks={result.chunk_count}"
                )
            except Exception:
                await db.rollback()
                await db.delete(document)
                await db.commit()
                raise

        print(f"total_chunks_in_store={len(load_all_chunks())}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    asyncio.run(_index_folder(args.owner_id))


if __name__ == "__main__":
    main()
