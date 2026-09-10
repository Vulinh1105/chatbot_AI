from typing import List, Dict, Any
NO_EVIDENCE_MESSAGE = "Tài liệu hiện tại không đề cập vấn đề này."
def has_evidence(
    chunks: List[Dict[str, Any]]
) -> bool:
    if not chunks:
        return False
    for chunk in chunks:
        if isinstance(chunk, str):
            if chunk.strip():
                return True
        elif isinstance(chunk, dict):
            content = (
                chunk.get("content")
                or chunk.get("text")
                or ""
            )
            if content and str(content).strip():
                return True
    return False
def get_source_metadata(
    chunk: Dict[str, Any]
) -> Dict[str, Any]:
    metadata = chunk.get(
        "metadata",
        {}
    )
    if not isinstance(metadata, dict):
        metadata = {}
    source = (
        chunk.get("source_file")
        or metadata.get("source")
        or metadata.get("file_name")
        or metadata.get("filename")
    )
    chunk_index = (
        chunk.get("chunk_index")
        or metadata.get("chunk_index")
    )
    page = (
        metadata.get("page")
        or metadata.get("page_number")
    )
    return {
        "source": source,
        "page": page,
        "chunk_index": chunk_index
    }
def build_citations(
    chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Tạo citation từ metadata thật của chunks.
    KHÔNG lấy citation do LLM tự sinh.
    """

    citations = []
    seen = set()

    for chunk in chunks:

        if not isinstance(chunk, dict):
            continue

        metadata = get_source_metadata(chunk)

        source = metadata["source"]
        page = metadata["page"]
        chunk_index = metadata["chunk_index"]

        # Không có source -> không tạo citation
        if not source:
            continue

        citation_key = (
            source,
            page,
            chunk_index
        )

        if citation_key in seen:
            continue

        seen.add(citation_key)

        citations.append({
            "source": source,
            "page": page,
            "chunk_index": chunk_index
        })

    return citations


def format_citations(
    citations: List[Dict[str, Any]]
) -> str:
    """
    Format citation để hiển thị cho người dùng.
    """

    if not citations:
        return ""

    lines = [
        "",
        "Nguồn tham khảo:"
    ]

    for citation in citations:

        source = citation["source"]
        page = citation.get("page")
        chunk_index = citation.get("chunk_index")

        # Có source + page
        if page is not None:
            lines.append(
                f"- {source}, trang {page}"
            )
        # Có source + chunk
        elif chunk_index is not None:
            lines.append(
                f"- {source}, chunk {chunk_index}"
            )
        # Chỉ có source
        else:
            lines.append(
                f"- {source}"
            )

    return "\n".join(lines)

def validate_answer(
    answer: str,
    chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validation cuối cùng của T17.

    Trả về:

    {
        "valid": True/False,
        "answer": "...",
        "citations": [...]
    }
    """

    # 1. Không có evidence
    if not has_evidence(chunks):

        return {
            "valid": False,
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }
    # 2. LLM không trả lời
    if not answer or not answer.strip():
        return {
            "valid": False,
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }
    answer = answer.strip()
    # 3. LLM đã trả câu từ chối
    if answer == NO_EVIDENCE_MESSAGE:
        return {
            "valid": False,
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }
    # 4. Tạo citation từ metadata thật
    citations = build_citations(chunks)
    # Có context nhưng không có nguồn
    if not citations:
        return {
            "valid": False,
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }
    # 5. Ghép Answer + Citation
    final_answer = (
        answer +
        format_citations(citations)
    )
    return {
        "valid": True,
        "answer": final_answer,
        "citations": citations
    }

print('done')