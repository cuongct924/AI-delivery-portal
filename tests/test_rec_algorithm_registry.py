"""infra/argo-workflows/training-image/rec_algorithm_registry.py."""

import pytest
from rec_algorithm_registry import REC_ALGORITHMS, get_rec_algorithm_spec


def test_registry_has_no_lightfm_entry() -> None:
    # Dropped — fails to build on Python 3.12/modern setuptools (mục 6e.5).
    assert "lightfm" not in REC_ALGORITHMS


@pytest.mark.parametrize(
    ("algorithm", "family"),
    [
        ("als", "collaborative_implicit"),
        ("bpr", "collaborative_implicit"),
        ("svd", "collaborative_explicit"),
        ("knn", "collaborative_explicit"),
        ("tfidf_cosine", "content_based"),
        ("popularity", "baseline"),
    ],
)
def test_get_rec_algorithm_spec_returns_matching_family(algorithm: str, family: str) -> None:
    assert get_rec_algorithm_spec(algorithm).family == family


def test_get_rec_algorithm_spec_rejects_unknown_algorithm() -> None:
    with pytest.raises(ValueError, match="unknown algorithm"):
        get_rec_algorithm_spec("lightfm")


def test_only_explicit_family_requires_rating() -> None:
    for algorithm, spec in REC_ALGORITHMS.items():
        assert spec.requires_rating == (spec.family == "collaborative_explicit"), algorithm


def test_only_content_based_requires_item_features() -> None:
    for algorithm, spec in REC_ALGORITHMS.items():
        assert spec.requires_item_features == (spec.family == "content_based"), algorithm
