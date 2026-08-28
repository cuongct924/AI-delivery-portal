"""Registry of Recommendation System algorithms (Phase 8, mục 6e,
docs/mlops-lifecycle-software-template.md) — keyed by algorithm name,
grouped by family (mục 6e.1).

Unlike `algorithm_registry.py` (mục 3.1), the underlying libraries don't
share a `fit`/`predict` interface — `implicit` works on sparse matrices,
`surprise` on its own `Trainset`, `tfidf_cosine` is hand-assembled from
sklearn primitives, `popularity` is pure pandas. Each family's actual
training/recommending logic lives in `train_rec.py`, not here — this
registry only tracks name -> family and which raw data each needs, driving
the Scaffolder form and `train_rec.py`'s dispatch.

No `lightfm` entry (hybrid family, mục 6e.1's table) — dropped after
discovering it fails to build on Python 3.12/modern setuptools (`AttributeError:
'dict' object has no attribute '__LIGHTFM_SETUP__'`, a known upstream
incompatibility, not fixable from this repo) — see mục 6e.5.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class RecAlgorithmSpec:
    """One registry entry.

    Attributes:
        family: One of "collaborative_implicit", "collaborative_explicit",
            "content_based", "baseline" — drives which training/
            recommending code path `train_rec.py` dispatches to.
        requires_rating: True for algorithms that need explicit feedback
            (a rating column) — collaborative_explicit only.
        requires_item_features: True for algorithms that need
            `itemFeaturesUri` — content_based only.
    """

    family: str
    requires_rating: bool
    requires_item_features: bool


REC_ALGORITHMS: Final[dict[str, RecAlgorithmSpec]] = {
    "als": RecAlgorithmSpec(
        "collaborative_implicit", requires_rating=False, requires_item_features=False
    ),
    "bpr": RecAlgorithmSpec(
        "collaborative_implicit", requires_rating=False, requires_item_features=False
    ),
    "svd": RecAlgorithmSpec(
        "collaborative_explicit", requires_rating=True, requires_item_features=False
    ),
    "knn": RecAlgorithmSpec(
        "collaborative_explicit", requires_rating=True, requires_item_features=False
    ),
    "tfidf_cosine": RecAlgorithmSpec(
        "content_based", requires_rating=False, requires_item_features=True
    ),
    "popularity": RecAlgorithmSpec("baseline", requires_rating=False, requires_item_features=False),
}


def get_rec_algorithm_spec(algorithm: str) -> RecAlgorithmSpec:
    """Looks up a registry entry.

    Args:
        algorithm: Registry key, e.g. "als".

    Returns:
        The matching RecAlgorithmSpec.

    Raises:
        ValueError: `algorithm` isn't in the registry.
    """
    spec = REC_ALGORITHMS.get(algorithm)
    if spec is None:
        raise ValueError(
            f"unknown algorithm {algorithm!r} — must be one of {sorted(REC_ALGORITHMS)}"
        )
    return spec
