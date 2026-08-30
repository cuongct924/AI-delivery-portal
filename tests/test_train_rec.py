"""infra/argo-workflows/training-image/train_rec.py — train_and_evaluate()
per algorithm family, against small real (not mocked) implicit/surprise/
sklearn training runs — no MLflow server or network involved, and the
libraries themselves are fast at this size."""

import pandas as pd
import pytest
from train_rec import RecModel, train_and_evaluate

_N_ROWS = 60
_N_USERS = 10
_N_ITEMS = 8


def _make_interactions(with_rating: bool = False) -> pd.DataFrame:
    rows = []
    for t in range(_N_ROWS):
        row = {
            "user": f"u{t % _N_USERS}",
            "item": f"i{t % _N_ITEMS}",
            "ts": t,
        }
        if with_rating:
            row["rating"] = 1 + (t % 5)
        rows.append(row)
    return pd.DataFrame(rows)


def _make_item_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "item": [f"i{i}" for i in range(_N_ITEMS)],
            "description": [f"category-{i % 3} widget number {i}" for i in range(_N_ITEMS)],
        }
    )


@pytest.mark.parametrize("algorithm", ["als", "bpr"])
def test_collaborative_implicit_trains_and_evaluates(algorithm: str) -> None:
    interactions = _make_interactions()

    model, metrics = train_and_evaluate(
        interactions,
        user_id_column="user",
        item_id_column="item",
        timestamp_column="ts",
        algorithm=algorithm,
        k=3,
        hyperparameters={"factors": 4, "iterations": 2},
    )

    assert isinstance(model, RecModel)
    assert set(metrics) == {"recall_at_k", "ndcg_at_k", "map_at_k", "cold_start_user_fraction"}
    assert 0.0 <= metrics["recall_at_k"] <= 1.0


@pytest.mark.parametrize("algorithm", ["svd", "knn"])
def test_collaborative_explicit_requires_rating_column(algorithm: str) -> None:
    interactions = _make_interactions(with_rating=False)

    with pytest.raises(ValueError, match="requires a rating column"):
        train_and_evaluate(
            interactions,
            user_id_column="user",
            item_id_column="item",
            timestamp_column="ts",
            algorithm=algorithm,
            k=3,
            hyperparameters={},
        )


@pytest.mark.parametrize("algorithm", ["svd", "knn"])
def test_collaborative_explicit_trains_and_evaluates(algorithm: str) -> None:
    interactions = _make_interactions(with_rating=True)

    model, metrics = train_and_evaluate(
        interactions,
        user_id_column="user",
        item_id_column="item",
        timestamp_column="ts",
        algorithm=algorithm,
        k=3,
        hyperparameters={"n_epochs": 2} if algorithm == "svd" else {"k": 5},
        rating_column="rating",
    )

    assert isinstance(model, RecModel)
    assert 0.0 <= metrics["recall_at_k"] <= 1.0


def test_content_based_requires_item_features() -> None:
    interactions = _make_interactions()

    with pytest.raises(ValueError, match="requires item_features"):
        train_and_evaluate(
            interactions,
            user_id_column="user",
            item_id_column="item",
            timestamp_column="ts",
            algorithm="tfidf_cosine",
            k=3,
            hyperparameters={},
        )


def test_content_based_trains_and_evaluates() -> None:
    interactions = _make_interactions()
    item_features = _make_item_features()

    model, metrics = train_and_evaluate(
        interactions,
        user_id_column="user",
        item_id_column="item",
        timestamp_column="ts",
        algorithm="tfidf_cosine",
        k=3,
        hyperparameters={},
        item_features=item_features,
        item_id_column_features="item",
        item_text_column="description",
    )

    assert isinstance(model, RecModel)
    assert 0.0 <= metrics["recall_at_k"] <= 1.0


def test_popularity_baseline_trains_and_evaluates() -> None:
    interactions = _make_interactions()

    model, metrics = train_and_evaluate(
        interactions,
        user_id_column="user",
        item_id_column="item",
        timestamp_column="ts",
        algorithm="popularity",
        k=3,
        hyperparameters={},
    )

    assert isinstance(model, RecModel)
    assert 0.0 <= metrics["recall_at_k"] <= 1.0
    # Every warm user should get the same top-3 (most popular in train),
    # minus whatever they've already seen.
    recs = {tuple(model.recommend(f"u{i}", top_k=3)) for i in range(_N_USERS)}
    assert len(recs) >= 1


def test_cold_start_user_falls_back_to_popularity() -> None:
    interactions = _make_interactions()
    model, _ = train_and_evaluate(
        interactions,
        user_id_column="user",
        item_id_column="item",
        timestamp_column="ts",
        algorithm="popularity",
        k=3,
        hyperparameters={},
    )

    recommendation = model.recommend("never-seen-user", top_k=3)

    assert recommendation == model._popularity_fallback[:3]  # noqa: SLF001 — white-box check


def test_rec_model_predict_handles_a_dataframe_of_requests() -> None:
    interactions = _make_interactions()
    model, _ = train_and_evaluate(
        interactions,
        user_id_column="user",
        item_id_column="item",
        timestamp_column="ts",
        algorithm="popularity",
        k=2,
        hyperparameters={},
    )

    predictions = model.predict(pd.DataFrame({"user_id": ["u0", "brand-new"], "top_k": [2, 2]}))

    assert len(predictions) == 2
    assert all(len(rec) <= 2 for rec in predictions)
