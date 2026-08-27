"""infra/argo-workflows/training-image/dl_architecture_registry.py."""

import pytest
from dl_architecture_registry import DL_ARCHITECTURES, get_dl_architecture
from dl_models import LSTMModel, MLPModel


def test_mlp_does_not_require_time_column() -> None:
    assert DL_ARCHITECTURES["mlp"].requires_time_column is False
    assert DL_ARCHITECTURES["mlp"].model_class is MLPModel


def test_lstm_requires_time_column() -> None:
    assert DL_ARCHITECTURES["lstm"].requires_time_column is True
    assert DL_ARCHITECTURES["lstm"].model_class is LSTMModel


def test_get_dl_architecture_returns_matching_entry() -> None:
    spec = get_dl_architecture("mlp")
    assert spec is DL_ARCHITECTURES["mlp"]


def test_get_dl_architecture_rejects_unknown_architecture() -> None:
    with pytest.raises(ValueError, match="unknown architecture"):
        get_dl_architecture("transformer")
