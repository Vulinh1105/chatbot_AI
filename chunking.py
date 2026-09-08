"""
chunking.py
-----------
T14 - Chunking MVP.

Nhận output từ parsing.py (dict {filename: raw_text}), dùng Langchain
để cắt nhỏ từng văn bản thành các đoạn (chunk) nhỏ hơn, phù hợp để
đưa vào bước embedding/vector store sau này.

Mỗi chunk được gắn kèm metadata: tên file gốc + chỉ số chunk, để sau
này còn biết chunk đó đến từ đâu.

Cách chạy thử độc lập (đọc trực tiếp từ backend/data/documents/):
    python chunking.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from parsing import DEFAULT_DOCS_DIR, parse_documents_in_dir

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Cấu hình mặc định cho MVP - có thể tinh chỉnh sau khi thử nghiệm thực tế.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


@dataclass
class Chunk:
    """Một đoạn văn bản đã được cắt nhỏ, kèm metadata để truy vết nguồn gốc."""

    text: str
    source_file: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source_file": self.source_file,
            "chunk_index": self.chunk_index,
            **self.metadata,
        }


def get_text_splitter(
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """Tạo splitter dùng chung, ưu tiên tách theo đoạn văn -> câu -> từ."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_text(
    text: str,
    source_file: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Cắt 1 văn bản thành danh sách Chunk."""
    splitter = get_text_splitter(chunk_size, chunk_overlap)
    raw_chunks = splitter.split_text(text)

    return [
        Chunk(text=chunk, source_file=source_file, chunk_index=i)
        for i, chunk in enumerate(raw_chunks)
    ]


def chunk_documents(
    documents: dict[str, str],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Nhận dict {filename: raw_text} (đầu ra của parsing.parse_documents_in_dir)
    và trả về danh sách tất cả các Chunk của tất cả các file.
    """
    all_chunks: list[Chunk] = []

    for filename, text in documents.items():
        if not text or not text.strip():
            logger.warning("Bỏ qua %s: text rỗng.", filename)
            continue

        chunks = chunk_text(text, filename, chunk_size, chunk_overlap)
        logger.info("%s -> %d chunk", filename, len(chunks))
        all_chunks.extend(chunks)

    logger.info("Tổng cộng: %d chunk từ %d file.", len(all_chunks), len(documents))
    return all_chunks


def run_pipeline(
    docs_dir: Path | str = DEFAULT_DOCS_DIR,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Chạy end-to-end: parsing.py -> chunking.py, trả về list Chunk."""
    documents = parse_documents_in_dir(docs_dir)
    if not documents:
        logger.warning("Không có văn bản nào để chunk.")
        return []
    return chunk_documents(documents, chunk_size, chunk_overlap)


if __name__ == "__main__":
    chunks = run_pipeline()
    for c in chunks[:5]:
        preview = c.text[:150].replace("\n", " ")
        print(f"\n--- {c.source_file} [chunk {c.chunk_index}] ({len(c.text)} ký tự) ---")
        print(preview + ("..." if len(c.text) > 150 else ""))

    if len(chunks) > 5:
        print(f"\n... và {len(chunks) - 5} chunk khác.")