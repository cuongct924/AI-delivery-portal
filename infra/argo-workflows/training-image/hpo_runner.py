"""Runs a Hyperparameter Search Strategy (hpo_strategies.py) as a plain
Python loop inside the training-image pod — no Ray Tune/Katib, deliberately
avoiding new infra. Each trial: sample → train_dl.py's train_and_evaluate()
→ log as a nested MLflow child run → feed the result back to the strategy.
After all trials, the best one's model/metrics/hyperparameters are handed
back to `train.py` to log at the parent-run level and register — the
register→gate→deploy flow downstream never changes.
"""

from typing import Any

import mlflow
import pandas as pd
from hpo_strategies import IHyperparameterSearchStrategy, SearchSpace
from train_dl import train_and_evaluate as train_dl_and_evaluate


def build_search_spaces(
    search_space_config: dict[str, dict[str, Any]], base_hyperparameters: dict[str, object]
) -> list[SearchSpace]:
    """Converts the Dev's `SEARCH_SPACE_JSON` (1 JSON field instead of a
    per-hyperparameter range/set field pair) into `SearchSpace` objects.

    Any DL hyperparameter not present in `search_space_config` stays fixed
    at its single value from `base_hyperparameters` — Dev can search a
    subset and fix the rest.

    Args:
        search_space_config: `{param_name: {"choices": [...]} |
            {"low": ..., "high": ...}}`.
        base_hyperparameters: The already-parsed fixed hyperparameter dict
            (`train.py::_read_dl_hyperparameters()`) — used only to infer
            int vs. float for range-shaped spaces.

    Returns:
        One `SearchSpace` per key in `search_space_config`.

    Raises:
        ValueError: an entry has neither `choices` nor both `low`/`high`.
    """
    spaces: list[SearchSpace] = []
    for param_name, spec in search_space_config.items():
        if "choices" in spec:
            spaces.append(SearchSpace(param_name=param_name, choices=spec["choices"]))
            continue
        if "low" not in spec or "high" not in spec:
            raise ValueError(
                f"search space for {param_name!r} needs either 'choices' or both 'low'/'high' "
                f"— got {spec!r}"
            )
        is_int = isinstance(base_hyperparameters.get(param_name), int)
        spaces.append(
            SearchSpace(param_name=param_name, low=spec["low"], high=spec["high"], is_int=is_int)
        )
    return spaces


def run_hpo(
    strategy: IHyperparameterSearchStrategy,
    base_hyperparameters: dict[str, object],
    spaces: list[SearchSpace],
    num_trials: int,
    train_features: pd.DataFrame,
    test_features: pd.DataFrame,
    train_labels: pd.Series,
    test_labels: pd.Series,
    task_type: str,
    architecture: str,
    mode: str,
    base_model_uri: str | None,
    objective_metric: str,
    objective_direction: str,
) -> tuple[Any, dict[str, float], dict[str, object]]:
    """Runs every trial the strategy produces and returns the best one.

    Returns:
        (model, metrics, hyperparameters) of the best trial by
        `objective_metric`, compared per `objective_direction`
        ("maximize" or "minimize").

    Raises:
        ValueError: `objective_direction` isn't "maximize"/"minimize", or
            no trial ran (empty search space with a 0-trial strategy).
    """
    if objective_direction not in ("maximize", "minimize"):
        raise ValueError(
            f"objective_direction must be 'maximize' or 'minimize', got {objective_direction!r}"
        )

    best_model: Any = None
    best_metrics: dict[str, float] | None = None
    best_hyperparameters: dict[str, object] | None = None
    best_value: float | None = None

    trial_count = strategy.trial_count(num_trials, spaces)
    for trial_number in range(trial_count):
        sampled = strategy.suggest_trial(trial_number, spaces)
        hyperparameters = {**base_hyperparameters, **sampled}
        with mlflow.start_run(nested=True):
            mlflow.log_params(hyperparameters)
            model, metrics = train_dl_and_evaluate(
                train_features,
                test_features,
                train_labels,
                test_labels,
                task_type,
                architecture,
                hyperparameters,
                mode,
                base_model_uri,
            )
            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value)

        objective_value = metrics[objective_metric]
        strategy.report_result(trial_number, objective_value)

        is_better = best_value is None or (
            objective_value > best_value
            if objective_direction == "maximize"
            else objective_value < best_value
        )
        if is_better:
            best_model, best_metrics, best_hyperparameters, best_value = (
                model,
                metrics,
                hyperparameters,
                objective_value,
            )

    if best_model is None or best_metrics is None or best_hyperparameters is None:
        raise ValueError("no trial ran — check numTrials and the search space")
    return best_model, best_metrics, best_hyperparameters
