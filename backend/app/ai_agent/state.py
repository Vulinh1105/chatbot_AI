from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.documents import Document

# data structure: định nghĩa dl đc truyền giữa các node trong langgraph
class RAGState(TypedDict, total=False):
    query: str
    session_id: str
    history: list[Any]
    cached_context: list[Document]
    query_allowed: bool
    refusal_reason: str
    needs_rewrite: bool
    rewritten_query: str
    retrieval_query: str
    retrieved_chunks: list[Document]
    reranked_chunks: list[Document]
    retrieval_quality: str
    hybrid_attempted: bool
    answer: str
    citations: list[dict[str, Any]]
    guardrail_reason: str | None
    valid: bool
    route: str
