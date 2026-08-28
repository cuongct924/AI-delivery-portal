"""Optimizer selection (Dev-facing) — shared between train_dl.py and
train_cv.py, the 2 places that build a raw `torch.optim` optimizer
directly. train_nlp.py's HuggingFace `Trainer` takes an `optim=` string
of its own instead (mapped separately there, not through this module).

This resolves the "optimizer" open point noted in
docs/mlops-lifecycle-software-template.md (the Q&A section before mục
7b.4) — previously fixed to Adam automatically; now a Dev-facing choice
between Adam and SGD, their own respective library defaults otherwise
(e.g. SGD's momentum=0) — no extra tuning knobs beyond the 2 the Dev
actually asked to choose between.
"""

from collections.abc import Callable, Iterable
from typing import Final

import torch

# Callable, not type[torch.optim.Optimizer] — Adam/SGD's own __init__
# signatures (which accept `lr=`) are what's actually called below; the
# base Optimizer.__init__(params, defaults) signature doesn't.
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
            backbone, mục 6h.2).
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
