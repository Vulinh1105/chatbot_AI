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

import json
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

# Thêm thư mục `backend` vào sys.path khi chạy script trực tiếp (python backend/app/doc_processing/chunking.py)
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

logger = logging.getLogger(__name__)

# backend/app/doc_processing/chunking.py -> parent = doc_processing/
OUTPUT_CHUNKING_DIR = Path(__file__).resolve().parent / "doc"

# Kho chunk DUY NHẤT của toàn hệ thống (yêu cầu: 1 file chunks.json chứa
# nhiều chunk liên tục để trả lời nhiều câu hỏi về sau).
CHUNKS_STORE_FILE = OUTPUT_CHUNKING_DIR / "chunks.json"

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


_STRATEGIES = {
    "fixed_overlap": _split_fixed_overlap,
    "recursive_paragraph": _split_recursive_paragraph,
}


# ---------------------------------------------------------------------------
# Hàm chunk chính - PURE FUNCTION (không I/O) để dễ viết unit test theo DoD của T09
# ---------------------------------------------------------------------------

def chunk_blocks(
    parsed_blocks: list[dict],
    strategy: str = "fixed_overlap",
    document_meta: dict | None = None,
    **strategy_kwargs,
) -> list[dict]:
    """
    Args:
        parsed_blocks: output của parsing.parse_document() - mỗi block có
            {document_id, page, text}.
        strategy: "fixed_overlap" hoặc "recursive_paragraph".
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
# I/O: gộp & lưu liên tục vào doc/chunks.json
# ---------------------------------------------------------------------------

def load_all_chunks() -> list[dict]:
    """Đọc toàn bộ kho chunk hiện có. Trả về [] nếu file chưa tồn tại hoặc
    rỗng - KHÔNG raise lỗi, để các module gọi (pipeline.py, G3 retrieval)
    không cần try/except riêng cho trường hợp "chưa có tài liệu nào được index"."""
    if not CHUNKS_STORE_FILE.exists():
        return []

    raw = CHUNKS_STORE_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # File bị ghi dở/hỏng (vd process bị kill giữa chừng lúc ghi). Không
        # để lỗi này làm sập cả pipeline - log cảnh báo, backup file lỗi lại
        # để debug, và coi như kho tạm thời rỗng.
        backup_path = CHUNKS_STORE_FILE.with_suffix(".corrupt.json")
        CHUNKS_STORE_FILE.replace(backup_path)
        logger.error(
            "chunks.json bị lỗi định dạng JSON (%s) - đã backup vào '%s' và reset kho chunk.",
            exc, backup_path,
        )
        return []


def _write_all_chunks(chunks: list[dict]) -> None:
    """Ghi ĐÈ toàn bộ kho chunk bằng kỹ thuật write-to-temp-then-rename
    (atomic write): ghi ra file tạm trước, rename đè lên file thật ở bước
    cuối cùng. Nếu tiến trình bị kill giữa chừng, file chunks.json cũ vẫn
    còn nguyên vẹn thay vì bị ghi dở dang."""
    OUTPUT_CHUNKING_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CHUNKS_STORE_FILE.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(CHUNKS_STORE_FILE)


def save_chunks(chunks: list[dict], document_id: int) -> Path:
    """
    Gộp `chunks` (của 1 document_id) vào kho chung `doc/chunks.json`:
      1. Load kho hiện có.
      2. Xoá các chunk CŨ của cùng document_id (nếu user re-upload / re-index
         tài liệu - UC-17 "Quản lý phiên bản tài liệu") để tránh trùng lặp
         hoặc chunk cũ trỏ sai nội dung mới.
      3. Thêm các chunk mới vào.
      4. Sắp xếp lại toàn kho theo (document_id, page, chunk_index) để chunk
         của cùng 1 tài liệu luôn nằm LIÊN TỤC (continuous) trong file - hỗ
         trợ G3 khi cần lấy nhiều chunk liền kề mở rộng ngữ cảnh, và giúp
         chunks.json luôn tích luỹ được nhiều chunk để trả lời nhiều câu hỏi
         khác nhau về sau, không bị mất dữ liệu của tài liệu upload trước.
      5. Ghi đè an toàn (atomic write).

    Trả về đường dẫn file `chunks.json`.
    """
    with _STORE_LOCK:
        existing = load_all_chunks()
        remaining = [c for c in existing if c.get("document_id") != document_id]
        merged = remaining + chunks
        merged.sort(key=lambda c: (c.get("document_id", 0), c.get("page", 0), c.get("chunk_index", 0)))
        _write_all_chunks(merged)
        logger.info(
            "Đã lưu %s chunk mới cho document_id=%s vào '%s' (tổng kho hiện có %s chunk).",
            len(chunks), document_id, CHUNKS_STORE_FILE, len(merged),
        )
        return CHUNKS_STORE_FILE


def delete_chunks_by_document(document_id: int) -> int:
    """Xoá toàn bộ chunk của 1 document_id khỏi kho chung - gọi khi tài liệu
    bị xoá (UC-16 "Xóa tài liệu") để tránh chatbot vẫn trả lời dựa trên tài
    liệu Admin đã xoá (dữ liệu "mồ côi"). Trả về số chunk đã xoá."""
    with _STORE_LOCK:
        existing = load_all_chunks()
        remaining = [c for c in existing if c.get("document_id") != document_id]
        removed_count = len(existing) - len(remaining)
        if removed_count:
            _write_all_chunks(remaining)
            logger.info("Đã xoá %s chunk của document_id=%s khỏi kho chunk.", removed_count, document_id)
        return removed_count


def chunk_and_save(
    parsed_blocks: list[dict],
    document_id: int,
    strategy: str = "fixed_overlap",
    document_meta: dict | None = None,
    **strategy_kwargs,
) -> tuple[list[dict], Path]:
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
    result = chunk_blocks(fake_blocks, strategy="recursive_paragraph")
    print(f"Đã tạo {len(result)} chunk demo trong bộ nhớ; không ghi vào chunks.json")
    print(f"Tổng số chunk trong kho={len(load_all_chunks())}")
