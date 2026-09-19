"""
inspect_qdrant.py — xem số lượng chunk và nội dung chunk đang có trên Qdrant.

Chạy từ thư mục `backend`:

    python -m app.ai_agent.inspect_qdrant                      # tổng quan + số chunk theo từng file
    python -m app.ai_agent.inspect_qdrant --show 5             # in thêm 5 chunk đầu (preview)
    python -m app.ai_agent.inspect_qdrant --show 3 --full      # in nội dung đầy đủ
    python -m app.ai_agent.inspect_qdrant --source alibaba     # chỉ xét file có tên chứa "alibaba"
    python -m app.ai_agent.inspect_qdrant --contains "doanh thu" --show 5   # chunk có chứa cụm từ

Script chỉ ĐỌC dữ liệu (không sửa / xóa gì trên Qdrant, không tải vector).
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from typing import Any, Iterator

from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "chatbot_documents_v2")

_SOURCE_KEYS = ("source", "source_file", "file_name", "filename", "document_name")


def _iter_points(
    client: QdrantClient,
    collection: str,
    batch_size: int = 256,
) -> Iterator[Any]:
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        yield from points
        if offset is None:
            break


def _parse_point(point: Any) -> dict[str, Any]:
    """Tách payload theo cùng cách với retrieval.get_all_documents()."""
    payload = point.payload or {}

    content = payload.get("page_content", payload.get("content", ""))
    if not isinstance(content, str):
        content = str(content)

    metadata = payload.get("metadata", {})
    metadata = dict(metadata) if isinstance(metadata, dict) else {}

    # collection cũ có thể lưu metadata ở root
    for key, value in payload.items():
        if key not in ("page_content", "content", "metadata"):
            metadata.setdefault(key, value)

    source = next((metadata[k] for k in _SOURCE_KEYS if metadata.get(k)), None)
    if source is None and metadata.get("document_id") is not None:
        source = f"document_{metadata['document_id']}"

    page = metadata.get("page")
    if page is None:
        page = metadata.get("page_number")

    return {
        "point_id": str(point.id),
        "chunk_id": metadata.get("chunk_id"),
        "chunk_index": metadata.get("chunk_index"),
        "source": source or "(không có source)",
        "page": page,
        "content": content,
        "metadata": metadata,
    }


def inspect_collection(
    client: QdrantClient,
    collection: str,
    *,
    show: int = 0,
    source: str | None = None,
    contains: str | None = None,
    full: bool = False,
) -> None:
    if not client.collection_exists(collection):
        print(f"Collection '{collection}' KHÔNG tồn tại trên Qdrant.")
        return

    info = client.get_collection(collection)
    exact_count = client.count(collection, exact=True).count

    print("=" * 70)
    print(f"Collection : {collection}")
    print(f"Status     : {info.status}")
    print(f"Số chunk   : {exact_count} (points_count={info.points_count})")

    vectors = info.config.params.vectors
    if isinstance(vectors, dict):
        for name, params in vectors.items():
            print(f"Vector '{name}': size={params.size}, distance={params.distance}")
    elif vectors is not None:
        print(f"Vector     : size={vectors.size}, distance={vectors.distance}")
    print("=" * 70)

    # đọc toàn bộ chunk (chỉ payload) và lọc theo yêu cầu
    chunks = [_parse_point(p) for p in _iter_points(client, collection)]

    if source:
        chunks = [c for c in chunks if source.lower() in str(c["source"]).lower()]
    if contains:
        chunks = [c for c in chunks if contains.lower() in c["content"].lower()]

    if source or contains:
        print(f"Số chunk sau khi lọc: {len(chunks)}")

    # thống kê theo file
    per_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        per_source[str(chunk["source"])].append(chunk)

    if per_source:
        print("\nSố chunk theo từng file:")
        for name, items in sorted(per_source.items(), key=lambda kv: -len(kv[1])):
            pages = sorted({c["page"] for c in items if c["page"] is not None}, key=str)
            page_text = f", {len(pages)} trang" if pages else ""
            avg_len = sum(len(c["content"]) for c in items) // len(items)
            print(f"  - {name}: {len(items)} chunk{page_text}, ~{avg_len} ký tự/chunk")

    empty = sum(1 for c in chunks if not c["content"].strip())
    if empty:
        print(f"\n⚠ Có {empty} chunk rỗng (page_content trống).")

    # in nội dung chunk
    if show > 0:
        print(f"\n{min(show, len(chunks))} chunk đầu tiên:")
        for index, chunk in enumerate(chunks[:show], start=1):
            text = chunk["content"].strip()
            if not full and len(text) > 300:
                text = text[:300] + " ..."
            print(f"\n--- [{index}] ---")
            print(f"point_id   : {chunk['point_id']}")
            print(f"chunk_id   : {chunk['chunk_id']}")
            print(f"source     : {chunk['source']}  | page: {chunk['page']}")
            print(f"độ dài     : {len(chunk['content'])} ký tự")
            print(f"nội dung   :\n{text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Xem chunk đang có trên Qdrant")
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--show", type=int, default=0, help="số chunk in ra để xem nội dung")
    parser.add_argument("--full", action="store_true", help="in nội dung đầy đủ (không cắt 300 ký tự)")
    parser.add_argument("--source", default=None, help="lọc theo tên file (chứa chuỗi này)")
    parser.add_argument("--contains", default=None, help="lọc chunk có chứa cụm từ này")
    args = parser.parse_args()

    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    inspect_collection(
        client,
        args.collection,
        show=args.show,
        source=args.source,
        contains=args.contains,
        full=args.full,
    )

    parser.add_argument(
        "--export",
        default=None,
        help="xuất toàn bộ chunk ra file txt"
    )


if __name__ == "__main__":
    main()