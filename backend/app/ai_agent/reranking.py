from time import perf_counter

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


DEFAULT_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2" #tên model rerank, có thể thay bằng model khác
DEFAULT_TOP_K = 5 #output top k documents sau khi rerank
DEFAULT_BATCH_SIZE = 8


class Reranker:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = "cpu",
    ) -> None:
        # Tải mô hình reranker một lần khi khởi tạo đối tượng.
        self.model_name = model_name
        self.model = CrossEncoder(
            model_name,
            device=device,
        )

    def rerank(
        self,
        query: str, #câu hỏi của người dùng
        documents: list[Document], #top N chunk nhận từ retriever
        top_k: int = DEFAULT_TOP_K, #trả về top k chunk sau khi rerank và thời gian rerank
    ) -> tuple[list[Document], float]:
        # Kiểm tra câu hỏi.
        if not query or not query.strip():
            raise ValueError("Query không được để trống.")

        if top_k <= 0:
            raise ValueError("top_k phải lớn hơn 0.")

        if not documents:
            return [], 0.0

        query_document_pairs = [
            (query, document.page_content)
            for document in documents
        ]

        start_time = perf_counter()

        scores = self.model.predict(
            query_document_pairs,
            batch_size=DEFAULT_BATCH_SIZE,
            show_progress_bar=False,
        ) #model chấm điểm

        latency_ms = (perf_counter() - start_time) * 1000

        ranked_documents = []

        # Gắn điểm và thứ hạng retrieval ban đầu vào metadata.
        for retrieval_rank, (document, score) in enumerate(
            zip(documents, scores),
            start=1,
        ):
            new_metadata = document.metadata.copy()
            new_metadata["retrieval_rank"] = retrieval_rank #lưu thứ hạng
            new_metadata["rerank_score"] = float(score) #lưu điểm rerank

            ranked_document = Document(
                page_content=document.page_content,
                metadata=new_metadata,
            )

            ranked_documents.append(ranked_document)

        # Sắp xếp điểm rerank từ cao xuống thấp.
        ranked_documents.sort(
            key=lambda document: document.metadata["rerank_score"],
            reverse=True,
        )

        # Gắn thứ hạng mới sau khi rerank.
        for rerank_rank, document in enumerate(
            ranked_documents,
            start=1,
        ):
            document.metadata["rerank_rank"] = rerank_rank

        # Trả về Top-K chunk và thời gian rerank.
        return ranked_documents[:top_k], latency_ms