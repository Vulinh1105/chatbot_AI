from __future__ import annotations

import re
import unicodedata
from collections import Counter
from math import log
from typing import Iterable

from langchain_core.documents import Document
from .retrieval import QdrantRetriever, Retriever

# hiện đang tìm chunk theo 2 cách: semantic search và Keyword Search -> trộn 2 danh sách = RRF -> lấy top k

RRF_K = 60

# xác định id của 1 chunk -> ưu tiên chunk_id
def _doc_id(doc: Document) -> str:
    meta = doc.metadata
    return str(
        meta.get("chunk_id")
        or meta.get("qdrant_point_id")
        or (
            f"{meta.get('document_id', '')}_"
            f"{meta.get('chunk_index', '')}"
        )
    )

# tách thành danh sách từ
def _tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(
        char
        for char in normalized
        if not unicodedata.combining(char)
    )
    normalized = normalized.replace("đ", "d")
    return re.findall(r"\w+", normalized, flags=re.UNICODE)

# tạo 1 bộ retriever kết hợp: Semantic Retriever + Keyword Retriever
class HybridRetriever:

    def __init__(
        self,
        semantic_retriever: Retriever,
        documents: Iterable[Document] | None = None
    ) -> None:
        # nhận semantic retrieval có sẵn
        self.semantic_retriever = semantic_retriever

        if documents is not None:
            self.documents = list(documents)


        # nếu dataset lớn -> chưa tối ưu
        # (qdrant -> scroll all 99 chunks -> đưa về python trong RAM -> BM25-like)
        # Qdrant đang lưu dữ liệu, nhưng keyword search chưa phải native sparse/full-text search của Qdrant.
        elif isinstance(
            semantic_retriever,
            QdrantRetriever,
        ):
            self.documents = (
                semantic_retriever.get_all_documents()
            )

        else:
            self.documents = []

        # Chuẩn bị dữ liệu cho BM25-like keyword search
        self._tokenized_documents = [
            _tokenize(doc.page_content)
            for doc in self.documents
        ]

        self._avg_doc_length = (
            sum(
                map(
                    len,
                    self._tokenized_documents
                )
            )
            / len(self._tokenized_documents)
            if self._tokenized_documents
            else 0
        )

        self._document_frequency = Counter(
            token
            for tokens in self._tokenized_documents
            for token in set(tokens)
        )

    # 1. Vector search
    # gọi semantic retrieval: retrieval.py -> qdrant
    def retrieve_semantic(
        self,
        query: str,
        k: int = 8
    ) -> list[Document]:
        return self.semantic_retriever.retrieve(
            query,
            k
        )

    # 2. keyword search
    # BM25-like; tách query thành các từ
    # tìm chunk dựa trên từ khoá xuất hiện trong text
    def retrieve_keyword(
        self,
        query: str,
        k: int = 8
    ) -> list[Document]:

        if not self.documents:
            return []

        terms = set(
            _tokenize(query)
        )

        if not terms:
            return []

        total_documents = len(
            self.documents
        )

        k1 = 1.5
        b = 0.75

        scored: list[
            tuple[float, Document]
        ] = []

        # duyệt từng chunk
        for doc, tokens in zip(
            self.documents,
            self._tokenized_documents,
        ):
            counts = Counter(tokens)
            length = len(tokens)

            if length == 0:
                continue

            score = 0.0

            # tính điểm cho từng query term
            for term in terms:
                frequency = counts[term]

                if not frequency:
                    continue

                document_frequency = (
                    self._document_frequency[term]
                )

                # IDF: ý tưởng: 1 từ xuất hiện ở ít document -> gtri phân biệt cao hơn
                idf = log(
                    1
                    + (
                        total_documents
                        - document_frequency
                        + 0.5
                    )
                    / (
                        document_frequency
                        + 0.5
                    )
                )

                # BM25 score: idea: score càng cao -> keyword match càng tốt
                score += (
                    idf
                    * frequency
                    * (k1 + 1)
                    / (
                        frequency
                        + k1
                        * (
                            1
                            - b
                            + b
                            * length
                            / self._avg_doc_length
                        )
                    )
                )

            if score > 0:
                metadata = dict(
                    doc.metadata
                )

                metadata["keyword_score"] = (
                    float(score)
                )

                scored.append(
                    (
                        float(score),
                        Document(
                            page_content=doc.page_content,
                            metadata=metadata,
                        ),
                    )
                )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            doc
            for _, doc in scored[:k]
        ]

    # Hybrid search
    # ham tổng
    def retrieve(
        self,
        query: str,
        k: int = 8,
    ) -> list[Document]:

        candidate_k = max(
            k * 3,
            10,
        )

        semantic_results = (
            self.retrieve_semantic(
                query,
                candidate_k,
            )
        )

        keyword_results = (
            self.retrieve_keyword(
                query,
                candidate_k,
            )
        )

        scores: dict[str, float] = {}
        docs: dict[str, Document] = {}

        # RRF
        for result_set in (
            semantic_results,
            keyword_results,
        ):
            for rank, document in enumerate(
                result_set,
                start=1,
            ):
                key = _doc_id(
                    document
                )

                scores[key] = (
                    scores.get(key, 0.0)
                    + 1
                    / (
                        RRF_K
                        + rank
                    )
                )

                docs[key] = document

        # Sort theo RRF score
        ranked_keys = sorted(
            scores,
            key=scores.get,
            reverse=True,
        )[:k]

        output: list[Document] = []

        for rank, key in enumerate(
            ranked_keys,
            start=1,
        ):
            doc = docs[key]

            metadata = dict(
                doc.metadata
            )

            metadata.update(
                {
                    "rrf_score": scores[key],
                    "retrieval_rank": rank,
                }
            )

            output.append(
                Document(
                    page_content=doc.page_content,
                    metadata=metadata,
                )
            )

        return output

'''
TODO/Future:
Keyword Search hiện tại chạy BM25-like trên toàn bộ chunks
load từ Qdrant bằng get_all_documents().
Phù hợp với prototype/dataset nhỏ.
Khi dataset lớn cần chuyển sang native Qdrant
Sparse/Keyword Search để tránh load toàn bộ chunks mỗi query.
'''