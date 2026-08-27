"""Tests adapters/deploy_strategies.py."""

from unittest.mock import MagicMock

from adapters.deploy_strategies import (
    DirectStrategy,
    InstantStrategy,
    PRGatedStrategy,
    TrafficSplitStrategy,
)


def test_direct_strategy_renders_no_extra_fields() -> None:
    assert DirectStrategy().render() == {}


def test_traffic_split_strategy_renders_canary_traffic_percent() -> None:
    assert TrafficSplitStrategy(percent=25).render() == {"canaryTrafficPercent": 25}


def test_pr_gated_strategy_is_a_no_op() -> None:
    result = PRGatedStrategy().release("fraud-detection", "3", "manifest: yaml")
    assert result == {"deployed": False}


def test_instant_strategy_deploys_via_the_inference_adapter() -> None:
    mock_adapter = MagicMock()
    strategy = InstantStrategy(mock_adapter, traffic_fields={"canaryTrafficPercent": 50})

    result = strategy.release("fraud-detection", "3", "manifest: yaml")

    mock_adapter.deploy_model.assert_called_once_with(
        "fraud-detection",
        "3",
        "models:/fraud-detection/3",
        traffic_fields={"canaryTrafficPercent": 50},
    )
    assert result == {"deployed": True}


def test_instant_strategy_defaults_to_empty_traffic_fields() -> None:
    mock_adapter = MagicMock()
    strategy = InstantStrategy(mock_adapter)

    strategy.release("fraud-detection", "1", "manifest: yaml")

    mock_adapter.deploy_model.assert_called_once_with(
        "fraud-detection", "1", "models:/fraud-detection/1", traffic_fields={}
    )
