from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# THÊM:
# evidence.py nằm tại:
# D:\chatbot_AI\backend\app\ai_agent\evidence.py
#
# parents[0] = ai_agent
# parents[1] = app
# parents[2] = backend
# parents[3] = chatbot_AI
#
# .env nằm ở root project D:\chatbot_AI\.env
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


# THÊM:
# Schema kết quả của Evidence Judge.
#
# supported_indices:
#   index của những chunk thực sự hỗ trợ câu hỏi.
#
# sufficient:
#   True nếu các chunk được chọn đủ evidence để trả lời.
#
# reason:
#   lý do ngắn gọn để debug/evaluation.
class EvidenceJudgeResult(BaseModel):
    sufficient: bool = Field(
        description=(
            "Cho biết các evidence được chọn "
            "có đủ để trả lời câu hỏi hay không."
        )
    )

    supported_indices: list[int] = Field(
        default_factory=list,
        description=(
            "Danh sách index của các chunk thực sự "
            "hỗ trợ câu hỏi. Index bắt đầu từ 0."
        ),
    )

    reason: str = Field(
        default="",
        description=(
            "Giải thích ngắn gọn tại sao evidence "
            "được xem là đủ hoặc không đủ."
        ),
    )


# THÊM:
# Prompt dành riêng cho Evidence Judge.
#
# Đây KHÔNG phải prompt trả lời người dùng.
# Nhiệm vụ duy nhất của prompt này là đánh giá
# mối quan hệ giữa query và các chunk.
#
# Không có rule về:
# - Alibaba
# - Trung Quốc
# - Việt Nam
# - GDP
# - doanh thu
# - marketing
#
# Vì vậy prompt không phụ thuộc vào tài liệu cụ thể.
EVIDENCE_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Bạn là Evidence Judge cho hệ thống RAG.

Nhiệm vụ của bạn là xác định những đoạn tài liệu nào thực sự
hỗ trợ việc trả lời câu hỏi.

Chỉ được đánh giá dựa trên câu hỏi và các chunk được cung cấp.

Quy tắc:
1. Chỉ chọn chunk nếu nội dung của chunk thực sự hỗ trợ câu hỏi.
2. Không chọn chunk chỉ vì có từ khóa giống câu hỏi.
3. Phải xét đúng đối tượng/chủ thể mà câu hỏi đề cập.
4. Phải xét đúng phạm vi, thời gian, đại lượng hoặc thuộc tính
   mà câu hỏi yêu cầu khi các thông tin này xuất hiện trong câu hỏi.
5. Không kết hợp các chunk thuộc những đối tượng hoặc phạm vi
   khác nhau để tạo thành evidence.
6. Nếu các chunk chỉ liên quan về chủ đề nhưng không đủ để
   trả lời câu hỏi, không chọn chúng.
7. Có thể chọn nhiều chunk nếu chúng bổ sung evidence cho cùng
   một câu hỏi và không mâu thuẫn về đối tượng/phạm vi.
8. Nếu không có chunk nào đủ để hỗ trợ câu hỏi,
   sufficient phải là false và supported_indices phải rỗng.
9. Không sử dụng kiến thức bên ngoài.
10. Không tự tạo thông tin không xuất hiện trong các chunk.
11. supported_indices phải chứa index của chunk, bắt đầu từ 0.

Mục tiêu là chọn evidence, không phải trả lời câu hỏi."""
        ),
        (
            "human",
            """Câu hỏi:
{query}

Các chunk sau đây đã được retrieval và reranking chọn làm candidate:

{chunks}

Hãy xác định những chunk thực sự hỗ trợ câu hỏi."""
        ),
    ]
)


# THÊM:
# Chuyển list[Document] thành context có index.
#
# Index được dùng làm "ID tạm thời" trong một lần judge.
# Evidence Judge chỉ trả index.
# Nội dung Document thật vẫn do Python giữ nguyên.
def _format_chunks(
    chunks: list[Document],
) -> str:

    formatted: list[str] = []

    for index, document in enumerate(chunks):

        metadata = document.metadata

        source = (
            metadata.get("source")
            or metadata.get("source_file")
            or metadata.get("file_name")
            or metadata.get("filename")
            or metadata.get("document_name")
        )

        page = (
            metadata.get("page")
            or metadata.get("page_number")
        )

        chunk_id = metadata.get(
            "chunk_id"
        )

        formatted.append(
            f"[CHUNK {index}]\n"
            f"source: {source}\n"
            f"page: {page}\n"
            f"chunk_id: {chunk_id}\n"
            f"content:\n"
            f"{document.page_content}"
        )

    return "\n\n---\n\n".join(
        formatted
    )


# THÊM:
# Hàm Evidence Judge chính.
#
# Input:
#   query
#   reranked_chunks
#
# Output:
#   EvidenceJudgeResult
#
# Đây là component độc lập với graph.
def judge_evidence(
    query: str,
    chunks: list[Document],
) -> EvidenceJudgeResult:

    if not query or not query.strip():
        return EvidenceJudgeResult(
            sufficient=False,
            supported_indices=[],
            reason="empty_query",
        )

    if not chunks:
        return EvidenceJudgeResult(
            sufficient=False,
            supported_indices=[],
            reason="no_candidate_chunks",
        )

    context = _format_chunks(
        chunks
    )

    llm = ChatOpenAI(
        model="gpt-5.4-nano",
        temperature=0,
    )

    structured_llm = llm.with_structured_output(
        EvidenceJudgeResult
    )

    chain = (
        EVIDENCE_JUDGE_PROMPT
        | structured_llm
    )

    result: EvidenceJudgeResult = (
        chain.invoke(
            {
                "query": query,
                "chunks": context,
            }
        )
    )

    # THÊM:
    # Không tin tuyệt đối vào index do LLM trả về.
    # Python kiểm tra lại range trước khi graph sử dụng chúng.
    valid_indices = [
        index
        for index in result.supported_indices
        if (
            isinstance(index, int)
            and 0 <= index < len(chunks)
        )
    ]

    # THÊM:
    # Loại duplicate index và giữ thứ tự.
    valid_indices = list(
        dict.fromkeys(
            valid_indices
        )
    )

    sufficient = (
        bool(valid_indices)
        and result.sufficient
    )

    return EvidenceJudgeResult(
        sufficient=sufficient,
        supported_indices=valid_indices,
        reason=result.reason,
    )