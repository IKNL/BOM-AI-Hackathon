"""Compute retrieval quality metrics from query results."""


def recall_at_k(relevant_found: int, total_relevant: int, k: int = 5) -> float:
    """Fraction of known-relevant items found in top-k results."""
    if total_relevant == 0:
        return 0.0
    return min(relevant_found, k) / total_relevant


def precision_at_k(relevance_scores: list[float], k: int = 5) -> float:
    """Fraction of top-k results that are relevant."""
    top_k = relevance_scores[:k]
    if not top_k:
        return 0.0
    return sum(top_k) / len(top_k)


def mrr(relevance_scores: list[float]) -> float:
    """Mean Reciprocal Rank -- 1/rank of first relevant result."""
    for i, score in enumerate(relevance_scores):
        if score > 0.5:
            return 1.0 / (i + 1)
    return 0.0


def aggregate_metrics(per_query_results: list[dict]) -> dict:
    """Compute aggregate metrics across all queries.

    Each entry in per_query_results should have:
    - recall_at_5: float
    - precision_at_5: float
    - mrr: float
    """
    n = len(per_query_results)
    if n == 0:
        return {"recall_at_5": 0.0, "precision_at_5": 0.0, "mrr": 0.0}

    return {
        "recall_at_5": sum(r["recall_at_5"] for r in per_query_results) / n,
        "precision_at_5": sum(r["precision_at_5"] for r in per_query_results) / n,
        "mrr": sum(r["mrr"] for r in per_query_results) / n,
    }


def compare_to_baseline(baseline: dict, variant: dict) -> dict:
    """Compute relative improvement over baseline for each metric."""
    result = {}
    for key in baseline:
        b = baseline[key]
        v = variant[key]
        if b > 0:
            result[f"{key}_delta_pct"] = ((v - b) / b) * 100
        else:
            result[f"{key}_delta_pct"] = 0.0 if v == 0 else float("inf")
    return result
