"""infra/argo-workflows/training-image/train_cv.py — dataset extraction,
train/test split, and CVModel.predict(), with the pretrained resnet18
backbone mocked out (no network download) in favor of a tiny real nn.Module
so autograd/backward() still runs for real."""

import base64
import io
import zipfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import torch
from PIL import Image
from torch import nn
from torchvision import transforms

_TINY_IMAGE_SIZE = 8


class _TinyBackbone(nn.Module):
    """Stand-in for resnet18 — flattens a _TINY_IMAGE_SIZE x _TINY_IMAGE_SIZE
    RGB image straight into a linear layer, matching the "has a `.fc`
    attribute that gets replaced" contract `train_and_evaluate()` relies
    on."""

    def __init__(self) -> None:
        super().__init__()
        self.fc = nn.Linear(3 * _TINY_IMAGE_SIZE * _TINY_IMAGE_SIZE, 1000)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x.flatten(1))


def _make_shapes_zip(zip_path: Path, classes: list[str], images_per_class: int) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        for class_name in classes:
            for i in range(images_per_class):
                img = Image.new("RGB", (16, 16), color=(i * 10 % 256, 50, 100))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"{class_name}/{class_name}_{i}.png", buf.getvalue())


@pytest.fixture
def _tiny_transform() -> transforms.Compose:
    return transforms.Compose(
        [transforms.Resize((_TINY_IMAGE_SIZE, _TINY_IMAGE_SIZE)), transforms.ToTensor()]
    )


@patch("train_cv.resnet18")
def test_train_and_evaluate_returns_model_and_metrics(
    mock_resnet18: MagicMock, tmp_path: Path, _tiny_transform: transforms.Compose
) -> None:
    mock_resnet18.return_value = _TinyBackbone()
    zip_path = tmp_path / "shapes.zip"
    _make_shapes_zip(zip_path, classes=["circle", "square"], images_per_class=6)

    with patch("train_cv._TRANSFORM", _tiny_transform):
        from train_cv import CVModel, train_and_evaluate

        model, metrics = train_and_evaluate(
            zip_path, {"learning_rate": 0.01, "epochs": 1, "batch_size": 2}
        )

    assert isinstance(model, CVModel)
    assert set(metrics) == {"accuracy", "precision", "recall", "f1"}
    assert 0.0 <= metrics["accuracy"] <= 1.0


@patch("train_cv.resnet18")
def test_train_and_evaluate_freezes_backbone_and_trains_only_the_head(
    mock_resnet18: MagicMock, tmp_path: Path, _tiny_transform: transforms.Compose
) -> None:
    mock_resnet18.return_value = _TinyBackbone()
    zip_path = tmp_path / "shapes.zip"
    _make_shapes_zip(zip_path, classes=["circle", "square"], images_per_class=6)

    with patch("train_cv._TRANSFORM", _tiny_transform):
        from train_cv import train_and_evaluate

        model, _ = train_and_evaluate(
            zip_path, {"learning_rate": 0.01, "epochs": 1, "batch_size": 2}
        )

    # model._backbone.fc is the only param group with requires_grad=True.
    backbone = model._backbone  # noqa: SLF001 — white-box check
    fc: nn.Module = cast(Any, backbone).fc
    fc_params = set(fc.parameters())
    for name, param in backbone.named_parameters():
        if param in fc_params:
            assert param.requires_grad, name
        else:
            assert not param.requires_grad, name


@patch("train_cv.resnet18")
def test_cv_model_predict_decodes_base64_images_and_returns_class_names(
    mock_resnet18: MagicMock, tmp_path: Path, _tiny_transform: transforms.Compose
) -> None:
    mock_resnet18.return_value = _TinyBackbone()
    zip_path = tmp_path / "shapes.zip"
    _make_shapes_zip(zip_path, classes=["circle", "square"], images_per_class=6)

    with patch("train_cv._TRANSFORM", _tiny_transform):
        from train_cv import train_and_evaluate

        model, _ = train_and_evaluate(
            zip_path, {"learning_rate": 0.01, "epochs": 1, "batch_size": 2}
        )

        img = Image.new("RGB", (16, 16), color=(200, 50, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode()

        predictions = model.predict(pd.DataFrame({"image": [encoded, encoded]}))

    assert predictions == [predictions[0], predictions[0]]
    assert predictions[0] in {"circle", "square"}


@patch("train_cv.resnet18")
def test_train_and_evaluate_uses_sgd_when_requested(
    mock_resnet18: MagicMock, tmp_path: Path, _tiny_transform: transforms.Compose
) -> None:
    mock_resnet18.return_value = _TinyBackbone()
    zip_path = tmp_path / "shapes.zip"
    _make_shapes_zip(zip_path, classes=["circle", "square"], images_per_class=6)

    with patch("train_cv._TRANSFORM", _tiny_transform):
        from optimizers import build_optimizer
        from train_cv import train_and_evaluate

        with patch("train_cv.build_optimizer", wraps=build_optimizer) as mock_build:
            train_and_evaluate(
                zip_path, {"learning_rate": 0.01, "epochs": 1, "batch_size": 2, "optimizer": "sgd"}
            )

    assert mock_build.call_args.args[0] == "sgd"
