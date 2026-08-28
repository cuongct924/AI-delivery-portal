"""Registry of which checks run for which task type — same registry-by-
dimension pattern as TASK_TYPE_ALGORITHMS (training image) and
TASK_TYPE_THRESHOLDS (evaluations/gate.py): universal checks every dataset
gets, plus a task-type-specific list, plus an optional time-column check
that's an independent axis (same convention as `timeColumn` for algorithms)."""

from collections.abc import Callable
from typing import Final

import pandas as pd

from data_quality.checks import (
    CheckResult,
    check_class_imbalance,
    check_dimensionality_vs_samples,
    check_duplicate_rows,
    check_high_cardinality,
    check_missing_values,
    check_rec_cold_start_ratio,
    check_rec_duplicate_interactions,
    check_rec_ids_present,
    check_target_leakage_correlation,
    check_time_gaps,
)

UNIVERSAL_CHECKS: Final[list[Callable[..., CheckResult]]] = [
    check_missing_values,
    check_duplicate_rows,
]

# nlp/cv/recsys entries land here when those phases add their own checks
# (mục 6f.2) — same dict, no new mechanism.
TASK_TYPE_CHECKS: Final[dict[str, list[Callable[..., CheckResult]]]] = {
    "classification": [
        check_target_leakage_correlation,
        check_class_imbalance,
        check_high_cardinality,
    ],
    "regression": [check_target_leakage_correlation, check_high_cardinality],
    "clustering": [check_dimensionality_vs_samples],
}


def run_checks(
    df: pd.DataFrame,
    task_type: str,
    target_column: str | None = None,
    time_column: str | None = None,
) -> list[CheckResult]:
    """Runs every applicable check for a dataset + task type.

    Every check function accepts the same (df, target_column=...) shape —
    ones that don't need target_column just ignore it — so this loop stays
    a plain "add a check, add a line to the registry" without per-function
    special-casing.

    Args:
        df: The dataset to validate.
        task_type: One of the keys in TASK_TYPE_CHECKS.
        target_column: Passed to every check — ignored by checks that don't
            need it, and by task-type-specific checks that do (leakage/
            imbalance) when it's None (e.g. clustering has no target).
        time_column: When set, also runs check_time_gaps — independent of
            task_type, same convention as TIME_COLUMN in the training image.

    Returns:
        One CheckResult per check that ran.
    """
    checks = UNIVERSAL_CHECKS + TASK_TYPE_CHECKS.get(task_type, [])
    results = [check(df, target_column=target_column) for check in checks]
    if time_column is not None:
        results.append(check_time_gaps(df, time_column))
    return results


def run_rec_checks(
    interactions: pd.DataFrame, user_id_column: str, item_id_column: str
) -> list[CheckResult]:
    """RecSys's own entry point (mục 6e.2/6f.5) — doesn't fit `run_checks()`'s
    shared `(df, target_column=...)` shape (2 required id columns, no
    single target), so it isn't in TASK_TYPE_CHECKS."""
    return [
        check_rec_ids_present(interactions, user_id_column, item_id_column),
        check_rec_duplicate_interactions(interactions, user_id_column, item_id_column),
        check_rec_cold_start_ratio(interactions, user_id_column, item_id_column),
    ]
