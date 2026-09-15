from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
import re
from collections import Counter
from math import log
import unicodedata

from langchain_core.documents import Document
from .retrieval import Retriever

RRF_K = 60
CHUNKS_PATH = Path(__file__).resolve().parents[1] / "doc_processing" / "doc" / "chunks.json"


def _doc_id(doc: Document) -> str:
    meta = doc.metadata
    return str(meta.get("chunk_id") or f"{meta.get('document_id', '')}_{meta.get('chunk_index', '')}")


def _tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.replace("đ", "d")
    return re.findall(r"\w+", normalized, flags=re.UNICODE)


def load_indexed_documents(path: Path = CHUNKS_PATH) -> list[Document]:
    """Loads text for keyword matching only; this never embeds documents."""
    if not path.exists():
        return []
    chunks = json.loads(path.read_text(encoding="utf-8"))
    return [Document(page_content=c["content"], metadata={k: v for k, v in c.items() if k != "content"}) for c in chunks]


class HybridRetriever:

    def __init__(self, semantic_retriever: Retriever, documents: Iterable[Document] | None = None) -> None: # nhận semantic retrieval có sẵn
        self.semantic_retriever = semantic_retriever
        self.documents = list(load_indexed_documents() if documents is None else documents)
        self._tokenized_documents = [_tokenize(doc.page_content) for doc in self.documents]
        self._avg_doc_length = sum(map(len, self._tokenized_documents)) / len(self._tokenized_documents) if self.documents else 0
        self._document_frequency = Counter(token for tokens in self._tokenized_documents for token in set(tokens))

    # gọi semantic retrieval
    def retrieve_semantic(self, query: str, k: int = 8) -> list[Document]:
        return self.semantic_retriever.retrieve(query, k)

    # BM25-like; tách query thành các từ
    def retrieve_keyword(self, query: str, k: int = 8) -> list[Document]:
        # BM25 lexical retriever over cached chunks. It creates no second vector
        # index and never embeds a document.
        terms = set(_tokenize(query))
        if not terms:
            return []
        scored: list[tuple[float, Document]] = []
        total_documents, k1, b = len(self.documents), 1.5, 0.75
        for doc, tokens in zip(self.documents, self._tokenized_documents):
            counts, length, score = Counter(tokens), len(tokens), 0.0
            for term in terms:
                frequency = counts[term]
                if not frequency:
                    continue
                idf = log(1 + (total_documents - self._document_frequency[term] + 0.5) / (self._document_frequency[term] + 0.5))
                score += idf * frequency * (k1 + 1) / (frequency + k1 * (1 - b + b * length / self._avg_doc_length))
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:k]]


    def retrieve(self, query: str, k: int = 8) -> list[Document]:
        candidate_k = max(k * 3, 10)
        scores: dict[str, float] = {}
        docs: dict[str, Document] = {}
        for result_set in (self.retrieve_semantic(query, candidate_k), self.retrieve_keyword(query, candidate_k)):
            for rank, document in enumerate(result_set, 1):
                key = _doc_id(document)
                scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank)
                docs[key] = document
        output = []
        for rank, key in enumerate(sorted(scores, key=scores.get, reverse=True)[:k], 1):
            doc = docs[key]
            metadata = dict(doc.metadata)
            metadata.update({"rrf_score": scores[key], "retrieval_rank": rank})
            output.append(Document(page_content=doc.page_content, metadata=metadata))
        return output
