"""Registry of Deep Learning architectures — same registry-by-dimension
pattern as algorithm_registry.py's TASK_TYPE_ALGORITHMS, keyed by
architecture name instead of task type.
"""

from dataclasses import dataclass
from typing import Final

from dl_models import LSTMModel, MLPModel
from torch import nn


@dataclass(frozen=True)
class DLArchitectureSpec:
    """One registry entry.

    Attributes:
        model_class: The nn.Module subclass to instantiate.
        requires_time_column: True for LSTM — sequence windowing needs a
            row ordering. False for MLP — timeColumn only improves split
            validity there (train.py's existing TimeSeriesSplit logic).
        hyperparameters: Names of the Dev-facing fields this architecture
            exposes.
    """

    model_class: type[nn.Module]
    requires_time_column: bool
    hyperparameters: list[str]


DL_ARCHITECTURES: Final[dict[str, DLArchitectureSpec]] = {
    "mlp": DLArchitectureSpec(
        model_class=MLPModel,
        requires_time_column=False,
        hyperparameters=["hidden_layers", "dropout", "learning_rate", "epochs", "batch_size"],
    ),
    "lstm": DLArchitectureSpec(
        model_class=LSTMModel,
        requires_time_column=True,
        hyperparameters=[
            "sequence_length",
            "num_layers",
            "hidden_size",
            "learning_rate",
            "epochs",
            "batch_size",
        ],
    ),
}


def get_dl_architecture(architecture: str) -> DLArchitectureSpec:
    """Looks up a registry entry.

    Args:
        architecture: "mlp" or "lstm".

    Returns:
        The matching DLArchitectureSpec.

    Raises:
        ValueError: architecture isn't in the registry.
    """
    spec = DL_ARCHITECTURES.get(architecture)
    if spec is None:
        raise ValueError(
            f"unknown architecture {architecture!r} — must be one of {sorted(DL_ARCHITECTURES)}"
        )
    return spec
