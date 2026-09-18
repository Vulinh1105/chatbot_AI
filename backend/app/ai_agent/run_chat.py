from __future__ import annotations

from app.ai_agent.rag_pipeline import run_pipeline


# 1. PRINT RESULT
def print_result(result: dict) -> None:
    """
    In kết quả cuối cùng của RAG pipeline.
    """

    print("\n")
    print("=" * 80)
    print("RAG RESULT")
    print("=" * 80)

    print("\nANSWER:")
    print(result.get("answer"))

    print("\nVALID:")
    print(result.get("valid"))

    print("\nROUTE:")
    print(result.get("route"))

    print("\nRETRIEVAL QUALITY:")
    print(result.get("retrieval_quality"))

    print("\nREWRITTEN QUERY:")
    print(result.get("rewritten_query"))

    print("\nNEEDS REWRITE:")
    print(result.get("needs_rewrite"))

    print("\nCITATIONS:")
    print(result.get("citations"))

    print("\nREFUSAL REASON:")
    print(result.get("refusal_reason"))

    # =========================================================================
    # DEBUG RETRIEVAL
    # =========================================================================
    # In các chunk sau reranking để kiểm tra:
    # - Reranker có chọn đúng chunk không
    # - rerank_score là bao nhiêu
    # - RRF score là bao nhiêu
    # - keyword score là bao nhiêu
    # - chunk thuộc document/page nào
    # - nội dung thực tế mà LLM nhận được
    #
    # Phần này chỉ dùng để debug/test.
    # Không thay đổi logic của RAG pipeline.

    reranked_chunks = result.get(
        "reranked_chunks",
        []
    )

    print("\n")
    print("=" * 80)
    print("RERANKED CHUNKS - DEBUG")
    print("=" * 80)

    if not reranked_chunks:
        print("\nKhông có reranked chunks.")
    else:
        for rank, document in enumerate(
            reranked_chunks,
            start=1,
        ):
            metadata = document.metadata

            print("\n" + "-" * 80)
            print(f"RERANKED CHUNK #{rank}")
            print("-" * 80)

            print(
                "rerank_score :",
                metadata.get("rerank_score"),
            )

            print(
                "rerank_rank  :",
                metadata.get("rerank_rank"),
            )

            print(
                "retrieval_rank :",
                metadata.get("retrieval_rank"),
            )

            print(
                "rrf_score    :",
                metadata.get("rrf_score"),
            )

            print(
                "keyword_score:",
                metadata.get("keyword_score"),
            )

            print(
                "retrieval_score:",
                metadata.get("retrieval_score"),
            )

            print(
                "document_id  :",
                metadata.get("document_id"),
            )

            print(
                "source       :",
                metadata.get("source"),
            )

            print(
                "page         :",
                metadata.get("page"),
            )

            print(
                "chunk_id     :",
                metadata.get("chunk_id"),
            )

            print("\nCONTENT:")
            print(document.page_content)

    print("\n" + "=" * 80)


# 2. CHAT LOOP
def main() -> None:
    """
    Chạy chatbot trực tiếp từ terminal.
    """

    print("=" * 80)
    print("RAG CHATBOT")
    print("=" * 80)

    print(
        "\nNhập câu hỏi để bắt đầu."
    )

    print(
        "Gõ 'exit' hoặc 'quit' để thoát."
    )

    session_id = "terminal_session"

    while True:
        print("\n" + "-" * 80)

        query = input("You: ").strip()

        if query.lower() in {
            "exit",
            "quit",
        }:
            print("\nThoát chatbot.")
            break

        if not query:
            print("Vui lòng nhập câu hỏi.")
            continue

        try:
            result = run_pipeline(
                query=query,
                session_id=session_id,
            )

            print_result(result)

        except Exception as exc:
            print("\nERROR:")
            print(type(exc).__name__)
            print(exc)


# 3. ENTRY POINT
if __name__ == "__main__":
    main()