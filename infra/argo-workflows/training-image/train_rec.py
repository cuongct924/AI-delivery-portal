"""Recommendation System training — Golden Path #3 (Phase 8, mục 6e,
docs/mlops-lifecycle-software-template.md). A separate entrypoint from
train.py — its own Argo WorkflowTemplate, its own env vars, its own
multi-file dataset contract (mục 6e.2), not a Golden Path #1 architecture
value.

Dispatches per algorithm family (rec_algorithm_registry.py) since the
underlying libraries don't share a fit/predict interface: `implicit` (a
sparse user-item matrix), `surprise` (its own `Trainset`), `tfidf_cosine`
(hand-assembled sklearn primitives), `popularity` (pure pandas) — see mục
6e.5 for the full delta writeup, including why `lightfm`/hybrid isn't here.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, cast

import mlflow
import numpy as np
import pandas as pd
from implicit.als import AlternatingLeastSquares
from implicit.bpr import BayesianPersonalizedRanking

# mlflow's top-level stub doesn't declare pyfunc as an exported attribute
# (same stub gap noted in train.py).
from mlflow import pyfunc as mlflow_pyfunc
from pyfunc_wrapper import GenericPyfuncWrapper
from rec_algorithm_registry import get_rec_algorithm_spec
from rec_metrics import compute_ranking_metrics
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise import SVD, KNNBasic, Reader
from surprise import Dataset as SurpriseDataset

_TRAIN_FRACTION = 0.8


def _read_dataset_digest(path: Path) -> str:
    """Reads the DVC md5 hash from `<path>.dvc` — same convention as
    train.py's own `_read_dataset_digest`, duplicated (not imported) so
    this entrypoint stays self-contained and doesn't drag in train.py's
    unrelated heavy imports (torch, xgboost, ...) for a Golden Path that
    never uses them."""
    dvc_path = path.with_name(path.name + ".dvc")
    dvc_text = dvc_path.read_text()
    md5_match = re.search(r"md5:\s*(\S+)", dvc_text)
    if md5_match is None:
        raise RuntimeError(f"no md5 hash found in {dvc_path}")
    return md5_match.group(1)


class RecModel:
    """Wraps a trained recommender for serving (mục 6e.4) — `.predict()`
    takes a DataFrame with `user_id`/`top_k` columns (1 row per request)
    and returns a ranked list of recommended item ids per row, falling
    back to the popularity baseline for any user with no training history
    at all (cold-start — mục 6e.4 requires this fallback live in
    `predict()` itself; no KServe/MLflow mechanism does it automatically).
    """

    def __init__(
        self,
        family: str,
        state: dict[str, Any],
        popularity_fallback: list[str],
        seen_items_by_user: dict[str, set[str]],
    ) -> None:
        self._family = family
        self._state = state
        self._popularity_fallback = popularity_fallback
        self._seen_items_by_user = seen_items_by_user

    def predict(self, model_input: pd.DataFrame) -> list[list[str]]:
        return [
            self.recommend(str(row["user_id"]), int(row["top_k"]))
            for _, row in model_input.iterrows()
        ]

    def recommend(self, user_id: str, top_k: int) -> list[str]:
        if user_id not in self._seen_items_by_user:
            return self._popularity_fallback[:top_k]
        seen = self._seen_items_by_user[user_id]
        return _recommend_for_user(
            self._family, self._state, user_id, top_k, seen, self._popularity_fallback
        )


def _recommend_for_user(
    family: str,
    state: dict[str, Any],
    user_id: str,
    top_k: int,
    seen: set[str],
    popularity_fallback: list[str],
) -> list[str]:
    if family == "collaborative_implicit":
        model = state["model"]
        user_idx = state["user_index"][user_id]
        item_ids = state["item_ids"]
        user_items = state["user_items_matrix"]
        item_indices, _scores = model.recommend(user_idx, user_items[user_idx], N=top_k)
        return [item_ids[i] for i in item_indices]
    if family == "collaborative_explicit":
        algo = state["algo"]
        candidates = [item for item in state["catalog"] if item not in seen]
        scored = [(item, algo.predict(user_id, item).est) for item in candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [item for item, _score in scored[:top_k]]
    if family == "content_based":
        profile = state["user_profiles"].get(user_id)
        if profile is None:
            return [item for item in popularity_fallback if item not in seen][:top_k]
        item_ids = state["item_ids"]
        similarities = cosine_similarity(profile, state["item_vectors"])[0]
        ranked = np.argsort(-similarities)
        recommended: list[str] = []
        for idx in ranked:
            item_id = item_ids[idx]
            if item_id not in seen:
                recommended.append(item_id)
            if len(recommended) >= top_k:
                break
        return recommended
    if family == "baseline":
        return [item for item in popularity_fallback if item not in seen][:top_k]
    raise ValueError(f"unknown family {family!r}")


def _train_implicit(
    train_df: pd.DataFrame, algorithm: str, hyperparameters: dict[str, object]
) -> dict[str, Any]:
    user_ids: list[str] = sorted(cast(list[str], train_df["user_id"].unique()))
    item_ids: list[str] = sorted(cast(list[str], train_df["item_id"].unique()))
    user_index: dict[str, int] = {user_id: idx for idx, user_id in enumerate(user_ids)}
    item_index: dict[str, int] = {item_id: idx for idx, item_id in enumerate(item_ids)}
    # .map(dict.get), not .map(dict) — pandas-stubs' .map() overload set
    # only resolves a callable, not a mapping, even though both work at
    # runtime.
    rows = train_df["user_id"].map(user_index.get)
    cols = train_df["item_id"].map(item_index.get)
    values = np.ones(len(train_df), dtype="float32")
    user_items_matrix = csr_matrix((values, (rows, cols)), shape=(len(user_ids), len(item_ids)))

    if algorithm == "als":
        model = AlternatingLeastSquares(
            factors=int(cast(int, hyperparameters.get("factors", 50))),
            regularization=float(cast(float, hyperparameters.get("regularization", 0.01))),
            iterations=int(cast(int, hyperparameters.get("iterations", 15))),
            use_gpu=False,
        )
    else:
        model = BayesianPersonalizedRanking(
            factors=int(cast(int, hyperparameters.get("factors", 50))),
            learning_rate=float(cast(float, hyperparameters.get("learning_rate", 0.01))),
            regularization=float(cast(float, hyperparameters.get("regularization", 0.01))),
            iterations=int(cast(int, hyperparameters.get("iterations", 15))),
            use_gpu=False,
        )
    model.fit(user_items_matrix, show_progress=False)
    return {
        "model": model,
        "user_index": user_index,
        "item_ids": item_ids,
        "user_items_matrix": user_items_matrix,
    }


def _train_explicit(
    train_df: pd.DataFrame, algorithm: str, hyperparameters: dict[str, object]
) -> dict[str, Any]:
    reader = Reader(rating_scale=(train_df["rating"].min(), train_df["rating"].max()))
    dataset = SurpriseDataset.load_from_df(train_df[["user_id", "item_id", "rating"]], reader)
    trainset = dataset.build_full_trainset()
    algo: Any
    if algorithm == "svd":
        algo = SVD(
            n_factors=int(cast(int, hyperparameters.get("n_factors", 50))),
            n_epochs=int(cast(int, hyperparameters.get("n_epochs", 20))),
            lr_all=float(cast(float, hyperparameters.get("lr_all", 0.005))),
            reg_all=float(cast(float, hyperparameters.get("reg_all", 0.02))),
        )
    else:
        algo = KNNBasic(
            k=int(cast(int, hyperparameters.get("k", 40))),
            sim_options={"user_based": bool(hyperparameters.get("user_based", True))},
            verbose=False,
        )
    algo.fit(trainset)
    return {"algo": algo, "catalog": sorted(train_df["item_id"].unique())}


def _train_content_based(
    item_features: pd.DataFrame,
    item_id_column_features: str,
    item_text_column: str,
    seen_items_by_user: dict[str, set[str]],
) -> dict[str, Any]:
    features = item_features.rename(
        columns={item_id_column_features: "item_id", item_text_column: "text"}
    )
    features = features.dropna(subset=["text"]).drop_duplicates(subset=["item_id"])
    item_ids = features["item_id"].astype(str).tolist()
    item_index = {item_id: idx for idx, item_id in enumerate(item_ids)}
    vectorizer = TfidfVectorizer(max_features=500)
    # sklearn/scipy stubs don't resolve fancy-indexing + .mean() on the
    # sparse matrix TfidfVectorizer actually returns at runtime.
    item_vectors = cast(Any, vectorizer.fit_transform(features["text"]))

    user_profiles: dict[str, Any] = {}
    for user_id, items in seen_items_by_user.items():
        indices = [item_index[item_id] for item_id in items if item_id in item_index]
        if not indices:
            continue
        user_profiles[user_id] = np.asarray(item_vectors[indices].mean(axis=0))

    return {"item_ids": item_ids, "item_vectors": item_vectors, "user_profiles": user_profiles}


def train_and_evaluate(
    interactions: pd.DataFrame,
    user_id_column: str,
    item_id_column: str,
    timestamp_column: str,
    algorithm: str,
    k: int,
    hyperparameters: dict[str, object],
    rating_column: str | None = None,
    item_features: pd.DataFrame | None = None,
    item_id_column_features: str | None = None,
    item_text_column: str | None = None,
) -> tuple[RecModel, dict[str, float]]:
    """Trains 1 RecSys algorithm and evaluates it on a global temporal
    split's warm users (mục 6e.2/6e.3).

    Returns:
        (RecModel, metrics) — `metrics` has `recall_at_k`/`ndcg_at_k`/
        `map_at_k` (mục 6e.3) plus `cold_start_user_fraction` (reference
        info, not gated).

    Raises:
        ValueError: the chosen algorithm's data requirement (rating column
            / item features) isn't satisfied.
    """
    spec = get_rec_algorithm_spec(algorithm)
    if spec.requires_rating and rating_column is None:
        raise ValueError(f"algorithm {algorithm!r} requires a rating column (explicit feedback)")
    if spec.requires_item_features and item_features is None:
        raise ValueError(f"algorithm {algorithm!r} requires item_features")

    rename = {user_id_column: "user_id", item_id_column: "item_id", timestamp_column: "timestamp"}
    if rating_column is not None:
        rename[rating_column] = "rating"
    df = interactions.rename(columns=rename)
    df["user_id"] = df["user_id"].astype(str)
    df["item_id"] = df["item_id"].astype(str)
    df = df.sort_values("timestamp").reset_index(drop=True)

    split_idx = int(len(df) * _TRAIN_FRACTION)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    train_users = set(train_df["user_id"])
    train_items = set(train_df["item_id"])
    seen_items_by_user = cast(
        dict[str, set[str]], train_df.groupby("user_id")["item_id"].apply(set).to_dict()
    )

    # Warm = present in train (mục 6e.3) — cold interactions are reported
    # (cold_start_user_fraction below), never gated.
    is_warm = test_df["user_id"].isin(train_users) & test_df["item_id"].isin(train_items)
    warm_test_df = test_df[is_warm]
    ground_truth = cast(
        dict[str, set[str]], warm_test_df.groupby("user_id")["item_id"].apply(set).to_dict()
    )

    popularity_fallback = train_df["item_id"].value_counts().index.tolist()

    state: dict[str, Any]
    if spec.family == "collaborative_implicit":
        state = _train_implicit(train_df, algorithm, hyperparameters)
    elif spec.family == "collaborative_explicit":
        state = _train_explicit(train_df, algorithm, hyperparameters)
    elif spec.family == "content_based":
        assert item_features is not None
        assert item_id_column_features is not None
        assert item_text_column is not None
        state = _train_content_based(
            item_features, item_id_column_features, item_text_column, seen_items_by_user
        )
    else:
        state = {}

    recommendations = {
        user_id: _recommend_for_user(
            spec.family,
            state,
            user_id,
            k,
            seen_items_by_user.get(user_id, set()),
            popularity_fallback,
        )
        for user_id in ground_truth
    }
    metrics = compute_ranking_metrics(recommendations, ground_truth, k)
    test_user_count = test_df["user_id"].nunique()
    cold_user_count = test_df["user_id"].nunique() - warm_test_df["user_id"].nunique()
    metrics["cold_start_user_fraction"] = (
        cold_user_count / test_user_count if test_user_count else 0.0
    )

    model = RecModel(spec.family, state, popularity_fallback, seen_items_by_user)
    return model, metrics


def main() -> None:
    interactions_uri = os.environ["INTERACTIONS_URI"]
    item_features_uri = os.environ.get("ITEM_FEATURES_URI") or None
    user_id_column = os.environ["USER_ID_COLUMN"]
    item_id_column = os.environ["ITEM_ID_COLUMN"]
    timestamp_column = os.environ["TIMESTAMP_COLUMN"]
    rating_column = os.environ.get("RATING_COLUMN") or None
    item_id_column_features = os.environ.get("ITEM_ID_COLUMN_FEATURES") or None
    item_text_column = os.environ.get("ITEM_TEXT_COLUMN") or None
    algorithm = os.environ["ALGORITHM"]
    k = int(os.environ.get("K", "10"))
    hyperparameters = cast(
        dict[str, object], json.loads(os.environ.get("HYPERPARAMETERS_JSON") or "{}")
    )

    interactions_path = Path(interactions_uri.removeprefix("file://"))
    interactions = pd.read_csv(interactions_path)
    dataset_digest = _read_dataset_digest(interactions_path)

    item_features = None
    if item_features_uri is not None:
        item_features = pd.read_csv(Path(item_features_uri.removeprefix("file://")))

    mlflow.set_tracking_uri(
        os.environ.get("MLFLOW_TRACKING_URI", "http://host.docker.internal:5000")
    )

    with mlflow.start_run() as run:
        mlflow.set_tag("task_type", "ranking")
        mlflow.log_param("algorithm", algorithm)
        mlflow.log_param("k", k)
        mlflow.log_param("interactions_uri", interactions_uri)
        mlflow.log_param("dataset_digest", dataset_digest)
        if item_features_uri is not None:
            mlflow.log_param("item_features_uri", item_features_uri)

        model, metrics = train_and_evaluate(
            interactions,
            user_id_column,
            item_id_column,
            timestamp_column,
            algorithm,
            k,
            hyperparameters,
            rating_column=rating_column,
            item_features=item_features,
            item_id_column_features=item_id_column_features,
            item_text_column=item_text_column,
        )
        for metric_name, value in metrics.items():
            mlflow.log_metric(metric_name, value)
        mlflow_pyfunc.log_model(python_model=GenericPyfuncWrapper(model), artifact_path="model")
        artifact_uri = f"runs:/{run.info.run_id}/model"

    Path("/tmp/artifact-uri").write_text(artifact_uri)
    Path("/tmp/dataset-digest").write_text(dataset_digest)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — top-level: any failure must fail the Argo step, not hang.
        print(f"training failed: {exc}", file=sys.stderr)
        sys.exit(1)
