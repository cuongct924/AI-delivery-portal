"""infra/argo-workflows/training-image/hpo_runner.py — build_search_spaces()
and run_hpo()'s trial loop / best-trial selection, with a fake strategy and
a mocked train_dl_and_evaluate/mlflow so no real training or MLflow server
is involved."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from hpo_runner import build_search_spaces, run_hpo
from hpo_strategies import SearchSpace


def test_build_search_spaces_choices() -> None:
    spaces = build_search_spaces({"batch_size": {"choices": [16, 32]}}, base_hyperparameters={})

    assert spaces == [SearchSpace(param_name="batch_size", choices=[16, 32])]


def test_build_search_spaces_range_infers_int_from_base_hyperparameters() -> None:
    spaces = build_search_spaces(
        {"epochs": {"low": 5, "high": 20}},
        base_hyperparameters={"epochs": 10},
    )

    assert spaces == [SearchSpace(param_name="epochs", low=5, high=20, is_int=True)]


def test_build_search_spaces_range_without_int_base_defaults_to_float() -> None:
    spaces = build_search_spaces(
        {"learning_rate": {"low": 0.001, "high": 0.1}},
        base_hyperparameters={"learning_rate": 0.01},
    )

    assert spaces == [SearchSpace(param_name="learning_rate", low=0.001, high=0.1, is_int=False)]


def test_build_search_spaces_rejects_missing_bounds() -> None:
    with pytest.raises(ValueError, match="needs either 'choices' or both 'low'/'high'"):
        build_search_spaces({"dropout": {"low": 0.1}}, base_hyperparameters={})


class _FakeStrategy:
    """Deterministic stand-in — trial N samples batch_size=(N+1)*16."""

    def __init__(self) -> None:
        self.reported: list[tuple[int, float]] = []

    def trial_count(self, requested_trials: int, spaces: list[SearchSpace]) -> int:
        return requested_trials

    def suggest_trial(self, trial_number: int, spaces: list[SearchSpace]) -> dict[str, object]:
        return {"batch_size": (trial_number + 1) * 16}

    def report_result(self, trial_number: int, value: float) -> None:
        self.reported.append((trial_number, value))


@patch("hpo_runner.mlflow")
@patch("hpo_runner.train_dl_and_evaluate")
def test_run_hpo_picks_the_best_trial_when_maximizing(
    mock_train_dl: MagicMock, mock_mlflow: MagicMock
) -> None:
    # 3 trials, accuracy increases with trial number — trial 2 (batch_size=48) wins.
    mock_train_dl.side_effect = [
        (MagicMock(name="model-0"), {"accuracy": 0.5}),
        (MagicMock(name="model-1"), {"accuracy": 0.9}),
        (MagicMock(name="model-2"), {"accuracy": 0.7}),
    ]
    strategy = _FakeStrategy()

    model, metrics, hyperparameters = run_hpo(
        strategy,
        base_hyperparameters={"learning_rate": 0.01},
        spaces=[],
        num_trials=3,
        train_features=pd.DataFrame(),
        test_features=pd.DataFrame(),
        train_labels=pd.Series(dtype="float64"),
        test_labels=pd.Series(dtype="float64"),
        task_type="classification",
        architecture="mlp",
        mode="train",
        base_model_uri=None,
        objective_metric="accuracy",
        objective_direction="maximize",
    )

    assert metrics == {"accuracy": 0.9}
    assert hyperparameters == {"learning_rate": 0.01, "batch_size": 32}
    assert strategy.reported == [(0, 0.5), (1, 0.9), (2, 0.7)]
    assert mock_mlflow.start_run.call_count == 3
    assert mock_mlflow.log_params.call_count == 3


@patch("hpo_runner.mlflow")
@patch("hpo_runner.train_dl_and_evaluate")
def test_run_hpo_picks_the_best_trial_when_minimizing(
    mock_train_dl: MagicMock, mock_mlflow: MagicMock
) -> None:
    mock_train_dl.side_effect = [
        (MagicMock(), {"mean_absolute_error": 5.0}),
        (MagicMock(), {"mean_absolute_error": 1.5}),
    ]
    strategy = _FakeStrategy()

    _, metrics, _ = run_hpo(
        strategy,
        base_hyperparameters={},
        spaces=[],
        num_trials=2,
        train_features=pd.DataFrame(),
        test_features=pd.DataFrame(),
        train_labels=pd.Series(dtype="float64"),
        test_labels=pd.Series(dtype="float64"),
        task_type="regression",
        architecture="lstm",
        mode="train",
        base_model_uri=None,
        objective_metric="mean_absolute_error",
        objective_direction="minimize",
    )

    assert metrics == {"mean_absolute_error": 1.5}


@patch("hpo_runner.mlflow")
@patch("hpo_runner.train_dl_and_evaluate")
def test_run_hpo_rejects_invalid_direction(
    mock_train_dl: MagicMock, mock_mlflow: MagicMock
) -> None:
    with pytest.raises(ValueError, match="objective_direction must be"):
        run_hpo(
            _FakeStrategy(),
            base_hyperparameters={},
            spaces=[],
            num_trials=1,
            train_features=pd.DataFrame(),
            test_features=pd.DataFrame(),
            train_labels=pd.Series(dtype="float64"),
            test_labels=pd.Series(dtype="float64"),
            task_type="classification",
            architecture="mlp",
            mode="train",
            base_model_uri=None,
            objective_metric="accuracy",
            objective_direction="sideways",
        )
    mock_train_dl.assert_not_called()
