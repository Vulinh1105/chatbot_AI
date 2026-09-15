"""Reset test document data.

Run from the repository root:
    python "backend/app/doc_processing/test code/reset_records.py" --yes

Run in Docker:
    docker compose exec app python "/app/backend/app/doc_processing/test code/reset_records.py" --yes

This removes all rows from the documents table, both JSON processing outputs,
and physical files under backend/documents/test. Users, chats, and files outside
the test folder are not changed.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import delete, func, select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.doc_processing.chunking import CHUNKS_STORE_FILE
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


def _clear_test_files() -> int:
    test_dir = Path(settings.documents_dir).resolve() / "test"
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


def _clear_processing_outputs() -> int:
    removed = 0
    for path in (CHUNKS_STORE_FILE, STATUS_LOG_FILE):
        if path.exists():
            path.unlink()
            removed += 1
    return removed


async def _reset() -> None:
    async with AsyncSessionLocal() as db:
        document_count = await db.scalar(select(func.count()).select_from(Document))
        await db.execute(delete(Document))
        await db.commit()

    removed_outputs = _clear_processing_outputs()
    removed_test_files = _clear_test_files()
    print(f"document_records_deleted={document_count or 0}")
    print(f"processing_output_files_deleted={removed_outputs}")
    print(f"test_files_deleted={removed_test_files}")


def main() -> None:
    args = _parse_args()
    if not args.yes:
        raise SystemExit(
            "Nothing deleted. Re-run with --yes to remove document records, "
            "processing outputs, and files in backend/documents/test."
        )
    asyncio.run(_reset())


if __name__ == "__main__":
    main()
