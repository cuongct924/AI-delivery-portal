"""Golden Path #1 training entrypoint — reads job config from env vars (set
by the `train-step` container in infra/argo-workflows/train-register-template.yaml),
trains (or fine-tunes) the selected algorithm, logs everything to MLflow,
and hands the resulting artifact URI + dataset digest to `register-step` via
/tmp files (Argo reads them back through `outputs.parameters`).
"""

import os
import re
import sys
from pathlib import Path
from typing import Any, cast

import mlflow
import numpy as np
import pandas as pd
from algorithm_registry import AlgorithmSpec, get_algorithm_spec
from metrics import compute_metrics

# Submodule imports, not `import mlflow` + `mlflow.sklearn.x` — mlflow's
# top-level stub doesn't declare `sklearn`/`data` as exported attributes.
from mlflow import data as mlflow_data
from mlflow import sklearn as mlflow_sklearn
from sklearn.impute import SimpleImputer
from sklearn.model_selection import TimeSeriesSplit, train_test_split
from sklearn.preprocessing import StandardScaler

# Below this row count, a single random holdout is too noisy to trust —
# k-fold cross-validation averages over multiple splits instead.
_SMALL_DATASET_THRESHOLD = 50
_HOLDOUT_TEST_SIZE = 0.3
_KFOLD_SPLITS = 5
_TIME_SERIES_SPLITS = 5


def _read_dataset_digest(csv_path: Path) -> str:
    """Reads the DVC md5 hash — the dataset-lineage convention documented
    in data/README.md."""
    dvc_path = csv_path.with_name(csv_path.name + ".dvc")
    dvc_text = dvc_path.read_text()
    md5_match = re.search(r"md5:\s*(\S+)", dvc_text)
    if md5_match is None:
        raise RuntimeError(f"no md5 hash found in {dvc_path}")
    return md5_match.group(1)


def _encode_categoricals(features: pd.DataFrame) -> pd.DataFrame:
    """Ordinal-encodes every object-dtype column so any registry algorithm
    (none of which parse strings) gets purely numeric input. NaN is kept as
    NaN (not the -1 sentinel `.cat.codes` would otherwise assign) so missing
    value handling downstream applies uniformly to encoded and
    already-numeric columns alike."""
    encoded = features.copy()
    for column in encoded.select_dtypes(include="object").columns:
        codes = encoded[column].astype("category").cat.codes.astype("float64")
        encoded[column] = codes.replace(-1.0, np.nan)
    return encoded


def _handle_missing_values(
    train_features: pd.DataFrame, test_features: pd.DataFrame, spec: AlgorithmSpec
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Imputes with the train split's median unless the algorithm handles
    NaN natively (XGBoost/LightGBM/CatBoost — where missingness itself can
    be predictive, so imputing it away would destroy signal)."""
    if spec.handles_missing_natively:
        return train_features, test_features
    imputer = SimpleImputer(strategy="median")
    train_imputed = pd.DataFrame(
        imputer.fit_transform(train_features),
        columns=train_features.columns,
        index=train_features.index,
    )
    test_imputed = pd.DataFrame(
        imputer.transform(test_features), columns=test_features.columns, index=test_features.index
    )
    return train_imputed, test_imputed


def _scale_features(
    train_features: pd.DataFrame, test_features: pd.DataFrame, spec: AlgorithmSpec
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Standard-scales distance-/gradient-based estimators; leaves
    tree-based ones alone (they split on raw values, scaling is a no-op at
    best)."""
    if not spec.requires_scaling:
        return train_features, test_features
    scaler = StandardScaler()
    train_scaled = pd.DataFrame(
        scaler.fit_transform(train_features),
        columns=train_features.columns,
        index=train_features.index,
    )
    test_scaled = pd.DataFrame(
        scaler.transform(test_features), columns=test_features.columns, index=test_features.index
    )
    return train_scaled, test_scaled


def _split(
    df: pd.DataFrame,
    features: pd.DataFrame,
    labels: pd.Series,
    task_type: str,
    time_column: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Picks the validation strategy automatically — Dev never chooses this
    (mục 2, "cơ chế ML thuần kỹ thuật" bucket).

    A `time_column` always wins and never shuffles — random holdout/k-fold
    would let future rows leak into training and inflate metrics
    regardless of dataset size. Otherwise: k-fold (via cross-validation
    indices) for small datasets, plain holdout otherwise.
    """
    if time_column is not None:
        order = df[time_column].argsort()
        features = features.iloc[order]
        labels = labels.iloc[order]
        splitter = TimeSeriesSplit(n_splits=min(_TIME_SERIES_SPLITS, len(df) - 1))
        train_idx, test_idx = list(splitter.split(features))[-1]
        return (
            features.iloc[train_idx],
            features.iloc[test_idx],
            labels.iloc[train_idx],
            labels.iloc[test_idx],
        )
    if len(df) < _SMALL_DATASET_THRESHOLD:
        splitter = TimeSeriesSplit(n_splits=min(_KFOLD_SPLITS, len(df) - 1))
        # Not time-ordered here — TimeSeriesSplit is reused purely as a
        # convenient "last N% held out" k-fold-style splitter, matching the
        # "k-fold for small datasets" strategy without a shuffle argument to
        # worry about aligning with a stratify option.
        train_idx, test_idx = list(splitter.split(features))[-1]
        return (
            features.iloc[train_idx],
            features.iloc[test_idx],
            labels.iloc[train_idx],
            labels.iloc[test_idx],
        )
    stratify = labels if task_type == "classification" else None
    # train_test_split's stub returns a generic `list` (arg count is
    # variadic) — 2 arrays in always means this exact 4-tuple shape out.
    return cast(
        tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series],
        train_test_split(
            features, labels, test_size=_HOLDOUT_TEST_SIZE, random_state=42, stratify=stratify
        ),
    )


def _fit(
    spec: AlgorithmSpec,
    mode: str,
    base_model_uri: str | None,
    train_features: pd.DataFrame,
    train_labels: pd.Series,
) -> Any:  # see AlgorithmSpec.estimator_class — no shared typed base class across libraries
    if mode == "train":
        model = spec.estimator_class()
        model.fit(train_features, train_labels)
        return model
    if mode == "finetune":
        if base_model_uri is None:
            raise RuntimeError("MODE=finetune requires BASE_MODEL_URI")
        # mlflow.sklearn's stub types load_model()'s return as None — wrong,
        # it returns the loaded estimator.
        model = cast(Any, mlflow_sklearn.load_model(base_model_uri))
        if not hasattr(model, "warm_start"):
            raise RuntimeError(
                f"{type(model).__name__} does not support warm_start — cannot fine-tune. "
                "Use MODE=train to train a new model instead."
            )
        model.set_params(warm_start=True)
        model.fit(train_features, train_labels)
        return model
    raise RuntimeError(f"unknown MODE {mode!r} — must be 'train' or 'finetune'")


def main() -> None:
    dataset_uri = os.environ["DATASET_URI"]
    task_type = os.environ["TASK_TYPE"]
    target_column = os.environ.get("TARGET_COLUMN") or None
    id_columns = [c for c in os.environ.get("ID_COLUMNS", "").split(",") if c]
    algorithm = os.environ["ALGORITHM"]
    mode = os.environ.get("MODE", "train")
    base_model_uri = os.environ.get("BASE_MODEL_URI") or None
    time_column = os.environ.get("TIME_COLUMN") or None

    if task_type != "clustering" and target_column is None:
        raise RuntimeError(f"TARGET_COLUMN is required for task_type {task_type!r}")

    # Strip the "file://" scheme to get a real filesystem path pandas can open.
    csv_path = Path(dataset_uri.removeprefix("file://"))
    df = pd.read_csv(csv_path)
    dataset_digest = _read_dataset_digest(csv_path)

    spec = get_algorithm_spec(task_type, algorithm)

    drop_columns = list(id_columns)
    if target_column is not None:
        drop_columns.append(target_column)
    features = _encode_categoricals(df.drop(columns=drop_columns))

    mlflow.set_tracking_uri(
        os.environ.get("MLFLOW_TRACKING_URI", "http://host.docker.internal:5000")
    )

    if task_type == "clustering":
        # DBSCAN/AgglomerativeClustering are transductive (no .predict on
        # new data) — clustering always fits+predicts on the full dataset,
        # no train/test split (mục 3.1).
        if mode != "train":
            raise RuntimeError("clustering does not support MODE=finetune")
        train_features, _ = _handle_missing_values(features, features, spec)
        train_features, _ = _scale_features(train_features, train_features, spec)
        model = spec.estimator_class()
        labels = model.fit_predict(train_features)
        metrics = compute_metrics(task_type, train_features, labels)
    else:
        # Validated non-None above (task_type != "clustering" requires it) —
        # asserted again here so the type checker can narrow it too.
        assert target_column is not None
        labels_full = cast(pd.Series, df[target_column])
        train_features, test_features, train_labels, test_labels = _split(
            df, features, labels_full, task_type, time_column
        )
        train_features, test_features = _handle_missing_values(train_features, test_features, spec)
        train_features, test_features = _scale_features(train_features, test_features, spec)
        model = _fit(spec, mode, base_model_uri, train_features, train_labels)
        predictions = model.predict(test_features)
        metrics = compute_metrics(task_type, test_labels, predictions)

    with mlflow.start_run() as run:
        mlflow.set_tag("task_type", task_type)
        mlflow.log_param("algorithm", algorithm)
        mlflow.log_param("mode", mode)
        for metric_name, value in metrics.items():
            mlflow.log_metric(metric_name, value)

        # mlflow.data's stub doesn't declare from_pandas even though it's a
        # real, documented function.
        dataset = mlflow_data.from_pandas(  # pyright: ignore[reportAttributeAccessIssue]
            df, source=dataset_uri, digest=dataset_digest
        )
        mlflow.log_input(dataset, context="training")

        mlflow_sklearn.log_model(model, artifact_path="model")
        artifact_uri = f"runs:/{run.info.run_id}/model"

    # Argo reads these back via outputs.parameters to hand off to register-step.
    Path("/tmp/artifact-uri").write_text(artifact_uri)
    Path("/tmp/dataset-digest").write_text(dataset_digest)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — top-level: any failure must fail the Argo step, not hang.
        print(f"training failed: {exc}", file=sys.stderr)
        sys.exit(1)
