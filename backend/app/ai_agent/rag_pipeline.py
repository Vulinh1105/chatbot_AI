from retrieval import retrieve
from reranking import Reranker
from prompt import generate_answer
from validation import validate_answer

RERANK_TOP_K = 3

reranker = Reranker()

# main pipeline
def run_pipeline(
    query: str
):

    # retrieval
    retrieved_chunks = retrieve(
        query
    )

    # print(
    #     f"[Retrieval] Found "
    #     f"{len(retrieved_chunks)} chunks."
    # )

    #  reranking
    reranked_chunks, latency_ms = (
        reranker.rerank(
            query,
            retrieved_chunks,
            top_k=RERANK_TOP_K,
        )
    )

    # print(
    #     f"[Reranking] Selected "
    #     f"{len(reranked_chunks)} chunks."
    # )

    # print(
    #     f"[Reranking] Latency: "
    #     f"{latency_ms:.2f} ms"
    # )

    # print("\n[Context sent to LLM]")
    # for i, doc in enumerate(reranked_chunks, start=1):
    #     print(f"--- Chunk {i} ---")
    #     print(doc.page_content)
    #     print("Metadata:", doc.metadata)

    # generation
    answer = generate_answer(
        query,
        reranked_chunks
    )

    # validation
    result = validate_answer(
        answer,
        reranked_chunks
    )


    return result


if __name__ == "__main__":

    print("Khởi chạy chatbot_AI\n")

    while True:
        query = input(
            'Question (type "exit" to quit): '
        )

        if query.strip().lower() == "exit":
            print(
                "Program exited."
            )
            break

        if not query.strip():
            continue

        # run pipeline
        try:
            result = run_pipeline(
                query
            )
            print("\nchatbot AI Answer:")

            print(result["answer"])

            print(
                f"\nValidation: "
                f"{result['valid']}"
            )
            print('\n\n\n\n')

        except Exception as e:

            print("\n[Lỗi Pipeline]")

            print(
                str(e)
            )

            print('\n\n\n\n')