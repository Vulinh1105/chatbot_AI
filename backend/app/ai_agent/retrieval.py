from __future__ import annotations

import os
from typing import Protocol

from dotenv import load_dotenv
from langchain_core.documents import Document

load_dotenv()
COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "chatbot_documents_v2")

# nhận: query, trả về: Document
class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 8) -> list[Document]: ...


class QdrantRetriever:
    def __init__(self, collection_name: str = COLLECTION_NAME) -> None:
        self.collection_name = collection_name
        self._store = None

    # hàm kết nối collection qdrant, tái kết noois
    def _get_store(self):
        if self._store is None:
            from langchain_openai import OpenAIEmbeddings
            from langchain_qdrant import QdrantVectorStore
            self._store = QdrantVectorStore.from_existing_collection(
                embedding=OpenAIEmbeddings(model="text-embedding-3-large"),
                collection_name=self.collection_name,
                url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"),
                prefer_grpc=False,
            )
        return self._store

    # retrieve: node
    def retrieve(self, query: str, k: int = 8) -> list[Document]:
        try:
            results = self._get_store().similarity_search_with_relevance_scores(query, k=k)
        except Exception:
            return []
        output = []
        for document, score in results:
            metadata = dict(document.metadata)
            metadata["retrieval_score"] = float(score)
            output.append(Document(page_content=document.page_content, metadata=metadata))
        return output


_default_retriever: QdrantRetriever | None = None


def retrieve(query: str, k: int = 8) -> list[Document]:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = QdrantRetriever()
    return _default_retriever.retrieve(query, k)
