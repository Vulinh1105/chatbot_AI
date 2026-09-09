from .retrieval import retrieve
from .prompt import generate_answer


def rag_pipeline(query: str):
    results = retrieve(query)

    if not results:
        return "Tài liệu hiện tại không đề cập vấn đề này."

    return generate_answer(
        query=query,
        context_chunks=results
    )


if __name__ == "__main__":
    while True:
        query = input('Question (type "exit" to quit): ')

        if query.strip().lower() == "exit":
            print("program exited.")
            break

        if not query.strip():
            continue

        answer = rag_pipeline(query)

        print(f"\nAssisstance Answer:\n{answer}\n")
