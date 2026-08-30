"""Optimizer selection (Dev-facing choice between Adam and SGD, each
kept at its library defaults otherwise) — shared between train_dl.py and
train_cv.py, the 2 places that build a raw `torch.optim` optimizer
directly. train_nlp.py's HuggingFace `Trainer` takes an `optim=` string of
its own instead (mapped separately there, not through this module).
"""

from collections.abc import Callable, Iterable
from typing import Final

import torch

# Callable, not type[Optimizer] — Adam/SGD's __init__ accepts lr=, the base class's doesn't.
_OPTIMIZERS: Final[dict[str, Callable[..., torch.optim.Optimizer]]] = {
    "adam": torch.optim.Adam,
    "sgd": torch.optim.SGD,
}


def build_optimizer(
    name: str, params: Iterable[torch.nn.Parameter], learning_rate: float
) -> torch.optim.Optimizer:
    """Constructs the chosen optimizer.

    Args:
        name: "adam" or "sgd".
        params: The model parameters to optimize (all of them for
            train_dl.py; only the replaced head for train_cv.py's frozen
            backbone).
        learning_rate: Passed through as-is to the optimizer's `lr`.

    Returns:
        The constructed optimizer.

    Raises:
        ValueError: `name` isn't a recognized optimizer.
    """
    optimizer_cls = _OPTIMIZERS.get(name)
    if optimizer_cls is None:
        raise ValueError(f"unknown optimizer {name!r} — must be one of {sorted(_OPTIMIZERS)}")
    return optimizer_cls(params, lr=learning_rate)
