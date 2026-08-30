"""infra/argo-workflows/training-image/rec_metrics.py — recall@k/ndcg@k/
map@k against hand-computed expected values."""

import math

import pytest
from rec_metrics import average_precision_at_k, compute_ranking_metrics, ndcg_at_k, recall_at_k


def test_recall_at_k_counts_hits_over_all_relevant() -> None:
    # 2 of 3 relevant items appear in the top 3 recommended.
    assert recall_at_k(["a", "b", "c"], {"a", "c", "z"}, k=3) == pytest.approx(2 / 3)


def test_recall_at_k_respects_cutoff() -> None:
    # "c" (the only relevant item) is outside the top 2.
    assert recall_at_k(["a", "b", "c"], {"c"}, k=2) == 0.0


def test_recall_at_k_empty_relevant_set_is_zero() -> None:
    assert recall_at_k(["a", "b"], set(), k=2) == 0.0


def test_ndcg_at_k_perfect_ranking_is_one() -> None:
    assert ndcg_at_k(["a", "b"], {"a", "b"}, k=2) == pytest.approx(1.0)


def test_ndcg_at_k_rewards_earlier_relevant_items() -> None:
    # Same 1 hit, but earlier in the ranking scores higher.
    early = ndcg_at_k(["a", "x", "y"], {"a"}, k=3)
    late = ndcg_at_k(["x", "y", "a"], {"a"}, k=3)
    assert early > late
    assert late == pytest.approx(1 / math.log2(4))


def test_ndcg_at_k_no_hits_is_zero() -> None:
    assert ndcg_at_k(["x", "y"], {"a"}, k=2) == 0.0


def test_average_precision_at_k_all_hits_first_is_one() -> None:
    assert average_precision_at_k(["a", "b"], {"a", "b"}, k=2) == pytest.approx(1.0)


def test_average_precision_at_k_penalizes_late_hits() -> None:
    # hit at position 2 (1-indexed) -> precision 1/2, averaged over min(relevant, k)=1.
    assert average_precision_at_k(["x", "a"], {"a"}, k=2) == pytest.approx(0.5)


def test_compute_ranking_metrics_averages_over_users() -> None:
    recommendations = {"u1": ["a", "b"], "u2": ["x", "y"]}
    ground_truth = {"u1": {"a"}, "u2": {"z"}}

    metrics = compute_ranking_metrics(recommendations, ground_truth, k=2)

    assert metrics["recall_at_k"] == pytest.approx((1.0 + 0.0) / 2)
    assert set(metrics) == {"recall_at_k", "ndcg_at_k", "map_at_k"}


def test_compute_ranking_metrics_rejects_empty_ground_truth() -> None:
    with pytest.raises(ValueError, match="no warm users"):
        compute_ranking_metrics({}, {}, k=5)
