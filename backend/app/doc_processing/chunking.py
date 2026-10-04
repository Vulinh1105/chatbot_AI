"""
doc_processing.chunking
========================
T09 - Chunking Strategy: nhan list "parsed block" (output cua
parsing.parse_document()) va cat thanh chunks theo cac chien luoc
(fixed_overlap, recursive_paragraph, semantic, structure_aware),
sau do GOP & LUU LIEN TUC vao kho Qdrant va luu ban sao local tai
app/doc_processing/doc/chunks.json.

Vi sao dung 1 kho Qdrant chung cho TAT CA tai lieu:
    - G3 (Retrieval) can tra loi NHIEU cau hoi khac nhau, co the lien quan
      den NHIEU tai lieu cung luc (vd so sanh noi dung 2 file).
    - Sap xep lien tuc theo (document_id, page, chunk_index) giup retrieval
      doc hieu qua, luon co du ngu canh lien mach.

Luu y ve RBAC: chunk co san department/access_level (mac dinh None/"internal")
de khong pha schema khi G4 bo sung RBAC that su sau nay - xem
ingestion.build_document_meta().

--- THAY DOI CHINH (structure-aware chunking) ---
Van de: chunking cu cat ngang bang markdown, khien header cot nam o chunk
truoc, data rows o chunk sau. LLM nhan bang so tran trui khong biet cot nao
la gi -> refuse du co du du lieu.

Giai phap:
1. _split_structure_aware(): nhan dien block table/heading/paragraph tu text
   tho, KHONG BAO GIO cat ngang 1 bang; bang lon thi lap lai header cot vao
   dau moi sub-chunk.
2. contextual_prefix: moi chunk mang "[Tai lieu: X] [H1 > H2]" de retriever
   co du ngu canh du khong lay 2 chunk lien ke cung luc.
3. min_chars guard: chunk < min_chars duoc gop vao chunk tiep theo.
4. Luu song song vao doc/chunks.json de theo doi / debug.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

logger = logging.getLogger(__name__)

OUTPUT_CHUNKING_DIR = Path(__file__).resolve().parent / "doc"
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "chatbot_documents_v2")
CHUNKS_STORE_FILE = OUTPUT_CHUNKING_DIR / "chunks.json"


def _qdrant_url() -> str:
    return os.getenv(
        "QDRANT_URL",
        f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}",
    )


def _qdrant_api_key() -> str | None:
    value = os.getenv("QDRANT_API_KEY")
    return None if value in {None, "", "None", "null"} else value


_STORE_LOCK = threading.Lock()


class ChunkingError(Exception):
    """Loi phat sinh khi cat chunk hoac doc/ghi kho chunks."""


# ---------------------------------------------------------------------------
# Helper functions cho _split_structure_aware
# ---------------------------------------------------------------------------

def _is_table_line(line: str) -> bool:
    """True neu dong la 1 hang bang markdown (bat dau bang |)."""
    stripped = line.strip()
    return stripped.startswith("|") and len(stripped) > 1


def _is_table_separator(line: str) -> bool:
    """True neu dong la separator bang markdown (|---|---|)."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    inner = stripped.strip("|")
    return bool(re.fullmatch(r"[\s\-:|]+", inner))


def _heading_level(line: str) -> int:
    """Tra ve level heading (1-6) neu la heading markdown, 0 neu khong phai."""
    m = re.match(r"^(#{1,6})\s+", line.strip())
    if m:
        return len(m.group(1))
    if re.match(r"^\*\*[^*]+\*\*\s*$", line.strip()):
        return 2
    return 0


def _detect_blocks(text: str) -> list[dict]:
    """
    Nhan dien cac block co cau truc tu text tho:
      - "table"    : 2+ dong lien tiep dang | col | (bao gom ca separator)
      - "heading"  : dong heading markdown (#) hoac **Bold standalone**
      - "paragraph": moi thu con lai
    Tra ve list[{"type": str, "lines": list[str], "level": int|None}]
    """
    lines = text.split("\n")
    blocks: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if _is_table_line(line):
            table_lines = [line]
            i += 1
            while i < len(lines) and (
                _is_table_line(lines[i]) or _is_table_separator(lines[i])
            ):
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) >= 2:
                blocks.append({"type": "table", "lines": table_lines, "level": None})
            else:
                blocks.append({"type": "paragraph", "lines": table_lines, "level": None})
            continue

        level = _heading_level(line)
        if level > 0 and line.strip():
            blocks.append({"type": "heading", "lines": [line], "level": level})
            i += 1
            continue

        para_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if _is_table_line(next_line) or _heading_level(next_line) > 0:
                break
            para_lines.append(next_line)
            i += 1
        blocks.append({"type": "paragraph", "lines": para_lines, "level": None})

    return blocks


def _extract_table_header(table_lines: list[str]) -> tuple[list[str], list[str]]:
    """
    Tach header rows khoi data rows cua mot bang.
    Header = dong dau tien + dong separator ngay sau no (neu co).
    Tra ve (header_lines, data_lines).
    """
    if len(table_lines) < 2:
        return table_lines, []
    sep_idx = None
    for idx, line in enumerate(table_lines):
        if _is_table_separator(line):
            sep_idx = idx
            break
    if sep_idx is None:
        return [], table_lines
    return table_lines[: sep_idx + 1], table_lines[sep_idx + 1 :]


def _split_table_into_chunks(table_lines: list[str], max_chars: int) -> list[str]:
    """
    Chia 1 bang lon thanh nhieu sub-chunks, lap lai header cot vao dau moi
    sub-chunk de LLM luon biet cot nao la gi du retriever chi lay 1 chunk.
    """
    header_lines, data_lines = _extract_table_header(table_lines)
    if not data_lines:
        return ["\n".join(table_lines)]

    header_text = "\n".join(header_lines)
    result_chunks: list[str] = []
    current_rows: list[str] = []

    for row in data_lines:
        candidate = header_text + "\n" + "\n".join(current_rows + [row])
        if len(candidate) > max_chars and current_rows:
            result_chunks.append(header_text + "\n" + "\n".join(current_rows))
            current_rows = [row]
        else:
            current_rows.append(row)

    if current_rows:
        result_chunks.append(header_text + "\n" + "\n".join(current_rows))

    return result_chunks if result_chunks else ["\n".join(table_lines)]


# ---------------------------------------------------------------------------
# Chien luoc 4 -- structure_aware (default, moi)
# ---------------------------------------------------------------------------

def _split_structure_aware(
    text: str,
    max_chars: int = 800,
    min_chars: int = 80,
    overlap_sentences: int = 1,
    document_name: str = "",
) -> list[tuple[str, str]]:
    """
    Chien luoc Structure-Aware (default):
    - Nhan dien block table/heading/paragraph.
    - KHONG BAO GIO cat ngang bang markdown.
    - Bang lon hon max_chars -> chia theo row va lap lai header cot vao dau
      moi sub-chunk.
    - Heading nho (H3+) duoc gop vao block tiep theo, khong tao chunk vun.
    - Chunk < min_chars duoc gop vao chunk tiep theo.
    - Moi chunk duoc gan contextual_prefix = "[Tai lieu: X] [H1 > H2]".

    Tra ve list[(content, context_prefix)].
    """
    blocks = _detect_blocks(text)
    results: list[tuple[str, str]] = []

    breadcrumb_stack: list[tuple[int, str]] = []

    def _current_breadcrumb() -> str:
        return " > ".join(t for _, t in breadcrumb_stack)

    def _make_prefix(crumb: str) -> str:
        parts = []
        if document_name:
            parts.append(f"[Tai lieu: {document_name}]")
        if crumb:
            parts.append(f"[{crumb}]")
        return " ".join(parts)

    buffer = ""
    buffer_prefix = _make_prefix("")
    pending_heading: str | None = None

    for block in blocks:
        btype = block["type"]
        blines = block["lines"]
        blevel = block.get("level")
        block_text = "\n".join(blines).strip()

        # --- HEADING ---
        if btype == "heading":
            while breadcrumb_stack and breadcrumb_stack[-1][0] >= blevel:
                breadcrumb_stack.pop()
            heading_clean = re.sub(r"^#{1,6}\s*", "", block_text).strip("*").strip()
            breadcrumb_stack.append((blevel, heading_clean))

            if blevel <= 2:
                # H1/H2 -> flush buffer cu, bat dau vung ngu nghia moi
                if buffer.strip():
                    results.append((buffer.strip(), buffer_prefix))
                    buffer = ""
                buffer_prefix = _make_prefix(_current_breadcrumb())
                pending_heading = block_text
            else:
                # H3+ -> ghep vao block tiep theo
                pending_heading = block_text
            continue

        # --- TABLE ---
        if btype == "table":
            if buffer.strip():
                results.append((buffer.strip(), buffer_prefix))
                buffer = ""

            prefix = _make_prefix(_current_breadcrumb())
            header_prefix_text = (pending_heading + "\n") if pending_heading else ""
            pending_heading = None

            table_full = (header_prefix_text + block_text).strip()

            if len(table_full) <= max_chars:
                results.append((table_full, prefix))
            else:
                sub_chunks = _split_table_into_chunks(blines, max_chars)
                for idx, sub in enumerate(sub_chunks):
                    sub_content = sub.strip()
                    if idx == 0 and header_prefix_text:
                        sub_content = header_prefix_text.strip() + "\n" + sub_content
                    results.append((sub_content, prefix))

            buffer_prefix = _make_prefix(_current_breadcrumb())
            continue

        # --- PARAGRAPH ---
        if btype == "paragraph":
            current_prefix = _make_prefix(_current_breadcrumb())

            paragraphs = [p.strip() for p in block_text.split("\n") if p.strip()]
            if not paragraphs:
                continue

            if pending_heading:
                paragraphs[0] = pending_heading + "\n" + paragraphs[0]
                pending_heading = None

            # Neu prefix thay doi (sang section moi) -> flush
            if buffer and buffer_prefix != current_prefix:
                results.append((buffer.strip(), buffer_prefix))
                buffer = ""
                buffer_prefix = current_prefix

            for p in paragraphs:
                sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]
                for i_s, s in enumerate(sents):
                    sep = "\n" if i_s == 0 and buffer else " "
                    candidate = (buffer + sep + s).strip() if buffer else s

                    if len(candidate) <= max_chars:
                        buffer = candidate
                    else:
                        if buffer.strip():
                            results.append((buffer.strip(), buffer_prefix))
                            if overlap_sentences > 0:
                                prev_sents = re.split(r"(?<=[.!?])\s+", buffer.strip())
                                overlap_text = " ".join(prev_sents[-overlap_sentences:]) if prev_sents else ""
                                buffer = (overlap_text + " " + s).strip() if overlap_text else s
                            else:
                                buffer = s
                        else:
                            buffer = s
                    buffer_prefix = current_prefix

    # Flush remaining
    if pending_heading:
        buffer = (buffer + "\n" + pending_heading).strip() if buffer else pending_heading
    if buffer.strip():
        results.append((buffer.strip(), buffer_prefix))

    # --- Min-chars guard: gop chunk vun (< min_chars) vao chunk tiep theo ---
    if min_chars > 0 and len(results) > 1:
        merged: list[tuple[str, str]] = []
        i = 0
        while i < len(results):
            content, prefix = results[i]
            if len(content) < min_chars and i + 1 < len(results):
                nc, np_ = results[i + 1]
                results[i + 1] = ((content + "\n" + nc).strip(), np_)
                i += 1
                continue
            merged.append((content, prefix))
            i += 1
        results = merged

    return results


# ---------------------------------------------------------------------------
# Chien luoc 1 -- fixed_overlap (baseline)
# ---------------------------------------------------------------------------

def _split_fixed_overlap(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chien luoc 1 - fixed_overlap: cat co dinh theo so ky tu, co overlap
    giua 2 chunk lien ke de khong mat ngu canh o ranh gioi. Don gian, nhanh,
    dung lam baseline, nhung co the cat ngang cau."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size phai lon hon overlap de tranh vong lap vo han.")

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


# ---------------------------------------------------------------------------
# Chien luoc 2 -- recursive_paragraph
# ---------------------------------------------------------------------------

def _split_recursive_paragraph(text: str, max_chars: int = 500) -> list[str]:
    """Chien luoc 2 - recursive_paragraph: cat theo doan van, gop cac doan
    ngan lai cho den gan max_chars. Giu tron ngu nghia tung doan tot hon
    chien luoc 1 (khong cat ngang cau) nhung kich thuoc chunk khong deu."""
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
            # Neu 1 doan van don le da dai hon max_chars, van giu nguyen
            # tron doan do thanh 1 chunk rieng (khong cat bo noi dung).
            buffer = p
    if buffer:
        pieces.append(buffer)
    return pieces


# ---------------------------------------------------------------------------
# Chien luoc 3 -- semantic
# ---------------------------------------------------------------------------

def _split_semantic(text: str, max_chars: int = 1500) -> list[str]:
    """
    Chien luoc 3 - Semantic Chunking:
    Chia van ban dua tren su thay doi ngu nghia giua cac cau, thay vi chi
    dua tren so luong ky tu. max_chars la tran cung de mot nhom cau khong
    tro thanh chunk qua dai khi cac cau co chu de gan nhau.
    LUU Y: khong nhan dien bang markdown - dung structure_aware de tranh cat bang.
    """
    import math
    from langchain_openai import OpenAIEmbeddings

    if max_chars <= 0:
        raise ValueError("max_chars phai lon hon 0.")

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text.strip())
        if s.strip()
    ]
    if len(sentences) <= 1:
        return [
            piece
            for sentence in sentences
            for piece in (
                [sentence]
                if len(sentence) <= max_chars
                else _split_fixed_overlap(sentence, chunk_size=max_chars, overlap=0)
            )
        ]

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectors = embeddings.embed_documents(sentences)
    distances = []
    for current, following in zip(vectors, vectors[1:]):
        cn = math.sqrt(sum(v * v for v in current))
        fn = math.sqrt(sum(v * v for v in following))
        if cn == 0 or fn == 0:
            distances.append(1.0)
            continue
        distances.append(
            1 - sum(a * b for a, b in zip(current, following)) / (cn * fn)
        )

    sorted_distances = sorted(distances)
    if not sorted_distances:
        return _split_recursive_paragraph(text, max_chars=max_chars)

    pi = (len(sorted_distances) - 1) * 0.95
    li = int(pi)
    ui = min(li + 1, len(sorted_distances) - 1)
    if li == ui:
        threshold = sorted_distances[li]
    else:
        threshold = sorted_distances[li] + (pi - li) * (
            sorted_distances[ui] - sorted_distances[li]
        )

    chunks: list[str] = []
    current_chunk = [sentences[0]]
    for idx, sentence in enumerate(sentences[1:]):
        candidate = " ".join(current_chunk + [sentence])
        if distances[idx] >= threshold or len(candidate) > max_chars:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
        current_chunk.append(sentence)
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    bounded: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            bounded.append(chunk)
        else:
            bounded.extend(_split_fixed_overlap(chunk, chunk_size=max_chars, overlap=0))
    return bounded


_STRATEGIES = {
    "structure_aware": "structure_aware",  # xu ly rieng trong chunk_blocks()
    "fixed_overlap": _split_fixed_overlap,
    "recursive_paragraph": _split_recursive_paragraph,
    "semantic": _split_semantic,
}


# ---------------------------------------------------------------------------
# Ham chunk chinh - PURE FUNCTION (khong I/O) de de viet unit test theo DoD T09
# ---------------------------------------------------------------------------

def chunk_blocks(
    parsed_blocks: list[dict],
    strategy: str = "structure_aware",
    document_meta: dict | None = None,
    max_chars: int = 800,
    min_chars: int = 80,
    overlap_sentences: int = 1,
    add_prefix: bool = True,
    **strategy_kwargs,
) -> list[dict]:
    """
    Args:
        parsed_blocks: output cua parsing.parse_document() - moi block co
            {document_id, page, text}.
        strategy: "structure_aware" (default), "fixed_overlap",
            "recursive_paragraph", hoac "semantic".
        document_meta: metadata bo sung theo chuan chunk schema trong
            Kick-off Guide, vi du:
            {"department": "HR", "access_level": "internal", "version": 1,
             "document_name": "HR_Policy.pdf"}.
            G4 se dung "department"/"access_level" de loc chunk trai quyen
            TRUOC khi dua context cho LLM (security scenario bat buoc trong
            Kick-off Guide). Neu khong truyen, dung gia tri mac dinh an toan.
        max_chars: tran ky tu cho 1 chunk. Default 800 -- du ngan gon va giu nguyen cau.
        min_chars: chunk ngan hon nguong nay bi gop vao chunk tiep theo
            (chi ap dung structure_aware). Default 80.
        overlap_sentences: so cau overlap giua 2 paragraph chunk lien ke
            (chi ap dung structure_aware). Default 1.
        add_prefix: neu True, field embed_content = prefix + content de
            embedding co du ngu canh; content goc duoc giu nguyen. Default True.
        **strategy_kwargs: tham so them cho chien luoc legacy (vd chunk_size,
            overlap, max_chars) - dung khi can thuc nghiem so sanh tham so.

    Returns:
        list[dict]: moi chunk co du field theo chunk schema thong nhat toan du an
        (chunk_id, document_id, content, embed_content, context_prefix,
        page, chunk_index, char_count, strategy, department, access_level,
        version, document_name, created_at).
    """
    if strategy not in _STRATEGIES:
        raise ValueError(
            f"Chien luoc khong ton tai: {strategy!r}. Chon 1 trong {list(_STRATEGIES)}"
        )

    document_meta = document_meta or {}
    document_name = document_meta.get("document_name", "")

    chunks: list[dict] = []
    global_chunk_index = 0  # chunk_index lien tuc (khong reset theo page)

    for block in parsed_blocks:
        page = block["page"]
        text = block["text"]
        doc_id = block["document_id"]

        if strategy == "structure_aware":
            pieces_with_prefix = _split_structure_aware(
                text,
                max_chars=max_chars,
                min_chars=min_chars,
                overlap_sentences=overlap_sentences,
                document_name=document_name,
            )
            for piece, prefix in pieces_with_prefix:
                if not piece:
                    continue
                embed_content = (
                    (prefix + "\n" + piece).strip() if (add_prefix and prefix) else piece
                )
                chunks.append({
                    "chunk_id": f"doc{doc_id}_p{page}_c{global_chunk_index:03d}",
                    "document_id": doc_id,
                    "content": piece,
                    "embed_content": embed_content,
                    "context_prefix": prefix,
                    "page": page,
                    "chunk_index": global_chunk_index,
                    "char_count": len(piece),
                    "strategy": strategy,
                    "department": document_meta.get("department"),
                    "access_level": document_meta.get("access_level", "internal"),
                    "version": document_meta.get("version", 1),
                    "document_name": document_name,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                global_chunk_index += 1

        else:
            # Cac chien luoc legacy (fixed_overlap, recursive_paragraph, semantic)
            split_fn = _STRATEGIES[strategy]
            kw = {**strategy_kwargs}
            if strategy in ("recursive_paragraph", "semantic") and "max_chars" not in kw:
                kw["max_chars"] = max_chars
            elif strategy == "fixed_overlap" and "chunk_size" not in kw:
                kw["chunk_size"] = max_chars
            pieces = split_fn(text, **kw)
            for piece in pieces:
                if not piece:
                    continue
                chunks.append({
                    "chunk_id": f"doc{doc_id}_p{page}_c{global_chunk_index:03d}",
                    "document_id": doc_id,
                    "content": piece,
                    "embed_content": piece,
                    "context_prefix": "",
                    "page": page,
                    "chunk_index": global_chunk_index,
                    "char_count": len(piece),
                    "strategy": strategy,
                    "department": document_meta.get("department"),
                    "access_level": document_meta.get("access_level", "internal"),
                    "version": document_meta.get("version", 1),
                    "document_name": document_name,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                global_chunk_index += 1

    return chunks


# ---------------------------------------------------------------------------
# I/O local: luu chunks.json de debug / theo doi
# ---------------------------------------------------------------------------

def _save_chunks_local(chunks: list[dict], document_id: int) -> None:
    """Luu / cap nhat chunks vao file JSON local doc/chunks.json.
    Khi re-ingest 1 document, cac chunk cu cua document_id do bi xoa truoc
    khi ghi moi, tranh trung lap.
    """
    OUTPUT_CHUNKING_DIR.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if CHUNKS_STORE_FILE.exists():
        try:
            with CHUNKS_STORE_FILE.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("chunks.json bi loi, se ghi de: %s", exc)
            existing = []

    existing = [c for c in existing if c.get("document_id") != document_id]
    existing.extend(chunks)
    existing.sort(key=lambda c: (c.get("document_id", 0), c.get("chunk_index", 0)))

    try:
        with CHUNKS_STORE_FILE.open("w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info(
            "Da luu %s chunk cua document_id=%s vao %s (tong: %s chunk).",
            len(chunks),
            document_id,
            CHUNKS_STORE_FILE,
            len(existing),
        )
    except OSError as exc:
        logger.warning("Khong the ghi chunks.json: %s", exc)


# ---------------------------------------------------------------------------
# I/O: luu chunk vao Qdrant
# ---------------------------------------------------------------------------

def load_all_chunks() -> list[dict]:
    """Doc payload chunk tu Qdrant de phuc vu keyword retrieval."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=_qdrant_url(), api_key=_qdrant_api_key())
        if not client.collection_exists(QDRANT_COLLECTION):
            return []
        points, _ = client.scroll(
            QDRANT_COLLECTION, limit=10000, with_payload=True, with_vectors=False
        )
        chunks = []
        for point in points:
            payload = point.payload or {}
            metadata = payload.get("metadata", {})
            content = payload.get("page_content", payload.get("content", ""))
            chunks.append({"content": content, **metadata})
        return chunks
    except Exception as exc:
        logger.warning("Khong the doc chunk tu Qdrant: %s", exc)
        return []


def _delete_qdrant_document(document_id: int) -> None:
    from qdrant_client import QdrantClient, models

    client = QdrantClient(url=_qdrant_url(), api_key=_qdrant_api_key())
    if client.collection_exists(QDRANT_COLLECTION):
        client.delete(
            QDRANT_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )


def _document_points_exist(document_id: int, expected_count: int) -> bool:
    """Xac nhan Qdrant da ghi du points sau khi client bao timeout."""
    if expected_count <= 0:
        return True
    try:
        from qdrant_client import QdrantClient, models

        client = QdrantClient(url=_qdrant_url(), api_key=_qdrant_api_key())
        if not client.collection_exists(QDRANT_COLLECTION):
            return False
        result = client.count(
            QDRANT_COLLECTION,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            ),
            exact=True,
        )
        return result.count == expected_count
    except Exception as exc:
        logger.warning(
            "Khong the xac nhan points sau timeout cho document_id=%s: %s",
            document_id,
            exc,
        )
        return False


def save_chunks(chunks: list[dict], document_id: int) -> str:
    """
    Xoa cac point cu cua tai lieu roi embedding va upsert chunk moi vao Qdrant.
    Dong thoi luu ban sao vao doc/chunks.json de debug/theo doi.

    embed_content (= contextual_prefix + content) duoc dung de embedding;
    content goc duoc luu trong payload de hien thi cho user.
    Cac truong con lai tro thanh payload metadata cua point.
    """
    with _STORE_LOCK:
        from langchain_core.documents import Document
        from app.ai_agent.embeddings import create_vector_db

        _delete_qdrant_document(document_id)

        docs = []
        for chunk in chunks:
            embed_text = chunk.get("embed_content") or chunk["content"]
            metadata = {
                key: value
                for key, value in chunk.items()
                if key not in ("content", "embed_content")
            }
            metadata["content"] = chunk["content"]
            docs.append(Document(page_content=embed_text, metadata=metadata))

        if docs:
            try:
                create_vector_db(docs)
            except Exception:
                if not _document_points_exist(document_id, len(chunks)):
                    raise
                logger.warning(
                    "Qdrant bao loi ghi nhung da co du %s points cho document_id=%s; "
                    "tiep tuc pipeline.",
                    len(chunks),
                    document_id,
                )

        logger.info(
            "Da index %s chunk cho document_id=%s vao collection '%s'.",
            len(chunks),
            document_id,
            QDRANT_COLLECTION,
        )

        try:
            _save_chunks_local(chunks, document_id)
        except Exception as exc:
            logger.warning(
                "Luu chunks.json local that bai (khong anh huong Qdrant): %s", exc
            )

        return QDRANT_COLLECTION


def delete_chunks_by_document(document_id: int) -> int:
    """Xoa toan bo chunk cua 1 document_id khoi kho chung - goi khi tai lieu
    bi xoa (UC-16 "Xoa tai lieu") de tranh chatbot van tra loi dua tren tai
    lieu Admin da xoa (du lieu "mo coi"). Tra ve so chunk da xoa."""
    with _STORE_LOCK:
        before = [
            chunk
            for chunk in load_all_chunks()
            if chunk.get("document_id") == document_id
        ]
        _delete_qdrant_document(document_id)

        if CHUNKS_STORE_FILE.exists():
            try:
                with CHUNKS_STORE_FILE.open("r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing = [c for c in existing if c.get("document_id") != document_id]
                with CHUNKS_STORE_FILE.open("w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Khong the cap nhat chunks.json khi xoa document: %s", exc
                )

        if before:
            logger.info(
                "Da xoa %s chunk cua document_id=%s khoi Qdrant.",
                len(before),
                document_id,
            )
        return len(before)


def chunk_and_save(
    parsed_blocks: list[dict],
    document_id: int,
    strategy: str = "structure_aware",
    document_meta: dict | None = None,
    **strategy_kwargs,
) -> tuple[list[dict], str]:
    """Tien ich gop: chunk roi luu luon vao kho chung - dung trong
    pipeline.py cho luong end-to-end (T11)."""
    chunks = chunk_blocks(
        parsed_blocks,
        strategy=strategy,
        document_meta=document_meta,
        **strategy_kwargs,
    )
    path = save_chunks(chunks, document_id=document_id)
    return chunks, path


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO)

    # Du lieu test mo phong chinh xac case loi tu nhan xet nhom (doc54):
    # bang GDP Trung Quoc 2025 bi cat giua header va data rows.
    fake_text = (
        "# Chuong 1: Kinh te vi mo\n\n"
        "## 1.1 Tang truong kinh te\n\n"
        "Nam 2025, kinh te Trung Quoc tiep tuc tang truong on dinh.\n\n"
        "**Bang 1-1: Co cau GDP nam 2025 theo nganh**\n\n"
        "| Nganh | Gia tri gia tang (ty NDT) | Tang truong | Ty trong |\n"
        "|-------|--------------------------|-------------|----------|\n"
        "| Nganh thu nhat | 93.347 | 3,9% | 6,7% |\n"
        "| Nganh thu hai | 499.653 | 4,5% | 35,6% |\n"
        "| Nganh thu ba | 808.879 | 5,4% | 57,7% |\n\n"
        "Ghi chu: so lieu tinh theo gia so sanh nam 2020.\n\n"
        "## 1.2 Lam phat\n\n"
        "Chi so gia tieu dung (CPI) tang 0,2% so voi nam truoc.\n"
        "Chi so gia san xuat (PPI) giam 2,2% do gia nguyen vat lieu giam manh.\n"
    )

    fake_blocks = [{"document_id": 54, "page": 1, "text": fake_text}]

    result = chunk_blocks(
        fake_blocks,
        strategy="structure_aware",
        document_meta={"document_name": "Bao cao GDP 2025.pdf"},
    )

    print(f"\n{'='*60}")
    print(f"Tong so chunk: {len(result)}")
    print(f"{'='*60}")
    for i, chunk in enumerate(result):
        print(f"\n--- Chunk {i} (page={chunk['page']}, chars={chunk['char_count']}) ---")
        print(f"PREFIX : {chunk['context_prefix']}")
        print(f"CONTENT:\n{chunk['content']}")

    tiny = [c for c in result if c["char_count"] < 80]
    if tiny:
        print(f"\n[WARNING] {len(tiny)} chunk ngan hon 80 ky tu:")
        for c in tiny:
            print(f"  {c['chunk_id']}, chars={c['char_count']}: {c['content'][:50]!r}")
    else:
        print(f"\n[OK] Khong co chunk vun (< 80 ky tu).")

    table_chunks = [c for c in result if "Nganh thu hai" in c["content"]]
    if table_chunks:
        tc = table_chunks[0]
        has_header = "Gia tri gia tang" in tc["content"]
        status = "[OK]" if has_header else "[FAIL]"
        print(
            f"\n{status} Chunk chua 'Nganh thu hai' "
            f"{'CO' if has_header else 'KHONG CO'} header cot 'Gia tri gia tang'."
        )
    else:
        print("\n[WARNING] Khong tim thay chunk chua 'Nganh thu hai'.")

    print(f"\nChunks.json se duoc luu tai: {CHUNKS_STORE_FILE} (khi goi save_chunks()).")
    print(f"Da tao {len(result)} chunk demo trong bo nho; khong ghi vao Qdrant.")
