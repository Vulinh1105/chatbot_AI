"""Reset test document data.

Run from the repository root:
    python "backend/app/doc_processing/test code/reset_records.py" --yes

Run in Docker:
    docker compose exec app python "/app/backend/app/doc_processing/test code/reset_records.py" --yes

This removes document rows whose files are under backend/documents/test_documents,
their chunks and status entries, and physical files under that test folder. Users,
chats, and documents/files outside the test folder are not changed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.doc_processing.chunking import CHUNKS_STORE_FILE, delete_chunks_by_document, load_all_chunks
from app.doc_processing.pipeline import STATUS_LOG_FILE
from app.model.document import Document


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset document-processing test data.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion of all document records and test processing data.",
    )
    return parser.parse_args()


def _test_dir() -> Path:
    return Path(settings.documents_dir).resolve() / "test_documents"


def _is_test_file(file_path: str) -> bool:
    try:
        Path(file_path).resolve().relative_to(_test_dir())
    except ValueError:
        return False
    return True


def _clear_test_files() -> int:
    test_dir = _test_dir()
    if not test_dir.exists():
        return 0

    removed = 0
    for path in test_dir.iterdir():
        if path.is_file() or path.is_symlink():
            path.unlink()
            removed += 1
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                    removed += 1
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            path.rmdir()
    return removed


def _clear_processing_outputs(document_ids: set[int]) -> int:
    removed = 0
    for document_id in document_ids:
        delete_chunks_by_document(document_id)

    if CHUNKS_STORE_FILE.exists() and document_ids and not load_all_chunks():
        CHUNKS_STORE_FILE.unlink()
        removed += 1

    if STATUS_LOG_FILE.exists() and document_ids:
        try:
            status_log = json.loads(STATUS_LOG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status_log = {}
        remaining = {
            document_id: status
            for document_id, status in status_log.items()
            if str(document_id) not in {str(value) for value in document_ids}
        }
        if remaining:
            STATUS_LOG_FILE.write_text(
                json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            STATUS_LOG_FILE.unlink()
        removed += 1
    return removed


async def _reset() -> None:
    async with AsyncSessionLocal() as db:
        documents = (await db.execute(select(Document))).scalars().all()
        test_documents = [document for document in documents if _is_test_file(document.file_path)]
        document_ids = {document.id for document in test_documents}
        document_count = len(test_documents)
        if document_ids:
            await db.execute(delete(Document).where(Document.id.in_(document_ids)))
        await db.commit()

    removed_outputs = _clear_processing_outputs(document_ids)
    removed_test_files = _clear_test_files()
    print(f"document_records_deleted={document_count or 0}")
    print(f"processing_output_files_deleted={removed_outputs}")
    print(f"test_files_deleted={removed_test_files}")


def main() -> None:
    args = _parse_args()
    if not args.yes:
        raise SystemExit(
            "Nothing deleted. Re-run with --yes to remove document records, "
            "processing outputs, and files in backend/documents/test_documents."
        )
    asyncio.run(_reset())


if __name__ == "__main__":
    main()
