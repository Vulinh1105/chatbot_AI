from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from .evidence import EvidenceJudgeResult, judge_evidence
from .hybrid_retrieval import HybridRetriever
from .prompt import generate_answer
from .retrieval import QdrantRetriever, Retriever
from .state import RAGState
from .validation import (
    NO_EVIDENCE_MESSAGE,
    check_query,
    validate_answer,
)


# Workflow controller

RERANK_TOP_K = 5


# CHANGE:
# Threshold dùng để xác định kết quả retrieval có đủ liên quan
# dựa trên rerank_score của document đứng đầu.
#
# Kết quả test:
# - Positive queries: top rerank score >= 0.882
# - Negative queries: top rerank score <= 0.00089
#
# Chọn 0.5 làm threshold ban đầu để tạo khoảng cách an toàn
# giữa nhóm có evidence và nhóm không có evidence.
RERANK_SCORE_THRESHOLD = 0.5


class ConversationStore(Protocol):
    def append(
        self,
        session_id: str,
        turn: Any,
    ) -> None:
        ...


@dataclass
class GraphDependencies:
    retriever: Retriever | HybridRetriever

    rerank: Callable[
        [
            str,
            list[Document],
            int,
        ],
        tuple[list[Document], float],
    ] | None = None

    # THÊM:
    # Evidence Judge nhận query + các chunk sau reranking
    # và xác định chunk nào thực sự có thể dùng làm evidence.
    #
    # Tách Evidence Judge thành dependency để:
    # - dễ test bằng fake function
    # - không khóa graph vào một model cụ thể
    # - sau này có thể thay LLM Judge bằng model/API khác.
    evidence_judge: Callable[
        [
            str,
            list[Document],
        ],
        EvidenceJudgeResult,
    ] = judge_evidence

    generate: Callable[
        [
            str,
            list[Document],
        ],
        str,
    ] = generate_answer

    query_checker: Callable[
        [str],
        Any,
    ] = check_query

    store: ConversationStore | None = None

    turn_factory: Callable[
        ...,
    ] | None = None


def build_rag_graph(
    deps: GraphDependencies,
):

    # HYBRID RETRIEVER
    retriever = (
        deps.retriever
        if isinstance(
            deps.retriever,
            HybridRetriever,
        )
        else HybridRetriever(
            deps.retriever
        )
    )

    reranker_instance = None

    # Reranking wrapper
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

            if isinstance(
                ranked,
                tuple,
            ):
                return ranked[0]

            return ranked

        from .reranking import Reranker

        if reranker_instance is None:
            reranker_instance = Reranker()

        ranked, _ = (
            reranker_instance.rerank(
                query,
                docs,
                top_k=RERANK_TOP_K,
            )
        )

        return ranked


    # 1. INPUT VALIDATION + QUERY REWRITE
    def validation_node(
        state: RAGState,
    ) -> dict[str, Any]:

        query = (
            state
            .get("query", "")
            .strip()
        )

        result = deps.query_checker(
            query
        )

        if hasattr(
            result,
            "allowed",
        ):

            query_allowed = (
                result.allowed
            )

            refusal_reason = (
                result.reason
            )

        elif isinstance(
            result,
            dict,
        ):

            query_allowed = result.get(
                "query_allowed",
                result.get(
                    "allowed",
                    False,
                ),
            )

            refusal_reason = (
                result.get(
                    "refusal_reason"
                )
            )

        else:

            query_allowed = bool(
                result
            )

            refusal_reason = None

        history = state.get(
            "history",
            [],
        )

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

        is_followup = (
            bool(history)
            and (
                clean.startswith(
                    followup_prefixes
                )
                or clean.endswith(
                    followup_terms
                )
            )
        )

        if is_followup:

            previous = history[-1]

            if isinstance(
                previous,
                dict,
            ):

                previous_query = (
                    previous.get(
                        "rewritten_query"
                    )
                    or previous.get(
                        "query"
                    )
                    or ""
                )

            else:

                previous_query = (
                    getattr(
                        previous,
                        "rewritten_query",
                        None,
                    )
                    or getattr(
                        previous,
                        "query",
                        "",
                    )
                )

            if previous_query:

                rewritten_query = (
                    f"{previous_query}. "
                    f"Câu hỏi tiếp theo: "
                    f"{query}"
                )

                retrieval_query = (
                    rewritten_query
                )

        return {
            "query_allowed": (
                query_allowed
            ),

            "refusal_reason": (
                refusal_reason
            ),

            "retrieval_query": (
                retrieval_query
            ),

            "rewritten_query": (
                rewritten_query
            ),

            "needs_rewrite": (
                rewritten_query
                is not None
            ),
        }


    # 2. HYBRID RETRIEVAL
    # Qdrant
    #   ├── Vector Search
    #   └── Keyword Search
    #           ↓
    #          RRF

    def retrieval_node(
        state: RAGState,
    ) -> dict[str, Any]:

        documents = retriever.retrieve(
            state["retrieval_query"],
            k=8,
        )

        return {
            "retrieved_chunks": documents,
            "route": "hybrid",
        }


    # 3. RERANKING
    def reranking_node(
        state: RAGState,
    ) -> dict[str, Any]:

        docs = [
            doc
            for doc in state.get(
                "retrieved_chunks",
                [],
            )
            if (
                doc.page_content
                and doc.page_content.strip()
            )
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


    # 4. RETRIEVAL QUALITY
    def retrieval_quality_node(
        state: RAGState,
    ) -> dict[str, Any]:

        docs = state.get(
            "reranked_chunks",
            [],
        )

        if not docs:

            return {
                "retrieval_quality": (
                    "insufficient"
                ),
                "valid": False,
            }


        # CHANGE:
        # Không còn kiểm tra đơn giản:
        # "có rrf_score => good".
        #
        # Trước đây hybrid retrieval luôn thêm rrf_score
        # cho các document được trả về.
        # Vì vậy kể cả query không liên quan vẫn có thể
        # bị đánh dấu là "good" và tiếp tục gọi LLM.
        #
        # Thay vào đó lấy rerank_score của document
        # đứng đầu sau bước reranking để đánh giá
        # mức độ liên quan của retrieval result.

        top_score = float(
            docs[0].metadata.get(
                "rerank_score",
                0.0,
            )
        )


        # CHANGE:
        # Nếu top rerank_score đạt threshold thì
        # retrieval được xem là đủ tốt để đưa cho LLM.
        #
        # Nếu thấp hơn threshold thì dừng tại đây
        # và chuyển sang refusal, không gọi LLM.

        if top_score >= RERANK_SCORE_THRESHOLD:

            quality = "good"

        else:

            quality = "insufficient"


        return {
            "retrieval_quality": quality,

            # CHANGE:
            # Lưu lại score để debug/log/evaluation.
            # Sau này có thể dùng giá trị này để
            # đánh giá và điều chỉnh threshold.

            "retrieval_top_score": top_score,

            "valid": (
                quality == "good"
            ),
        }


    # THÊM:
    # 5. EVIDENCE SELECTION
    #
    # Reranking chỉ xác định document nào có mức độ liên quan cao.
    # Nó chưa đảm bảo document đó thực sự chứa bằng chứng để trả lời query.
    #
    # Node này dùng Evidence Judge để chọn ra các chunk
    # thực sự hỗ trợ câu hỏi.
    def evidence_selection_node(
        state: RAGState,
    ) -> dict[str, Any]:

        query = state.get(
            "retrieval_query",
            "",
        )

        docs = state.get(
            "reranked_chunks",
            [],
        )

        if not docs:
            return {
                "evidence_chunks": [],
                "evidence_sufficient": False,
            }

        result = deps.evidence_judge(
            query,
            docs,
        )

        supported_chunks: list[Document] = []

        # THÊM:
        # Evidence Judge chỉ trả về index của các chunk được chọn.
        # Python chịu trách nhiệm lấy Document thật từ danh sách
        # reranked_chunks, tránh để LLM tự tạo hoặc sửa nội dung evidence.
        for index in result.supported_indices:

            if (
                isinstance(index, int)
                and 0 <= index < len(docs)
            ):
                supported_chunks.append(
                    docs[index]
                )

        # THÊM:
        # Nếu Judge đánh dấu sufficient nhưng không chọn được
        # chunk hợp lệ thì không cho phép tiếp tục generation.
        evidence_sufficient = (
            result.sufficient
            and bool(supported_chunks)
        )

        return {
            "evidence_chunks": supported_chunks,
            "evidence_sufficient": evidence_sufficient,
        }


    # 6. GENERATION
    def generation_node(
        state: RAGState,
    ) -> dict[str, Any]:

        # CHANGE:
        # Trước đây LLM nhận toàn bộ reranked_chunks.
        # Bây giờ chỉ truyền evidence_chunks đã được Evidence Selection
        # xác định là có thể dùng để trả lời câu hỏi.
        return {
            "answer": deps.generate(
                state[
                    "retrieval_query"
                ],
                state[
                    "evidence_chunks"
                ],
            )
        }


    # 7. OUTPUT VALIDATION
    def validate_answer_node(
        state: RAGState,
    ) -> dict[str, Any]:

        # CHANGE:
        # Citation và validation phải dựa trên chính evidence
        # được đưa cho LLM, không phải toàn bộ reranked_chunks.
        return validate_answer(
            state.get(
                "answer",
                "",
            ),
            state.get(
                "evidence_chunks",
                [],
            ),
        )


    # 8. REFUSAL
    def refuse_node(
        state: RAGState,
    ) -> dict[str, Any]:

        refusal_reason = (
            state.get(
                "refusal_reason"
            )
        )

        validation_reason = (
            state.get("reason")
        )

        if refusal_reason:

            answer = (
                "Tôi không thể xử lý "
                "yêu cầu này. "
                "Vui lòng hỏi về tài liệu "
                "nội bộ một cách an toàn."
            )

        elif validation_reason in (
            "empty_answer",
            "no_evidence",
            "no_context",
            "missing_citations",
        ):

            answer = (
                NO_EVIDENCE_MESSAGE
            )

        else:

            answer = (
                NO_EVIDENCE_MESSAGE
            )

        return {
            "valid": False,
            "answer": answer,
            "citations": [],
            "route": "refuse",
        }


    # 9. SAVE CONVERSATION
    def save_node(
        state: RAGState,
    ) -> dict[str, Any]:

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

                # CHANGE:
                # Conversation context nên lưu evidence thực sự
                # được sử dụng để tạo answer, thay vì toàn bộ
                # reranked_chunks.
                context=state.get(
                    "evidence_chunks",
                    [],
                ),
            )

            deps.store.append(
                state["session_id"],
                turn,
            )

        return {}


    # BUILD GRAPH
    graph = StateGraph(
        RAGState
    )

    nodes = (
        (
            "validation",
            validation_node,
        ),
        (
            "retrieval",
            retrieval_node,
        ),
        (
            "reranking",
            reranking_node,
        ),
        (
            "retrieval_quality",
            retrieval_quality_node,
        ),

        # THÊM:
        # Node Evidence Selection nằm giữa
        # Retrieval Quality và Generation.
        (
            "evidence_selection",
            evidence_selection_node,
        ),

        (
            "generation",
            generation_node,
        ),
        (
            "validate_answer",
            validate_answer_node,
        ),
        (
            "refuse",
            refuse_node,
        ),
        (
            "save_turn",
            save_node,
        ),
    )

    for name, node in nodes:

        graph.add_node(
            name,
            node,
        )


    # EDGES
    graph.add_edge(
        START,
        "validation",
    )

    graph.add_conditional_edges(
        "validation",
        lambda state: (
            "retrieval"
            if state[
                "query_allowed"
            ]
            else "refuse"
        ),
    )

    graph.add_edge(
        "retrieval",
        "reranking",
    )

    graph.add_edge(
        "reranking",
        "retrieval_quality",
    )

    # CHANGE:
    # Retrieval Quality không đi thẳng tới Generation nữa.
    # Kết quả phải đi qua Evidence Selection trước.
    graph.add_conditional_edges(
        "retrieval_quality",
        lambda state: (
            "evidence_selection"
            if state[
                "retrieval_quality"
            ] == "good"
            else "refuse"
        ),
    )

    # THÊM:
    # Chỉ khi Evidence Selection xác định đủ evidence
    # mới cho phép gọi LLM.
    graph.add_conditional_edges(
        "evidence_selection",
        lambda state: (
            "generation"
            if state.get(
                "evidence_sufficient",
                False,
            )
            else "refuse"
        ),
    )

    graph.add_edge(
        "generation",
        "validate_answer",
    )

    graph.add_conditional_edges(
        "validate_answer",
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