"""Metric computation dispatched by task type — each task type has a
different notion of "good" and needs different sklearn.metrics calls."""

from numpy.typing import ArrayLike
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    precision_score,
    r2_score,
    recall_score,
    silhouette_score,
)


def compute_metrics(task_type: str, y_true: ArrayLike, y_pred: ArrayLike) -> dict[str, float]:
    """Computes the metric set for one task type.

    Args:
        task_type: One of "classification", "regression", "clustering".
        y_true: Ground-truth labels/targets (classification/regression) or
            the feature matrix used to cluster (clustering — silhouette
            needs the points, not labels). Accepts ndarray/Series/DataFrame —
            callers pass whichever shape their task type produces.
        y_pred: Model predictions (classification/regression) or cluster
            assignments (clustering).

    Returns:
        Metric name -> value.

    Raises:
        ValueError: task_type isn't recognized.
    """
    if task_type == "classification":
        # weighted average handles multiclass/imbalance; zero_division stub type is wrong.
        precision = precision_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0,  # pyright: ignore[reportArgumentType]
        )
        recall = recall_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0,  # pyright: ignore[reportArgumentType]
        )
        f1 = f1_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0,  # pyright: ignore[reportArgumentType]
        )
        return {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    if task_type == "regression":
        # r2/MAPE are scale-free, usable as gate thresholds; MAE isn't (logged only).
        return {
            "r2": r2_score(y_true, y_pred),
            "mean_absolute_percentage_error": mean_absolute_percentage_error(y_true, y_pred),
            "mean_absolute_error": mean_absolute_error(y_true, y_pred),
        }
    if task_type == "clustering":
        # Bounded in [-1, 1] — scale-free, same reasoning as regression above.
        return {"silhouette_score": silhouette_score(y_true, y_pred)}
    raise ValueError(f"unknown task_type {task_type!r}")
