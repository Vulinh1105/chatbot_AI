"""
doc_processing.chunking
========================
T09 - Chunking Strategy: nhận list "parsed block" (output của
parsing.parse_document()) và cắt thành chunks theo 1 trong 2 chiến lược có
thể so sánh với nhau, sau đó GỘP & LƯU LIÊN TỤC vào 1 kho JSON DUY NHẤT:
`app/doc_processing/doc/chunks.json`.

Vì sao dùng 1 file chunks.json chung cho TẤT CẢ tài liệu (thay vì mỗi
document 1 file riêng như `{document_id}_chunking.json`):
    - G3 (Retrieval) cần trả lời NHIỀU câu hỏi khác nhau, có thể liên quan
      đến NHIỀU tài liệu cùng lúc (vd so sánh nội dung 2 file). Nếu chunk
      nằm rải rác nhiều file JSON, G3 phải tự loop/gộp lại mỗi lần truy vấn.
    - Gộp vào 1 kho chung, sắp xếp liên tục theo (document_id, page,
      chunk_index) giúp retrieval đọc 1 lần, luôn có đủ ngữ cảnh liền mạch
      để trả lời nhiều câu hỏi về sau mà không bỏ sót tài liệu nào.

Lưu ý về RBAC: app/model/document.py hiện CHƯA có field department/
access_level (RBAC/versioning chưa được model hoá - thuộc T10/T20, do
G2 phối hợp G4). Chunk ở đây vẫn có sẵn 2 field này (mặc định None/"internal")
để không phá schema khi G4 bổ sung RBAC thật sự sau này - xem
ingestion.build_document_meta().
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Thêm thư mục `backend` vào sys.path khi chạy script trực tiếp (python backend/app/doc_processing/chunking.py)
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

logger = logging.getLogger(__name__)

# backend/app/doc_processing/chunking.py -> parent = doc_processing/
OUTPUT_CHUNKING_DIR = Path(__file__).resolve().parent / "doc"

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "chatbot_documents_v2")
# Giữ hằng số để các script dọn dữ liệu cũ không bị lỗi import. Chunk mới
# không còn được ghi vào file này.
CHUNKS_STORE_FILE = OUTPUT_CHUNKING_DIR / "chunks.json"


def _qdrant_url() -> str:
    return os.getenv(
        "QDRANT_URL",
        f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}",
    )


def _qdrant_api_key() -> str | None:
    value = os.getenv("QDRANT_API_KEY")
    return None if value in {None, "", "None", "null"} else value

# Nhiều request upload có thể chạy song song (FastAPI BackgroundTasks), nếu
# không khoá ghi file, 2 tiến trình có thể ghi đè lẫn nhau -> mất dữ liệu.
# Lock này bảo vệ trong phạm vi 1 worker process của Python; nếu G6 deploy
# nhiều worker process (vd Gunicorn -w N) cần thay bằng file lock hệ điều
# hành hoặc chuyển hẳn kho chunk sang DB/pgvector thật.
_STORE_LOCK = threading.Lock()


class ChunkingError(Exception):
    """Lỗi phát sinh khi cắt chunk hoặc đọc/ghi kho chunks.json."""


# ---------------------------------------------------------------------------
# 2 chiến lược chunking (T09 yêu cầu so sánh >= 2 chiến lược, giữ source metadata)
# ---------------------------------------------------------------------------

def _split_fixed_overlap(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chiến lược 1 - fixed_overlap: cắt cố định theo số ký tự, có overlap
    giữa 2 chunk liền kề để không mất ngữ cảnh ở ranh giới. Đơn giản, nhanh,
    dùng làm baseline, nhưng có thể cắt ngang câu."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size phải lớn hơn overlap để tránh vòng lặp vô hạn.")

    pieces: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= text_len:
            break
        start = end - overlap
    return pieces


def _split_recursive_paragraph(text: str, max_chars: int = 500) -> list[str]:
    """Chiến lược 2 - recursive_paragraph: cắt theo đoạn văn, gộp các đoạn
    ngắn lại cho đến gần max_chars. Giữ trọn ngữ nghĩa từng đoạn tốt hơn
    chiến lược 1 (không cắt ngang câu) nhưng kích thước chunk không đều."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    pieces: list[str] = []
    buffer = ""
    for p in paragraphs:
        candidate = f"{buffer}\n{p}".strip() if buffer else p
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                pieces.append(buffer)
            # Nếu 1 đoạn văn đơn lẻ đã dài hơn max_chars, vẫn giữ nguyên
            # trọn đoạn đó thành 1 chunk riêng (không cắt bỏ nội dung).
            buffer = p
    if buffer:
        pieces.append(buffer)
    return pieces

def _split_semantic(text: str) -> list[str]:
    """
    Chiến lược Semantic Chunking:
    Chia văn bản dựa trên sự thay đổi ngữ nghĩa giữa các câu,
    thay vì chỉ dựa trên số lượng ký tự.
    """
    import math

    from langchain_openai import OpenAIEmbeddings

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?。！？])\s+", text.strip())
        if sentence.strip()
    ]
    if len(sentences) <= 1:
        return sentences

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectors = embeddings.embed_documents(sentences)
    distances = []
    for current, following in zip(vectors, vectors[1:]):
        current_norm = math.sqrt(sum(value * value for value in current))
        following_norm = math.sqrt(sum(value * value for value in following))
        if current_norm == 0 or following_norm == 0:
            distances.append(1.0)
            continue
        similarity = sum(a * b for a, b in zip(current, following)) / (
            current_norm * following_norm
        )
        distances.append(1 - similarity)

    sorted_distances = sorted(distances)
    percentile_index = (len(sorted_distances) - 1) * 0.95
    lower_index = math.floor(percentile_index)
    upper_index = math.ceil(percentile_index)
    if lower_index == upper_index:
        threshold = sorted_distances[lower_index]
    else:
        fraction = percentile_index - lower_index
        threshold = sorted_distances[lower_index] + fraction * (
            sorted_distances[upper_index] - sorted_distances[lower_index]
        )

    chunks = []
    current_chunk = [sentences[0]]
    for index, sentence in enumerate(sentences[1:]):
        current_chunk.append(sentence)
        if distances[index] >= threshold:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


_STRATEGIES = {
    "fixed_overlap": _split_fixed_overlap,
    "recursive_paragraph": _split_recursive_paragraph,
    "semantic": _split_semantic,
}


# ---------------------------------------------------------------------------
# Hàm chunk chính - PURE FUNCTION (không I/O) để dễ viết unit test theo DoD của T09
# ---------------------------------------------------------------------------

def chunk_blocks(
    parsed_blocks: list[dict],
    strategy: str = "semantic",
    document_meta: dict | None = None,
    **strategy_kwargs,
) -> list[dict]:
    """
    Args:
        parsed_blocks: output của parsing.parse_document() - mỗi block có
            {document_id, page, text}.
        strategy: "semantic", "fixed_overlap" hoặc "recursive_paragraph".
        document_meta: metadata bổ sung theo chuẩn chunk schema trong
            Kick-off Guide, ví dụ:
            {"department": "HR", "access_level": "internal", "version": 1,
             "document_name": "HR_Policy.pdf"}.
            G4 sẽ dùng "department"/"access_level" để lọc chunk trái quyền
            TRƯỚC khi đưa context cho LLM (security scenario bắt buộc trong
            Kick-off Guide). Nếu không truyền, dùng giá trị mặc định an toàn.
        **strategy_kwargs: tham số thêm cho chiến lược (vd chunk_size,
            overlap, max_chars) - dùng khi cần thực nghiệm so sánh tham số.

    Returns:
        list[dict]: mỗi chunk có đủ field theo chunk schema thống nhất toàn dự án
        (chunk_id, document_id, content, page, chunk_index, char_count,
        strategy, department, access_level, version, document_name, created_at).
    """
    if strategy not in _STRATEGIES:
        raise ValueError(f"Chiến lược không tồn tại: {strategy!r}. Chọn 1 trong {list(_STRATEGIES)}")

    document_meta = document_meta or {}
    split_fn = _STRATEGIES[strategy]

    chunks: list[dict] = []
    for block in parsed_blocks:
        pieces = split_fn(block["text"], **strategy_kwargs)
        for i, piece in enumerate(pieces):
            chunks.append({
                "chunk_id": f"doc{block['document_id']}_p{block['page']}_c{i:03d}_{strategy}",
                "document_id": block["document_id"],
                "content": piece,
                "page": block["page"],
                "chunk_index": i,
                "char_count": len(piece),
                "strategy": strategy,
                "department": document_meta.get("department"),
                "access_level": document_meta.get("access_level", "internal"),
                "version": document_meta.get("version", 1),
                "document_name": document_meta.get("document_name"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    return chunks


# ---------------------------------------------------------------------------
# I/O: lưu chunk vào Qdrant
# ---------------------------------------------------------------------------

def load_all_chunks() -> list[dict]:
    """Đọc payload chunk từ Qdrant để phục vụ keyword retrieval."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=_qdrant_url(), api_key=_qdrant_api_key())
        if not client.collection_exists(QDRANT_COLLECTION):
            return []
        points, _ = client.scroll(QDRANT_COLLECTION, limit=10000, with_payload=True, with_vectors=False)
        chunks = []
        for point in points:
            payload = point.payload or {}
            metadata = payload.get("metadata", {})
            content = payload.get("page_content", payload.get("content", ""))
            chunks.append({"content": content, **metadata})
        return chunks
    except Exception as exc:
        logger.warning("Không thể đọc chunk từ Qdrant: %s", exc)
        return []


def _delete_qdrant_document(document_id: int) -> None:
    from qdrant_client import QdrantClient, models

    client = QdrantClient(url=_qdrant_url(), api_key=_qdrant_api_key())
    if client.collection_exists(QDRANT_COLLECTION):
        client.delete(
            QDRANT_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="metadata.document_id", match=models.MatchValue(value=document_id))]
                )
            ),
        )


def save_chunks(chunks: list[dict], document_id: int) -> str:
    """
    Xóa các point cũ của tài liệu rồi embedding và upsert chunk mới vào Qdrant.
    `content` được đưa vào page_content; các trường còn lại trở thành payload
    metadata của point.
    """
    with _STORE_LOCK:
        from langchain_core.documents import Document
        from app.ai_agent.embeddings import create_vector_db

        _delete_qdrant_document(document_id)
        docs = [
            Document(
                page_content=chunk["content"],
                metadata={key: value for key, value in chunk.items() if key != "content"},
            )
            for chunk in chunks
        ]
        if docs:
            create_vector_db(docs)
        logger.info(
            "Đã index %s chunk cho document_id=%s vào collection '%s'.",
            len(chunks), document_id, QDRANT_COLLECTION,
        )
        return QDRANT_COLLECTION


def delete_chunks_by_document(document_id: int) -> int:
    """Xoá toàn bộ chunk của 1 document_id khỏi kho chung - gọi khi tài liệu
    bị xoá (UC-16 "Xóa tài liệu") để tránh chatbot vẫn trả lời dựa trên tài
    liệu Admin đã xoá (dữ liệu "mồ côi"). Trả về số chunk đã xoá."""
    with _STORE_LOCK:
        before = [chunk for chunk in load_all_chunks() if chunk.get("document_id") == document_id]
        _delete_qdrant_document(document_id)
        if before:
            logger.info("Đã xoá %s chunk của document_id=%s khỏi Qdrant.", len(before), document_id)
        return len(before)


def chunk_and_save(
    parsed_blocks: list[dict],
    document_id: int,
    strategy: str = "semantic",
    document_meta: dict | None = None,
    **strategy_kwargs,
 ) -> tuple[list[dict], str]:
    """Tiện ích gộp: chunk rồi lưu luôn vào kho chung - dùng trong
    pipeline.py cho luồng end-to-end (T11)."""
    chunks = chunk_blocks(parsed_blocks, strategy=strategy, document_meta=document_meta, **strategy_kwargs)
    path = save_chunks(chunks, document_id=document_id)
    return chunks, path


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO)
    fake_blocks = [{
        "document_id": 1,
        "page": 1,
        "text": "Nhan vien thu viec duoc nghi phep 2 ngay moi thang.\nQuy dinh ap dung tu 2024.",
    }]
    result = chunk_blocks(fake_blocks, strategy="semantic")
    print(f"Đã tạo {len(result)} chunk demo trong bộ nhớ; không ghi vào chunks.json")
    print(f"Tổng số chunk trong kho={len(load_all_chunks())}")
