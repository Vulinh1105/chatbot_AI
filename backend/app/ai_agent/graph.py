from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from .guardrails import REFUSAL_MESSAGE, check_output
from .hybrid_retrieval import HybridRetriever
from .prompt import generate_answer
from .retrieval import QdrantRetriever, Retriever
from .state import RAGState
from .validation import NO_EVIDENCE_MESSAGE, check_query


RERANK_TOP_K = 5
MIN_RETRIEVAL_SCORE = 0.15


class ConversationStore(Protocol):
    def append(self, session_id: str, turn: Any) -> None: ...


@dataclass
class GraphDependencies:
    retriever: Retriever | HybridRetriever
    rerank: Callable[
        [str, list[Document], int],
        tuple[list[Document], float],
    ] | None = None
    generate: Callable[[str, list[Document]], str] = generate_answer
    query_checker: Callable[[str], Any] = check_query
    store: ConversationStore | None = None
    turn_factory: Callable[..., Any] | None = None


def build_rag_graph(deps: GraphDependencies):

    retriever = (
        deps.retriever
        if isinstance(deps.retriever, HybridRetriever)
        else HybridRetriever(deps.retriever)
    )

    reranker_instance = None

    def rerank(
        query: str,
        docs: list[Document],
    ) -> list[Document]:
        nonlocal reranker_instance

        if deps.rerank is not None:
            ranked = deps.rerank(
                query,
                docs,
                RERANK_TOP_K,
            )

            if isinstance(ranked, tuple):
                return ranked[0]

            return ranked

        from .reranking import Reranker

        if reranker_instance is None:
            reranker_instance = Reranker()

        ranked, _ = reranker_instance.rerank(
            query,
            docs,
            top_k=RERANK_TOP_K,
        )

        return ranked

    def validation_node(state: RAGState) -> dict[str, Any]:
        query = state.get("query", "").strip()

        result = deps.query_checker(query)

        if isinstance(result, dict):
            query_allowed = result.get(
                "query_allowed",
                result.get("allowed", False),
            )
            refusal_reason = result.get("refusal_reason")
        else:
            query_allowed = bool(result)
            refusal_reason = None

        history = state.get("history", [])

        rewritten_query = None
        retrieval_query = query

        followup_prefixes = (
            "còn",
            "thế",
            "nó",
            "điều này",
            "vậy",
            "cái này",
            "cái đó",
            "phần này",
            "loại đó",
            "mục đó",
        )

        followup_terms = (
            "này",
            "đó",
            "đây",
            "kia",
            "trên",
            "dưới",
        )

        clean = query.lower()

        is_followup = bool(history) and (
            clean.startswith(followup_prefixes)
            or clean.endswith(followup_terms)
        )

        if is_followup:
            previous = history[-1]

            if isinstance(previous, dict):
                previous_query = (
                    previous.get("rewritten_query")
                    or previous.get("query")
                    or ""
                )
            else:
                previous_query = (
                    getattr(previous, "rewritten_query", None)
                    or getattr(previous, "query", "")
                )

            if previous_query:
                rewritten_query = (
                    f"{previous_query}. "
                    f"Câu hỏi tiếp theo: {query}"
                )
                retrieval_query = rewritten_query

        return {
            "query_allowed": query_allowed,
            "refusal_reason": refusal_reason,
            "retrieval_query": retrieval_query,
            "rewritten_query": rewritten_query,
            "needs_rewrite": rewritten_query is not None,
        }

    def retrieval_node(state: RAGState) -> dict[str, Any]:
        return {
            "retrieved_chunks": retriever.retrieve_semantic(
                state["retrieval_query"],
                k=8,
            ),
            "route": "semantic",
        }

    def hybrid_node(state: RAGState) -> dict[str, Any]:
        return {
            "retrieved_chunks": retriever.retrieve(
                state["retrieval_query"],
                k=8,
            ),
            "hybrid_attempted": True,
            "route": "hybrid",
        }

    def reranking_node(state: RAGState) -> dict[str, Any]:
        docs = [
            doc
            for doc in state.get("retrieved_chunks", [])
            if doc.page_content
            and doc.page_content.strip()
        ]

        if not docs:
            return {
                "reranked_chunks": [],
            }

        return {
            "reranked_chunks": rerank(
                state["retrieval_query"],
                docs,
            ),
        }

    def evaluate_node(state: RAGState) -> dict[str, Any]:
        docs = state.get("reranked_chunks", [])

        if not docs:
            return {
                "retrieval_quality": "insufficient",
                "valid": False,
            }

        retrieval_scores = [
            float(doc.metadata["retrieval_score"])
            for doc in docs
            if "retrieval_score" in doc.metadata
        ]

        rrf_scores = [
            float(doc.metadata["rrf_score"])
            for doc in docs
            if "rrf_score" in doc.metadata
        ]

        if retrieval_scores:
            best_score = max(retrieval_scores)

            quality = (
                "good"
                if best_score >= MIN_RETRIEVAL_SCORE
                else "insufficient"
            )

        elif rrf_scores:
            quality = "good"

        else:
            quality = "insufficient"

        return {
            "retrieval_quality": quality,
            "valid": quality == "good",
        }

    def generation_node(state: RAGState) -> dict[str, Any]:
        return {
            "answer": deps.generate(
                state["retrieval_query"],
                state["reranked_chunks"],
            )
        }

    def guardrails_node(state: RAGState) -> dict[str, Any]:
        return check_output(
            state.get("answer", ""),
            state.get("reranked_chunks", []),
        )

    def refuse_node(state: RAGState) -> dict[str, Any]:
        refusal_reason = state.get("refusal_reason")
        guardrail_reason = state.get("guardrail_reason")

        if refusal_reason:
            answer = REFUSAL_MESSAGE
        elif guardrail_reason in (
            "empty_answer",
            "ungrounded_answer",
            "no_evidence",
        ):
            answer = NO_EVIDENCE_MESSAGE
        else:
            answer = NO_EVIDENCE_MESSAGE

        return {
            "valid": False,
            "answer": answer,
            "citations": [],
            "route": "refuse",
        }

    def save_node(state: RAGState) -> dict[str, Any]:
        if (
            deps.store is not None
            and deps.turn_factory is not None
        ):
            turn = deps.turn_factory(
                query=state["query"],
                answer=state["answer"],
                rewritten_query=state.get(
                    "rewritten_query"
                ),
                context=state.get(
                    "reranked_chunks",
                    [],
                ),
            )

            deps.store.append(
                state["session_id"],
                turn,
            )

        return {}

    graph = StateGraph(RAGState)

    nodes = (
        ("validation", validation_node),
        ("retrieval", retrieval_node),
        ("reranking", reranking_node),
        ("evaluate_retrieval", evaluate_node),
        ("hybrid_retrieval", hybrid_node),
        ("generation", generation_node),
        ("guardrails", guardrails_node),
        ("refuse", refuse_node),
        ("save_turn", save_node),
    )

    for name, node in nodes:
        graph.add_node(name, node)

    graph.add_edge(
        START,
        "validation",
    )

    graph.add_conditional_edges(
        "validation",
        lambda state: (
            "retrieval"
            if state["query_allowed"]
            else "refuse"
        ),
    )

    graph.add_edge(
        "retrieval",
        "reranking",
    )

    graph.add_edge(
        "reranking",
        "evaluate_retrieval",
    )

    graph.add_conditional_edges(
        "evaluate_retrieval",
        lambda state: (
            "generation"
            if state["retrieval_quality"] == "good"
            else (
                "refuse"
                if state.get("hybrid_attempted")
                else "hybrid_retrieval"
            )
        ),
    )

    graph.add_edge(
        "hybrid_retrieval",
        "reranking",
    )

    graph.add_edge(
        "generation",
        "guardrails",
    )

    graph.add_conditional_edges(
        "guardrails",
        lambda state: (
            "save_turn"
            if state["valid"]
            else "refuse"
        ),
    )

    graph.add_edge(
        "refuse",
        "save_turn",
    )

    graph.add_edge(
        "save_turn",
        END,
    )

    return graph.compile()