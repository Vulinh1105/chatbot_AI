from time import perf_counter

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


DEFAULT_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
DEFAULT_TOP_K = 5
DEFAULT_BATCH_SIZE = 8


class Reranker:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.model = CrossEncoder(
            model_name,
            device=device,
        )

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int = DEFAULT_TOP_K,
    ) -> tuple[list[Document], float]:
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        if not documents:
            return [], 0.0

        pairs = [
            (query, document.page_content)
            for document in documents
        ]

        start_time = perf_counter()

        scores = self.model.predict(
            pairs,
            batch_size=DEFAULT_BATCH_SIZE,
            show_progress_bar=False,
        )

        latency_ms = (perf_counter() - start_time) * 1000

        ranked_documents = []

        for retrieval_rank, (document, score) in enumerate(
            zip(documents, scores),
            start=1,
        ):
            metadata = dict(document.metadata)

            metadata["retrieval_rank"] = retrieval_rank
            metadata["rerank_score"] = float(score)

            ranked_documents.append(
                Document(
                    page_content=document.page_content,
                    metadata=metadata,
                )
            )

        ranked_documents.sort(
            key=lambda document: document.metadata["rerank_score"],
            reverse=True,
        )

        for rerank_rank, document in enumerate(
            ranked_documents,
            start=1,
        ):
            document.metadata["rerank_rank"] = rerank_rank

        return ranked_documents[:top_k], latency_ms