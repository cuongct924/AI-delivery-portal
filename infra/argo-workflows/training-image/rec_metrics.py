"""Ranking metrics for RecSys — recall@k/ndcg@k/map@k, averaged per-user
over the warm subset the caller (train_rec.py) already filtered to
(cold-start users/items excluded from the gate, reported separately as
reference info)."""

import math


def _dcg_at_k(relevances: list[int], k: int) -> float:
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances[:k]))


def recall_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Fraction of `relevant` items that appear in the top `k`
    recommendations."""
    if not relevant:
        return 0.0
    hits = len(set(recommended[:k]) & relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain — rewards relevant items
    appearing earlier in the ranking, normalized against the best possible
    ordering."""
    relevances = [1 if item in relevant else 0 for item in recommended[:k]]
    dcg = _dcg_at_k(relevances, k)
    ideal_relevances = [1] * min(len(relevant), k)
    idcg = _dcg_at_k(ideal_relevances, k)
    return dcg / idcg if idcg > 0 else 0.0


def average_precision_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Mean of precision-at-i for every relevant item found within the top
    `k`, i.e. the per-user term MAP@k averages over users."""
    if not relevant:
        return 0.0
    hits = 0
    precisions: list[float] = []
    for idx, item in enumerate(recommended[:k]):
        if item in relevant:
            hits += 1
            precisions.append(hits / (idx + 1))
    return sum(precisions) / min(len(relevant), k) if precisions else 0.0


def compute_ranking_metrics(
    recommendations: dict[str, list[str]], ground_truth: dict[str, set[str]], k: int
) -> dict[str, float]:
    """Averages recall@k/ndcg@k/map@k over every user in `ground_truth`.

    Args:
        recommendations: user_id -> ranked recommended item ids.
        ground_truth: user_id -> set of relevant (test-period-interacted)
            item ids — already filtered to warm users by the caller.
        k: Cutoff — must match how `recommendations` were generated.

    Returns:
        `dict` with exactly `recall_at_k`/`ndcg_at_k`/`map_at_k` (mục
        6e.3 — `map_at_k` has no gate threshold but is still logged, since
        it's cheap to compute alongside the other 2).

    Raises:
        ValueError: `ground_truth` is empty — nothing to average over.
    """
    if not ground_truth:
        raise ValueError(
            "no warm users to evaluate — check the temporal split and k-core filtering"
        )
    recalls: list[float] = []
    ndcgs: list[float] = []
    maps: list[float] = []
    for user_id, relevant in ground_truth.items():
        recommended = recommendations.get(user_id, [])
        recalls.append(recall_at_k(recommended, relevant, k))
        ndcgs.append(ndcg_at_k(recommended, relevant, k))
        maps.append(average_precision_at_k(recommended, relevant, k))
    return {
        "recall_at_k": sum(recalls) / len(recalls),
        "ndcg_at_k": sum(ndcgs) / len(ndcgs),
        "map_at_k": sum(maps) / len(maps),
    }
