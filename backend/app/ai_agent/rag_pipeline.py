from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from langchain_core.documents import Document

# THAY ĐỔI:
# Không import EvalCase, run_comparison từ evaluate_retrieval.py nữa.
# evaluate_retrieval.py hiện tại là file kiểm tra/đánh giá Qdrant,
# không phải dependency của runtime RAG hỏi đáp.
#
# from .evaluate_retrieval import EvalCase, run_comparison

from .graph import GraphDependencies, build_rag_graph
from .hybrid_retrieval import HybridRetriever
from .prompt import generate_answer
from .retrieval import QdrantRetriever, Retriever
from .validation import check_query


# Represents one completed conversation turn. -> lưu: query, answer, rewritten_query, context
@dataclass
class Turn:
    query: str
    answer: str
    rewritten_query: str | None = None
    context: list[Document] = field(default_factory=list)


# luu lịch sử hội thoại
class ConversationStore(Protocol):

    def get(self, session_id: str) -> list[Turn]:
        raise NotImplementedError

    def append(self, session_id: str, turn: Turn) -> None:
        raise NotImplementedError


# lưu lịch sử chat trong RAM
class InMemoryConversationStore:
    """
    Stores conversation history in application memory.

    Suitable for:
        - local development
        - testing
        - demos

    Not suitable for production persistence because
    data disappears when the process/server restarts.
    """

    def __init__(self) -> None:
        self._turns: dict[str, list[Turn]] = {}

    # lấy history của session, nếu session chưa tồn tại -> []
    def get(self, session_id: str) -> list[Turn]:
        return list(
            self._turns.get(session_id, [])
        )

    # thêm 1 conversation turn vào session, nếu session chưa tồn tại -> tạo list mới
    def append(
        self,
        session_id: str,
        turn: Turn,
    ) -> None:
        if session_id not in self._turns:
            self._turns[session_id] = []

        self._turns[session_id].append(turn)


# RAG Pipeline -> lắp ráp -> xây LangGraph
class RAGPipeline:

    # inject các component
    def __init__(
        self,
        *,
        retriever: Retriever | HybridRetriever | None = None,
        rerank: Callable[
            [str, list[Document], int],
            tuple[list[Document], float],
        ]
        | None = None,
        generate: Callable[
            [str, list[Document]],
            str,
        ] = generate_answer,
        store: ConversationStore | None = None,
        # lấy check_query trực tiếp từ validation.py
        query_checker: Callable[
            [str],
            Any,
        ] = check_query,
    ) -> None:

        #  Create retrieval component
        semantic_retriever = retriever or QdrantRetriever()

        # If the supplied retriever is already hybrid,
        # use it directly.
        if isinstance(
            semantic_retriever,
            HybridRetriever,
        ):
            self.retriever = semantic_retriever

        # Otherwise wrap the semantic retriever
        # inside HybridRetriever.
        else:
            self.retriever = HybridRetriever(
                semantic_retriever
            )

        #  Create conversation storage
        self.store = (
            store
            if store is not None
            else InMemoryConversationStore()
        )

        # create GraphDependencies -> đóng gói all dependency đưa sang graph.py
        dependencies = GraphDependencies(
            retriever=self.retriever,
            rerank=rerank,
            generate=generate,
            query_checker=query_checker,
            store=self.store,
            turn_factory=Turn,
        )

        # tạo langgraph workflow từ các dependency vừa cbi
        self.graph = build_rag_graph(
            dependencies
        )

    # Runnnnn Timeeee
    def run(
        self,
        query: str,
        session_id: str = "default",
    ) -> dict[str, Any]:

        # get previous conversation
        history = self.store.get(
            session_id
        )

        # execute complete LangGraph workflow
        initial_state = {
            "query": query,
            "session_id": session_id,
            "history": history,
            "hybrid_attempted": False,
        }

        result = self.graph.invoke(
            initial_state
        )

        # Return only application-facing fields
        output_keys = (
            "answer",
            "valid",
            "citations",
            "rewritten_query",
            "needs_rewrite",
            "route",
            "refusal_reason",
            "retrieval_quality",
            "retrieved_chunks",
            "reranked_chunks",
        )

        return {
            key: result.get(key)
            for key in output_keys
        }


# THAY ĐỔI:
# Đã bỏ hàm evaluate_retrieval() khỏi RAGPipeline.
#
# Lý do:
# - Hàm này chỉ phục vụ offline retrieval evaluation.
# - evaluate_retrieval.py hiện tại không còn định nghĩa EvalCase/run_comparison.
# - Runtime hỏi đáp không cần gọi chức năng evaluation.
#
# Phần evaluation nên được chạy độc lập bằng file evaluate_retrieval.py
# hoặc test evaluation riêng, không nối vào runtime RAG.


# 7. Application-level pipeline instance
_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    """
    Return the shared RAGPipeline instance.

    The graph is created once and reused across requests.
    """

    global _pipeline

    if _pipeline is None:
        _pipeline = RAGPipeline()

    return _pipeline


# 8. Public entry point - function mà API/ application có the gọi
def run_pipeline(
    query: str,
    session_id: str = "default",
) -> dict[str, Any]:
    """
    Public function used by the API/application layer.
    """

    pipeline = get_pipeline()

    return pipeline.run(
        query=query,
        session_id=session_id,
    )