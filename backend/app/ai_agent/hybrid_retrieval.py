from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever

from dotenv import load_dotenv


load_dotenv()


FAISS_PATH = Path(__file__).resolve().parent.parent.parent / 'faiss_index'
embedder = OpenAIEmbeddings(
    model='text-embedding-3-large'
)

# lấy phần embedding ở T12
db = FAISS.load_local(
    FAISS_PATH,
    embedder,
    allow_dangerous_deserialization=True
)

# Semantic retriever (giống T13)
semantic_retriever = db.as_retriever(
    search_type='similarity_score_threshold',
    search_kwargs={'k': 3, 'score_threshold': 0.2}
)


def _load_indexed_documents():
    """
    Lấy toàn bộ Document đã được embed trong FAISS index (T12) để build
    keyword index (BM25) trên đúng nội dung đã index - tránh phải đọc lại
    file chunking JSON riêng, dễ bị lệch nếu FAISS index được cập nhật sau.
    """
    return list(db.docstore._dict.values())


_indexed_docs = _load_indexed_documents()
print(f'Đã nạp {len(_indexed_docs)} chunks đã index để build Keyword (BM25) retriever.')

# Keyword retriever (T14 - BM25)
keyword_retriever = BM25Retriever.from_documents(_indexed_docs)
keyword_retriever.k = 3

RRF_K = 60  # hằng số Reciprocal Rank Fusion (giá trị phổ biến, giảm ảnh hưởng hạng thấp)


def _doc_id(doc) -> str:
    """
    ID duy nhất của 1 chunk, dùng để hợp nhất kết quả giữa 2 retriever.
    Ưu tiên chunk_id có sẵn trong metadata (từ T14 - chunking.py);
    fallback sang document_id + chunk_index nếu thiếu chunk_id.
    """
    meta = doc.metadata
    if meta.get('chunk_id') is not None:
        return str(meta['chunk_id'])
    return f"{meta.get('document_id', '')}_{meta.get('chunk_index', '')}"


def retrieve_semantic(query, k=3):
    """Semantic-only retrieval (T13), dùng để so sánh với Hybrid."""
    semantic_retriever.search_kwargs['k'] = k
    return semantic_retriever.invoke(query)


def retrieve_keyword(query, k=3):
    """Keyword-only retrieval (BM25), dùng để so sánh với Hybrid."""
    keyword_retriever.k = k
    return keyword_retriever.invoke(query)


def retrieve_hybrid(query, k=3):
    """
    Hybrid Retrieval (T14): kết hợp Semantic search (T13) và Keyword search
    (BM25) bằng Reciprocal Rank Fusion (RRF).

    RRF được chọn vì điểm cosine similarity (semantic) và điểm BM25 (keyword)
    không cùng thang đo - không thể cộng điểm trực tiếp mà không làm 1 bên
    lấn át bên kia. RRF chỉ dựa vào *thứ hạng* của mỗi kết quả trong từng
    danh sách nên không cần chuẩn hóa điểm số giữa 2 phương pháp:

        RRF_score(doc) = sum( 1 / (RRF_K + rank_i) ) trên mỗi danh sách mà doc xuất hiện
    """
    # Lấy candidate rộng hơn k để RRF có đủ ứng viên tốt trước khi cắt còn k.
    candidate_k = max(k * 3, 10)

    semantic_retriever.search_kwargs['k'] = candidate_k
    semantic_results = semantic_retriever.invoke(query)

    keyword_retriever.k = candidate_k
    keyword_results = keyword_retriever.invoke(query)

    rrf_scores = {}
    doc_by_id = {}

    for result_list in (semantic_results, keyword_results):
        for rank, doc in enumerate(result_list):
            doc_id = _doc_id(doc)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_by_id[doc_id] = doc

    ranked_ids = sorted(rrf_scores, key=lambda i: rrf_scores[i], reverse=True)

    return [doc_by_id[doc_id] for doc_id in ranked_ids[:k]]


if __name__ == '__main__':
    query = input('Question: ')

    print('\n=== SEMANTIC (T13) ===')
    for i, doc in enumerate(retrieve_semantic(query), start=1):
        print(f'--- Result {i} ---')
        print('Content:', doc.page_content)
        print('Metadata:', doc.metadata)

    print('\n=== KEYWORD (T14 - BM25) ===')
    for i, doc in enumerate(retrieve_keyword(query), start=1):
        print(f'--- Result {i} ---')
        print('Content:', doc.page_content)
        print('Metadata:', doc.metadata)

    print('\n=== HYBRID (T14 - RRF) ===')
    for i, doc in enumerate(retrieve_hybrid(query), start=1):
        print(f'--- Result {i} ---')
        print('Content:', doc.page_content)
        print('Metadata:', doc.metadata)
