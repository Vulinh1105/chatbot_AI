"""
evaluate_retrieval.py
----------------------
T14 - Comparison report: so sánh hiệu năng giữa Semantic (vector) retrieval
thông thường (T13) và Hybrid retrieval (T14 - Semantic + Keyword/BM25 qua RRF)
trên một tập dữ liệu đánh giá (evaluation set).

Metrics (chuẩn IR, tính ở ngưỡng top-k):
- Hit Rate@k : tỉ lệ câu hỏi có ít nhất 1 kết quả đúng nằm trong top-k.
- Precision@k: trung bình (số kết quả đúng trong top-k / k).
- MRR@k      : Mean Reciprocal Rank - trung bình 1/hạng của kết quả đúng
               đầu tiên (0 nếu không có kết quả đúng nào trong top-k).

Cách chạy:
    python evaluate_retrieval.py
"""

from dataclasses import dataclass

from hybrid_retrieval import retrieve_semantic, retrieve_hybrid, _doc_id


@dataclass
class EvalCase:
    query: str
    relevant_ids: set  # tập chunk_id (hoặc document_id_chunk_index) đúng cho câu hỏi này


# Tập dữ liệu đánh giá mẫu - THAY bằng bộ câu hỏi + nhãn thật của dự án
# (chunk_id lấy từ metadata thật trong faiss_index / file 1_chunking.json).
DEFAULT_EVAL_SET: list[EvalCase] = [
    EvalCase("Ví dụ câu hỏi 1 - thay bằng câu hỏi thật", {"chunk_id_dung_1"}),
    EvalCase("Ví dụ câu hỏi 2 - thay bằng câu hỏi thật", {"chunk_id_dung_2"}),
]


def _hit_rate(retrieved_ids, relevant_ids) -> float:
    return 1.0 if any(rid in relevant_ids for rid in retrieved_ids) else 0.0


def _precision_at_k(retrieved_ids, relevant_ids) -> float:
    if not retrieved_ids:
        return 0.0
    hits = sum(1 for rid in retrieved_ids if rid in relevant_ids)
    return hits / len(retrieved_ids)


def _reciprocal_rank(retrieved_ids, relevant_ids) -> float:
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def evaluate_retriever(search_fn, eval_set: list[EvalCase], top_k: int = 3) -> dict:
    """Chạy search_fn(query, top_k) trên toàn bộ eval_set, tính metric trung bình."""
    hit_rates, precisions, reciprocal_ranks = [], [], []
    per_query_detail = []

    for case in eval_set:
        docs = search_fn(case.query, top_k)
        retrieved_ids = [_doc_id(d) for d in docs]

        hr = _hit_rate(retrieved_ids, case.relevant_ids)
        prec = _precision_at_k(retrieved_ids, case.relevant_ids)
        rr = _reciprocal_rank(retrieved_ids, case.relevant_ids)

        hit_rates.append(hr)
        precisions.append(prec)
        reciprocal_ranks.append(rr)

        per_query_detail.append({
            "query": case.query,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": sorted(case.relevant_ids),
            "hit": hr == 1.0,
        })

    n = len(eval_set)
    return {
        "hit_rate_at_k": round(sum(hit_rates) / n, 4),
        "precision_at_k": round(sum(precisions) / n, 4),
        "mrr_at_k": round(sum(reciprocal_ranks) / n, 4),
        "num_queries": n,
        "details": per_query_detail,
    }


def print_comparison_report(semantic_metrics: dict, hybrid_metrics: dict, top_k: int) -> None:
    print("\n" + "=" * 60)
    print(f" BÁO CÁO SO SÁNH: Semantic Search vs Hybrid Search (top_k={top_k})")
    print("=" * 60)

    print(f"{'Metric':<20}{'Semantic':>15}{'Hybrid':>15}{'Chênh lệch':>15}")
    print("-" * 60)

    for label, key in (("Hit Rate@k", "hit_rate_at_k"),
                        ("Precision@k", "precision_at_k"),
                        ("MRR@k", "mrr_at_k")):
        s_val, h_val = semantic_metrics[key], hybrid_metrics[key]
        diff = round(h_val - s_val, 4)
        print(f"{label:<20}{s_val:>15.4f}{h_val:>15.4f}{diff:>+15.4f}")

    print("-" * 60)
    print(f"Số câu hỏi đánh giá: {semantic_metrics['num_queries']}")

    print("\n--- Chi tiết theo từng câu hỏi ---")
    for s, h in zip(semantic_metrics["details"], hybrid_metrics["details"]):
        print(f"\nQuery: {s['query']}")
        print(f"  Relevant (đúng)  : {s['relevant_ids']}")
        print(f"  Semantic trả về  : {s['retrieved_ids']} ({'✓ hit' if s['hit'] else '✗ miss'})")
        print(f"  Hybrid trả về    : {h['retrieved_ids']} ({'✓ hit' if h['hit'] else '✗ miss'})")


def run_comparison(eval_set: list[EvalCase] = DEFAULT_EVAL_SET, top_k: int = 3):
    """Chạy full comparison giữa Semantic (T13) và Hybrid (T14), in báo cáo."""
    semantic_metrics = evaluate_retriever(retrieve_semantic, eval_set, top_k)
    hybrid_metrics = evaluate_retriever(retrieve_hybrid, eval_set, top_k)

    print_comparison_report(semantic_metrics, hybrid_metrics, top_k)

    return semantic_metrics, hybrid_metrics


if __name__ == "__main__":
    run_comparison()
