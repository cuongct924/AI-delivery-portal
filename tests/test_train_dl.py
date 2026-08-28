"""infra/argo-workflows/training-image/train_dl.py.

Patches the module-level `mlflow` name (train_dl.py's per-epoch
mlflow.log_metric calls) so these tests don't need a real MLflow tracking
server — same reasoning as tests/test_mlflow_adapter.py patching the real
mlflow SDK.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from dl_models import MLPModel
from optimizers import build_optimizer
from train_dl import build_sequences, train_and_evaluate


def test_build_sequences_shapes_and_alignment() -> None:
    features = np.arange(20).reshape(10, 2).astype("float64")
    labels = np.arange(10).astype("float64")

    x, y = build_sequences(features, labels, sequence_length=3)

    assert x.shape == (7, 3, 2)
    assert y.shape == (7,)
    # Window 0 covers rows 0-2, predicts the label at row 3 — never a label
    # that's inside the window itself (no leakage).
    assert np.array_equal(x[0], features[0:3])
    assert y[0] == labels[3]
    assert np.array_equal(x[-1], features[6:9])
    assert y[-1] == labels[9]


def test_build_sequences_rejects_sequence_length_too_long() -> None:
    features = np.zeros((5, 2))
    labels = np.zeros(5)
    with pytest.raises(ValueError, match="sequence_length"):
        build_sequences(features, labels, sequence_length=5)


def _regression_data(n: int = 60) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    rng = np.random.default_rng(0)
    features = pd.DataFrame({"f1": rng.normal(size=n), "f2": rng.normal(size=n)})
    labels = pd.Series(features["f1"] * 2 - features["f2"], name="target")
    split = int(n * 0.75)
    return features.iloc[:split], features.iloc[split:], labels.iloc[:split], labels.iloc[split:]


def _classification_data(n: int = 60) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    rng = np.random.default_rng(1)
    features = pd.DataFrame({"f1": rng.normal(size=n), "f2": rng.normal(size=n)})
    labels = pd.Series((features["f1"] + features["f2"] > 0).astype(int), name="target")
    split = int(n * 0.75)
    return features.iloc[:split], features.iloc[split:], labels.iloc[:split], labels.iloc[split:]


@patch("train_dl.mlflow")
def test_train_and_evaluate_mlp_regression(mock_mlflow: MagicMock) -> None:
    train_features, test_features, train_labels, test_labels = _regression_data()
    hyperparameters = {
        "hidden_layers": [8, 4],
        "dropout": 0.0,
        "learning_rate": 0.05,
        "epochs": 3,
        "batch_size": 16,
    }

    model, metrics = train_and_evaluate(
        train_features,
        test_features,
        train_labels,
        test_labels,
        "regression",
        "mlp",
        hyperparameters,
        "train",
        None,
    )

    assert isinstance(model, MLPModel)
    assert set(metrics) == {"r2", "mean_absolute_percentage_error", "mean_absolute_error"}
    assert mock_mlflow.log_metric.call_count == 3  # once per epoch


@patch("train_dl.mlflow")
def test_train_and_evaluate_mlp_classification(mock_mlflow: MagicMock) -> None:
    del mock_mlflow
    train_features, test_features, train_labels, test_labels = _classification_data()
    hyperparameters = {
        "hidden_layers": [8],
        "dropout": 0.0,
        "learning_rate": 0.05,
        "epochs": 2,
        "batch_size": 16,
    }

    _, metrics = train_and_evaluate(
        train_features,
        test_features,
        train_labels,
        test_labels,
        "classification",
        "mlp",
        hyperparameters,
        "train",
        None,
    )

    assert set(metrics) == {"accuracy", "precision", "recall", "f1"}


@patch("train_dl.mlflow")
def test_train_and_evaluate_lstm_windows_before_training(mock_mlflow: MagicMock) -> None:
    del mock_mlflow
    train_features, test_features, train_labels, test_labels = _regression_data()
    hyperparameters = {
        "sequence_length": 5,
        "num_layers": 1,
        "hidden_size": 8,
        "learning_rate": 0.05,
        "epochs": 2,
        "batch_size": 8,
    }

    model, metrics = train_and_evaluate(
        train_features,
        test_features,
        train_labels,
        test_labels,
        "regression",
        "lstm",
        hyperparameters,
        "train",
        None,
    )

    assert set(metrics) == {"r2", "mean_absolute_percentage_error", "mean_absolute_error"}


@patch("train_dl.mlflow")
def test_train_and_evaluate_defaults_to_adam_when_optimizer_unset(mock_mlflow: MagicMock) -> None:
    del mock_mlflow
    train_features, test_features, train_labels, test_labels = _regression_data()
    hyperparameters = {
        "hidden_layers": [4],
        "dropout": 0.0,
        "learning_rate": 0.05,
        "epochs": 1,
        "batch_size": 16,
    }

    with patch("train_dl.build_optimizer", wraps=build_optimizer) as mock_build:
        train_and_evaluate(
            train_features,
            test_features,
            train_labels,
            test_labels,
            "regression",
            "mlp",
            hyperparameters,
            "train",
            None,
        )

    assert mock_build.call_args.args[0] == "adam"


@patch("train_dl.mlflow")
def test_train_and_evaluate_uses_sgd_when_requested(mock_mlflow: MagicMock) -> None:
    del mock_mlflow
    train_features, test_features, train_labels, test_labels = _classification_data()
    hyperparameters = {
        "hidden_layers": [4],
        "dropout": 0.0,
        "learning_rate": 0.05,
        "epochs": 1,
        "batch_size": 16,
        "optimizer": "sgd",
    }

    with patch("train_dl.build_optimizer", wraps=build_optimizer) as mock_build:
        model, _ = train_and_evaluate(
            train_features,
            test_features,
            train_labels,
            test_labels,
            "classification",
            "mlp",
            hyperparameters,
            "train",
            None,
        )

    assert mock_build.call_args.args[0] == "sgd"
    assert isinstance(model, MLPModel)


def test_train_and_evaluate_rejects_unknown_optimizer() -> None:
    train_features, test_features, train_labels, test_labels = _classification_data()
    hyperparameters = {
        "hidden_layers": [4],
        "dropout": 0.0,
        "learning_rate": 0.05,
        "epochs": 1,
        "batch_size": 16,
        "optimizer": "rmsprop",
    }

    with (
        patch("train_dl.mlflow"),
        pytest.raises(ValueError, match="unknown optimizer"),
    ):
        train_and_evaluate(
            train_features,
            test_features,
            train_labels,
            test_labels,
            "classification",
            "mlp",
            hyperparameters,
            "train",
            None,
        )


@patch("train_dl.mlflow_pytorch")
@patch("train_dl.mlflow")
def test_train_and_evaluate_finetune_loads_base_model(
    mock_mlflow: MagicMock, mock_mlflow_pytorch: MagicMock
) -> None:
    del mock_mlflow
    train_features, test_features, train_labels, test_labels = _regression_data()
    base_model = MLPModel(input_size=2, hidden_layers=[8, 4], dropout=0.0, output_size=1)
    mock_mlflow_pytorch.load_model.return_value = base_model
    hyperparameters = {"learning_rate": 0.01, "epochs": 1, "batch_size": 16}

    model, _ = train_and_evaluate(
        train_features,
        test_features,
        train_labels,
        test_labels,
        "regression",
        "mlp",
        hyperparameters,
        "finetune",
        "models:/some-model/1",
    )

    mock_mlflow_pytorch.load_model.assert_called_once_with("models:/some-model/1")
    assert model is base_model


@patch("train_dl.mlflow")
def test_train_and_evaluate_finetune_without_base_model_uri_raises(mock_mlflow: MagicMock) -> None:
    del mock_mlflow
    train_features, test_features, train_labels, test_labels = _regression_data()
    hyperparameters = {"learning_rate": 0.01, "epochs": 1, "batch_size": 16}

    with pytest.raises(RuntimeError, match="MODE=finetune requires BASE_MODEL_URI"):
        train_and_evaluate(
            train_features,
            test_features,
            train_labels,
            test_labels,
            "regression",
            "mlp",
            hyperparameters,
            "finetune",
            None,
        )
