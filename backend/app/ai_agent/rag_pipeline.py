"""
# rag_pipeline.py — entry point của RAG pipeline.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import defaultdict, deque
from typing import Any

from .graph import (
    DEFAULT_MIN_RERANK_SCORE,
    DEFAULT_RERANK_TOP_K,
    DEFAULT_RETRIEVE_K,
    GenerateFn,
    RerankerLike,
    RetrieverLike,
    build_rag_graph,
)
from .state import RAGState
from .validation import check_query

logger = logging.getLogger(__name__)


# Cấu hình (có thể override bằng biến môi trường trong .env)
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default



# Lưu lịch sử hội thoại (in-memory)
class InMemoryTurnStore:
    """
    Lưu lịch sử theo session_id trong RAM (mất khi restart).
    Thay bằng DB / Redis khi cần lưu bền vững — chỉ cần giữ nguyên
    chữ ký save(...) và get_history(...).
    """

    def __init__(self, max_turns: int = 20) -> None:
        self._messages: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_turns * 2)
        )

    def save(
        self,
        session_id: str,
        query: str,
        answer: str,
        citations: list[dict[str, Any]],
    ) -> None:
        messages = self._messages[session_id]
        messages.append({"role": "user", "content": query})
        messages.append(
            {"role": "assistant", "content": answer, "citations": citations}
        )

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        return list(self._messages.get(session_id, []))


# Chuẩn bị dependency (lazy import)
def _build_hybrid_retriever() -> RetrieverLike:
    from .hybrid_retrieval import HybridRetriever
    from .retrieval import QdrantRetriever

    semantic = QdrantRetriever()
    hybrid = HybridRetriever(semantic)  # scroll toàn bộ chunk từ Qdrant vào RAM

    if not hybrid.documents:
        logger.warning(
            "HybridRetriever không load được chunk nào từ Qdrant "
            "-> keyword search sẽ không hoạt động."
        )
    else:
        logger.info("HybridRetriever loaded %d chunks", len(hybrid.documents))

    return hybrid


def _build_reranker() -> RerankerLike:
    from .reranking import Reranker

    return Reranker()  # load model 1 lần duy nhất


def _build_generator() -> GenerateFn:
    # prompt.py: generate_answer(query, context_chunks) -> str
    from .prompt import generate_answer

    return generate_answer


# RAGPipeline
class RAGPipeline:
    """Đóng gói dependency + graph. Tạo 1 lần, gọi .run() nhiều lần."""

    def __init__(
        self,
        *,
        retriever: RetrieverLike | None = None,
        reranker: RerankerLike | None = None,
        generator: GenerateFn | None = None,
        query_checker=check_query,
        turn_store: InMemoryTurnStore | None = None,
        retrieve_k: int | None = None,
        rerank_top_k: int | None = None,
        min_rerank_score: float | None = None,
    ) -> None:
        # 1. Chuẩn bị dependency
        self.turn_store = turn_store or InMemoryTurnStore()
        self.retriever = retriever or _build_hybrid_retriever()
        self.reranker = reranker or _build_reranker()
        self.generator = generator or _build_generator()

        # 2. Tạo graph
        self.graph = build_rag_graph(
            retriever=self.retriever,
            reranker=self.reranker,
            generate_fn=self.generator,
            query_checker=query_checker,
            save_turn_fn=self.turn_store.save,
            retrieve_k=retrieve_k
            if retrieve_k is not None
            else _env_int("RETRIEVE_K", DEFAULT_RETRIEVE_K),
            rerank_top_k=rerank_top_k
            if rerank_top_k is not None
            else _env_int("RERANK_TOP_K", DEFAULT_RERANK_TOP_K),
            min_rerank_score=min_rerank_score
            if min_rerank_score is not None
            else _env_float("MIN_RERANK_SCORE", DEFAULT_MIN_RERANK_SCORE),
        )

    def run(
        self,
        query: str,
        session_id: str = "default",
        *,
        include_state: bool = False,
    ) -> dict[str, Any]:
        # 3. Tạo initial state
        initial_state: RAGState = {
            "query": query,
            "session_id": session_id,
            "history": self.turn_store.get_history(session_id),
            "hybrid_attempted": False,
        }

        # 4. Chạy graph
        final_state = self.graph.invoke(initial_state)

        result: dict[str, Any] = {
            "answer": final_state.get("answer", ""),
            "citations": final_state.get("citations", []),
            "valid": bool(final_state.get("valid", False)),
            "route": final_state.get("route", "refuse"),
            "refusal_reason": final_state.get("refusal_reason"),
            "guardrail_reason": final_state.get("guardrail_reason"),
            "top_rerank_score": final_state.get("top_rerank_score"),
            "evidence_reason": final_state.get("evidence_reason"),
            "session_id": session_id,
        }

        if include_state:
            result["state"] = final_state

        return result


# API đơn giản cho code khác gọi
_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    """Singleton: model reranker + chunk keyword chỉ load 1 lần."""
    global _pipeline

    if _pipeline is None:
        _pipeline = RAGPipeline()

    return _pipeline


def run_rag(
    query: str,
    session_id: str = "default",
    *,
    include_state: bool = False,
) -> dict[str, Any]:
    return get_pipeline().run(
        query,
        session_id,
        include_state=include_state,
    )


# ---------------------------------------------------------------------------
# Chat thử trên terminal (chỉ chạy khi chạy trực tiếp file này)
# ---------------------------------------------------------------------------

_EXIT_COMMANDS = {"exit", "quit", "q", "thoát"}


def _chat_cli() -> None:
    """Vòng lặp hỏi đáp nhiều câu để test local. Gõ 'exit' để thoát."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    print("Đang khởi tạo RAG pipeline (load chunks + reranker)...")
    pipeline = get_pipeline()  # load 1 lần, dùng lại cho mọi câu hỏi
    session_id = "cli"
    print("Sẵn sàng. Gõ 'exit' để thoát.\n")

    while True:
        try:
            query = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query:
            continue

        if query.lower() in _EXIT_COMMANDS:
            break

        output = pipeline.run(query, session_id)

        print(f"\nBot: {output['answer']}")
        print(
            f"\n[route={output['route']} "
            f"refusal_reason={output['refusal_reason']} "
            f"top_rerank_score={output['top_rerank_score']}]\n"
        )


if __name__ == "__main__":
    _chat_cli()