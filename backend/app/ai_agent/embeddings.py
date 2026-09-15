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


# hàm tạo id ổn định cho từng chunk: kiểm tra chunk tồn tại
def _point_id(document: Document) -> str:
    chunk_id = document.metadata.get("chunk_id")
    identity = str(chunk_id or f"{document.metadata.get('document_id')}:{document.metadata.get('chunk_index')}:{document.page_content}")
    return str(uuid5(NAMESPACE_URL, f"{COLLECTION_NAME}:{identity}"))

# chunk -> vectordb
def create_vector_db(docs: list[Document]) -> QdrantVectorStore:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    ids = [_point_id(doc) for doc in docs]

    # qdrant collection đã tồn tại
    if client.collection_exists(COLLECTION_NAME):
        store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings, collection_name=COLLECTION_NAME,
            url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"),
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
        url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"),
        collection_name=COLLECTION_NAME, batch_size=5,
    )
