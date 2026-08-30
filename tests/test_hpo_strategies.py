"""infra/argo-workflows/training-image/hpo_strategies.py — Grid/Random/
Bayesian search strategies, exercised with real (lightweight) Optuna
studies, no MLflow/training involved."""

import pytest
from hpo_strategies import (
    BayesianSearchStrategy,
    FixedStrategy,
    GridSearchStrategy,
    RandomSearchStrategy,
    SearchSpace,
    build_search_strategy,
)


def test_fixed_strategy_always_returns_one_trial() -> None:
    strategy = FixedStrategy()
    spaces = [SearchSpace(param_name="epochs", choices=[10])]

    assert strategy.trial_count(requested_trials=99, spaces=spaces) == 1
    assert strategy.suggest_trial(0, spaces) == {"epochs": 10}


def test_grid_strategy_covers_full_cartesian_product() -> None:
    strategy = GridSearchStrategy()
    spaces = [
        SearchSpace(param_name="batch_size", choices=[16, 32]),
        SearchSpace(param_name="epochs", choices=[5, 10, 15]),
    ]

    trial_count = strategy.trial_count(requested_trials=1, spaces=spaces)

    assert trial_count == 6  # 2 * 3, ignores requested_trials
    combos = {tuple(strategy.suggest_trial(i, spaces).items()) for i in range(trial_count)}
    assert combos == {
        (("batch_size", 16), ("epochs", 5)),
        (("batch_size", 16), ("epochs", 10)),
        (("batch_size", 16), ("epochs", 15)),
        (("batch_size", 32), ("epochs", 5)),
        (("batch_size", 32), ("epochs", 10)),
        (("batch_size", 32), ("epochs", 15)),
    }


def test_grid_strategy_rejects_range_spaces() -> None:
    strategy = GridSearchStrategy()
    spaces = [SearchSpace(param_name="learning_rate", low=0.001, high=0.1)]

    with pytest.raises(ValueError, match="requires discrete choices"):
        strategy.trial_count(requested_trials=1, spaces=spaces)


def test_random_strategy_samples_within_bounds_and_honors_requested_trials() -> None:
    strategy = RandomSearchStrategy(direction="maximize", seed=1)
    spaces = [
        SearchSpace(param_name="learning_rate", low=0.001, high=0.1, is_int=False),
        SearchSpace(param_name="epochs", low=5, high=20, is_int=True),
        SearchSpace(param_name="batch_size", choices=[16, 32, 64]),
    ]

    assert strategy.trial_count(requested_trials=7, spaces=spaces) == 7
    sampled = strategy.suggest_trial(0, spaces)

    assert 0.001 <= sampled["learning_rate"] <= 0.1
    assert isinstance(sampled["epochs"], int)
    assert 5 <= sampled["epochs"] <= 20
    assert sampled["batch_size"] in (16, 32, 64)


def test_random_strategy_report_result_consumes_the_pending_trial() -> None:
    strategy = RandomSearchStrategy(direction="minimize", seed=2)
    spaces = [SearchSpace(param_name="dropout", low=0.0, high=0.5)]

    strategy.suggest_trial(0, spaces)
    strategy.report_result(0, 0.42)

    # No pending trial left for id 0 — reporting again must fail loudly,
    # not silently succeed against stale/reused state.
    with pytest.raises(KeyError):
        strategy.report_result(0, 0.1)


def test_bayesian_strategy_samples_within_bounds() -> None:
    strategy = BayesianSearchStrategy(direction="maximize")
    spaces = [SearchSpace(param_name="hidden_size", low=8, high=64, is_int=True)]

    for trial_number in range(3):
        sampled = strategy.suggest_trial(trial_number, spaces)
        assert 8 <= sampled["hidden_size"] <= 64
        strategy.report_result(trial_number, float(sampled["hidden_size"]))


@pytest.mark.parametrize(
    ("name", "expected_type"),
    [
        ("fixed", FixedStrategy),
        ("grid", GridSearchStrategy),
        ("random", RandomSearchStrategy),
        ("bayesian", BayesianSearchStrategy),
    ],
)
def test_build_search_strategy_returns_the_matching_type(name: str, expected_type: type) -> None:
    assert isinstance(build_search_strategy(name, "maximize"), expected_type)


def test_build_search_strategy_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown search strategy"):
        build_search_strategy("evolutionary", "maximize")
