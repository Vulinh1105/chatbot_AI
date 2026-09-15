from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

from .validation import (
    QueryCheckResult,
    check_query,
    validate_answer,
)

REFUSAL_MESSAGE = (
    "Tôi không thể xử lý yêu cầu này. "
    "Vui lòng hỏi về tài liệu nội bộ một cách an toàn."
)


def check_output(
    answer: str,
    chunks: list[Document],
) -> dict[str, Any]:

    result = validate_answer(
        answer,
        chunks,
    )

    reason = result.get("reason")

    if reason == "no_evidence":
        return {
            **result,
            "guardrail_reason": "no_evidence",
        }

    if reason == "empty_answer":
        return {
            **result,
            "guardrail_reason": "empty_answer",
        }

    if reason in (
        "no_context",
        "missing_citations",
    ):
        return {
            **result,
            "guardrail_reason": "ungrounded_answer",
        }

    return {
        **result,
        "guardrail_reason": None,
    }


__all__ = [
    "REFUSAL_MESSAGE",
    "QueryCheckResult",
    "check_query",
    "check_output",
]