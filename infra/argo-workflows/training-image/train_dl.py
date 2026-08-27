"""Deep Learning training loop (MLP/LSTM) — dispatched from train.py when
ARCHITECTURE is not "sklearn". Kept in a separate file per mục 5.2: the
epoch/batch/backprop training loop shape is fundamentally different from
sklearn's single `.fit()` call, not worth cramming into train.py.
"""

from typing import Any, cast

import mlflow
import numpy as np
import pandas as pd
import torch
from dl_architecture_registry import get_dl_architecture
from metrics import compute_metrics

# mlflow.pytorch's stub has the same gaps as mlflow.sklearn/mlflow.data
# (see train.py) — submodule import instead of attribute access.
from mlflow import pytorch as mlflow_pytorch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


def build_sequences(
    features: np.ndarray, labels: np.ndarray, sequence_length: int
) -> tuple[np.ndarray, np.ndarray]:
    """Sliding-window sequences for LSTM — window i predicts the label
    for the row right after that window, never a label inside it."""
    num_windows = len(features) - sequence_length
    if num_windows <= 0:
        raise ValueError(
            f"sequence_length ({sequence_length}) must be shorter than the "
            f"split's row count ({len(features)})"
        )
    x = np.stack([features[i : i + sequence_length] for i in range(num_windows)])
    y = np.stack([labels[i + sequence_length] for i in range(num_windows)])
    return x, y


def _normalize(
    train: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Neural nets always need scaled input — no per-architecture
    requires_scaling flag like AlgorithmSpec, this is unconditional."""
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std[std == 0] = 1.0  # a constant column would otherwise divide by zero
    return (train - mean) / std, (test - mean) / std, mean, std


def train_and_evaluate(
    train_features: pd.DataFrame,
    test_features: pd.DataFrame,
    train_labels: pd.Series,
    test_labels: pd.Series,
    task_type: str,
    architecture: str,
    hyperparameters: dict[str, Any],
    mode: str,
    base_model_uri: str | None,
) -> tuple[nn.Module, dict[str, float]]:
    """Trains (or fine-tunes) an MLP/LSTM and returns it with its test metrics.

    Logs one `loss` metric per epoch to the currently active MLflow run
    (opened by the caller, train.py's main()) — reuses MLflow's own UI for
    live experiment tracking instead of building a new dashboard, same
    approach already used for HPO (mục 6c.3).
    """
    spec = get_dl_architecture(architecture)
    epochs = int(hyperparameters["epochs"])
    batch_size = int(hyperparameters["batch_size"])
    learning_rate = float(hyperparameters["learning_rate"])

    train_x_raw = train_features.to_numpy(dtype="float64")
    test_x_raw = test_features.to_numpy(dtype="float64")
    train_x_raw, test_x_raw, _, _ = _normalize(train_x_raw, test_x_raw)

    is_regression = task_type == "regression"
    target_mean, target_std = 0.0, 1.0
    if is_regression:
        # Standardizing the target too — otherwise MSELoss's gradient scale
        # depends on the target's raw units, and predictions must be
        # un-scaled before compute_metrics() (R2/MAPE need the real scale).
        target_mean = float(train_labels.mean())
        target_std = float(train_labels.std()) or 1.0
        train_y_raw = ((train_labels - target_mean) / target_std).to_numpy(dtype="float64")
        test_y_raw = ((test_labels - target_mean) / target_std).to_numpy(dtype="float64")
    else:
        train_y_raw = train_labels.to_numpy(dtype="int64")
        test_y_raw = test_labels.to_numpy(dtype="int64")

    if spec.requires_time_column:
        sequence_length = int(hyperparameters["sequence_length"])
        train_x_raw, train_y_raw = build_sequences(train_x_raw, train_y_raw, sequence_length)
        test_x_raw, test_y_raw = build_sequences(test_x_raw, test_y_raw, sequence_length)

    train_x = torch.tensor(train_x_raw, dtype=torch.float32)
    test_x = torch.tensor(test_x_raw, dtype=torch.float32)
    train_y = torch.tensor(train_y_raw, dtype=torch.float32 if is_regression else torch.long)
    test_y = torch.tensor(test_y_raw, dtype=torch.float32 if is_regression else torch.long)

    input_size = train_features.shape[1]
    output_size = 1 if is_regression else int(train_labels.nunique())

    if mode == "finetune":
        if base_model_uri is None:
            raise RuntimeError("MODE=finetune requires BASE_MODEL_URI")
        model = cast(nn.Module, mlflow_pytorch.load_model(base_model_uri))
    elif architecture == "mlp":
        model = spec.model_class(
            input_size=input_size,
            hidden_layers=[int(n) for n in hyperparameters["hidden_layers"]],
            dropout=float(hyperparameters["dropout"]),
            output_size=output_size,
        )
    else:
        model = spec.model_class(
            input_size=input_size,
            hidden_size=int(hyperparameters["hidden_size"]),
            num_layers=int(hyperparameters["num_layers"]),
            output_size=output_size,
        )

    loss_fn: nn.Module = nn.MSELoss() if is_regression else nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loader = DataLoader(TensorDataset(train_x, train_y), batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            output = model(batch_x)
            loss = loss_fn(output.squeeze(-1) if is_regression else output, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(batch_x)
        mlflow.log_metric("loss", epoch_loss / len(train_x), step=epoch)

    model.eval()
    with torch.no_grad():
        raw_predictions = model(test_x)
        if is_regression:
            predictions = raw_predictions.squeeze(-1).numpy() * target_std + target_mean
            y_true = test_y.numpy() * target_std + target_mean
        else:
            predictions = raw_predictions.argmax(dim=1).numpy()
            y_true = test_y.numpy()

    return model, compute_metrics(task_type, y_true, predictions)
