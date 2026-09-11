from typing import List, Dict, Any

from langchain_core import documents
from langchain_core.documents import Document


NO_EVIDENCE_MESSAGE = "Tài liệu hiện tại không đề cập vấn đề này."

# check evidence
def has_evidence(
    chunks: List[Document]
) -> bool:
    if not chunks:
        return False
    for chunk in chunks:
        if isinstance(chunk, Document):
            if (chunk.page_content and chunk.page_content.strip()):
                return True
    return False

# get source metadata
def get_source_metadata(
    chunk: Document
) -> Dict[str, Any]:
    """
    Lấy metadata citation từ Document
    """
    if not isinstance(
        chunk,
        Document
    ):
        return {
            "source": None,
            "page": None,
            "chunk_index": None,
        }

    metadata = chunk.metadata

    if not isinstance(metadata, dict):
        metadata = {}

    # sourse
    source = (
        metadata.get("source")
        or metadata.get("source_file")
        or metadata.get("file_name")
        or metadata.get("filename")
        or metadata.get("document_name")
    )

    # page
    page = metadata.get("page")
    if page is None:
        page = metadata.get("page_number")

    # chunk_index
    chunk_index = metadata.get("chunk_index")
    return {
        "source": source,
        "page": page,
        "chunk_index": chunk_index,
    }


def build_citations(
    chunks: List[Document]
) -> List[Dict[str, Any]]:
    """
    Tạo citation từ metadata thật của chunks.
    KHÔNG lấy citation do LLM tự sinh.
    """

    grouped = {}

    for chunk in chunks:

        metadata = get_source_metadata(chunk)

        source = metadata["source"]
        page = metadata["page"]

        # Không có source -> không tạo citation
        if not source:
            continue

        if source not in grouped:
            grouped[source] = {
                "source": source,
                "pages": []
            }

        if page is not None and page not in grouped[source]["pages"]:
            grouped[source]["pages"].append(page)

    citations = []

    for source, data in grouped.items():
        data["pages"].sort()

        citations.append({
            "source": source,
            "pages": data["pages"]
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
        pages = citation.get("pages", [])

        # Có source + page
        if pages:
            pages = sorted(set(pages))

            if len(pages) == 1:
                page_text = f"trang {pages[0]}"
            else:
                page_text = "trang " + ", ".join(
                    str(page) for page in pages
                )

            lines.append(
                f"- {source}, {page_text}"
            )

        # Chỉ có source
        else:
            lines.append(
                f"- {source}"
            )

    return "\n".join(lines)

# final
def validate_answer(
    answer: str,
    chunks: List[Document]
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

# print('validation done')