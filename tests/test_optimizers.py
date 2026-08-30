"""infra/argo-workflows/training-image/optimizers.py."""

import pytest
import torch
from optimizers import build_optimizer
from torch import nn


def test_build_optimizer_adam_returns_adam_instance() -> None:
    model = nn.Linear(2, 1)
    optimizer = build_optimizer("adam", model.parameters(), 0.01)

    assert isinstance(optimizer, torch.optim.Adam)
    assert optimizer.param_groups[0]["lr"] == 0.01


def test_build_optimizer_sgd_returns_sgd_instance() -> None:
    model = nn.Linear(2, 1)
    optimizer = build_optimizer("sgd", model.parameters(), 0.05)

    assert isinstance(optimizer, torch.optim.SGD)
    assert optimizer.param_groups[0]["lr"] == 0.05


def test_build_optimizer_rejects_unknown_name() -> None:
    model = nn.Linear(2, 1)
    with pytest.raises(ValueError, match="unknown optimizer"):
        build_optimizer("rmsprop", model.parameters(), 0.01)
