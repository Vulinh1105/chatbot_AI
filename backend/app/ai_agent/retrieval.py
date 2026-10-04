from __future__ import annotations
from qdrant_client import QdrantClient
import os
from typing import Protocol
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
from langchain_core.documents import Document

load_dotenv()
COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "chatbot_documents_v2")

# nhận: query, trả về: Document
class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 8) -> list[Document]: ...

# class: qly truy vấn qdrant
class QdrantRetriever:
    # cbi thông tin
    def __init__(
        self,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.collection_name = collection_name
        self._store = None
        self._client = None

    # hàm kết nối collection qdrant, tái kết noois
    def _get_store(self) -> QdrantVectorStore:

        if self._store is None:
            self._store = QdrantVectorStore.from_existing_collection(
                embedding=OpenAIEmbeddings(
                    model="text-embedding-3-large"
                ),
                collection_name=self.collection_name,
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
                prefer_grpc=False,
            )

        return self._store


    # Qdrant Client
    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
            )

        return self._client


    # 1. Semantic Search
    # retrieve: node
    # nhận câu hỏi ng dùng -> tìm k -> trả về Document
    def retrieve(
        self,
        query: str,
        k: int = 8,
    ) -> list[Document]:

        try:
            results = (
                self._get_store()
                .similarity_search_with_relevance_scores(
                    query,
                    k=k,
                )
            )

        except Exception:
            return []
        output: list[Document] = []
        for document, score in results:
            metadata = dict(document.metadata)
            metadata["retrieval_score"] = float(score)

            output.append(
                Document(
                    page_content=document.page_content,
                    metadata=metadata,
                )
            )
        return output

    # 2. Load chunks from Qdrant - lấy page_content + metadata trực tiếp từ Qdrant.
    def get_all_documents(
        self,
        batch_size: int = 256,
    ) -> list[Document]:
        client = self._get_client()
        documents: list[Document] = []
        offset = None

        while True:
            points, offset = client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}

                # LangChain Qdrant mặc định thường lưu:
                # {
                #     "page_content": "...",
                #     "metadata": {...}
                # }

                page_content = payload.get(
                    "page_content",
                    payload.get("content", ""),
                )

                raw_metadata = payload.get(
                    "metadata",
                    {},
                )

                if not isinstance(raw_metadata, dict):
                    raw_metadata = {}

                metadata = dict(raw_metadata)

                # Nếu collection cũ lưu metadata ở root
                # thì vẫn giữ lại các field đó.
                for key, value in payload.items():

                    if key not in (
                        "page_content",
                        "content",
                        "metadata",
                    ):
                        metadata.setdefault(
                            key,
                            value,
                        )

                # Giữ point ID nếu chunk chưa có chunk_id
                metadata.setdefault(
                    "qdrant_point_id",
                    str(point.id),
                )

                if (
                    isinstance(page_content, str)
                    and page_content.strip()
                ):
                    documents.append(
                        Document(
                            page_content=page_content,
                            metadata=metadata,
                        )
                    )

            if offset is None:
                break

        return documents



# hàm wrapper -> code khác gọi
# retrieve(query) -> _default_retriever -> QdrantRetriever.retrieve() -> Qdrant
_default_retriever: QdrantRetriever | None = None

def retrieve(
    query: str,
    k: int = 8,
) -> list[Document]:
    global _default_retriever

    if _default_retriever is None:
        _default_retriever = QdrantRetriever()

    return _default_retriever.retrieve(
        query,
        k,
    )