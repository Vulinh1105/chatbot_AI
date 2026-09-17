from __future__ import annotations

import os
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv()
COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "chatbot_documents_v2")


def _qdrant_url() -> str:
    return os.getenv(
        "QDRANT_URL",
        f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}",
    )


def _qdrant_api_key() -> str | None:
    value = os.getenv("QDRANT_API_KEY")
    return None if value in {None, "", "None", "null"} else value


# hàm tạo id ổn định cho từng chunk: kiểm tra chunk tồn tại
def _point_id(document: Document) -> str:
    chunk_id = document.metadata.get("chunk_id")
    identity = str(chunk_id or f"{document.metadata.get('document_id')}:{document.metadata.get('chunk_index')}:{document.page_content}")
    return str(uuid5(NAMESPACE_URL, f"{COLLECTION_NAME}:{identity}"))

# chunk -> vectordb
def create_vector_db(docs: list[Document]) -> QdrantVectorStore:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    qdrant_url = _qdrant_url()
    api_key = _qdrant_api_key()
    client = QdrantClient(url=qdrant_url, api_key=api_key)
    ids = [_point_id(doc) for doc in docs]

    # qdrant collection đã tồn tại
    if client.collection_exists(COLLECTION_NAME):
        store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings, collection_name=COLLECTION_NAME,
            url=qdrant_url, api_key=api_key,
        )
        existing = client.retrieve(COLLECTION_NAME, ids=ids, with_payload=False, with_vectors=False)
        existing_ids = {str(point.id) for point in existing}
        new_pairs = [(doc, point_id) for doc, point_id in zip(docs, ids) if point_id not in existing_ids]
        if new_pairs:
            store.add_documents([doc for doc, _ in new_pairs], ids=[point_id for _, point_id in new_pairs])
        return store

    # qdrant chưa tồn tại
    return QdrantVectorStore.from_documents(
        documents=docs, embedding=embeddings, ids=ids,
        url=qdrant_url, api_key=api_key,
        collection_name=COLLECTION_NAME, batch_size=5,
    )
