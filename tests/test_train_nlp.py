"""infra/argo-workflows/training-image/train_nlp.py — label encoding,
dataset construction, and metric computation, with the actual HuggingFace
model/tokenizer/Trainer classes mocked (no network, no real fine-tuning).
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class _FakeTokenizer:
    """Minimal stand-in that produces real (if meaningless) token ids so
    `datasets.Dataset.map()` — exercised for real here, not mocked — has
    valid per-example column data to merge in."""

    def __call__(
        self, texts: list[str], truncation: bool, padding: bool
    ) -> dict[str, list[list[int]]]:
        return {
            "input_ids": [[len(text)] for text in texts],
            "attention_mask": [[1] for _ in texts],
        }


@patch("train_nlp.Trainer")
@patch("train_nlp.AutoModelForSequenceClassification")
@patch("train_nlp.AutoTokenizer")
def test_train_and_evaluate_encodes_labels_consistently_and_returns_metrics(
    mock_auto_tokenizer: MagicMock,
    mock_auto_model: MagicMock,
    mock_trainer_cls: MagicMock,
) -> None:
    mock_auto_tokenizer.from_pretrained.return_value = _FakeTokenizer()
    fake_model = MagicMock()
    mock_auto_model.from_pretrained.return_value = fake_model

    mock_trainer = MagicMock()
    # 2 test rows, 2 classes — argmax picks index 1 then 0.
    mock_trainer.predict.return_value = MagicMock(predictions=np.array([[0.1, 0.9], [0.8, 0.2]]))
    mock_trainer_cls.return_value = mock_trainer

    from train_nlp import train_and_evaluate

    train_text = pd.Series(["great product", "terrible service", "loved it"])
    test_text = pd.Series(["not good", "amazing"])
    train_labels = pd.Series(["positive", "negative", "positive"])
    test_labels = pd.Series(["negative", "positive"])

    hyperparameters = {
        "base_model_name": "distilbert-base-uncased",
        "learning_rate": 5e-5,
        "epochs": 1,
        "batch_size": 2,
    }
    model, metrics = train_and_evaluate(
        train_text, test_text, train_labels, test_labels, hyperparameters
    )

    mock_auto_tokenizer.from_pretrained.assert_called_once_with("distilbert-base-uncased")
    mock_auto_model.from_pretrained.assert_called_once_with(
        "distilbert-base-uncased",
        num_labels=2,  # positive/negative
    )
    mock_trainer.train.assert_called_once()
    fake_tokenizer = mock_auto_tokenizer.from_pretrained.return_value
    assert model == {"model": fake_model, "tokenizer": fake_tokenizer}
    # Labels sorted: negative=0, positive=1. Predicted [1,0] vs true
    # [0,1] — both wrong.
    assert metrics["accuracy"] == 0.0
    assert set(metrics) == {"accuracy", "precision", "recall", "f1"}


@patch("train_nlp.Trainer")
@patch("train_nlp.AutoModelForSequenceClassification")
@patch("train_nlp.AutoTokenizer")
def test_train_and_evaluate_passes_hyperparameters_to_training_args(
    mock_auto_tokenizer: MagicMock,
    mock_auto_model: MagicMock,
    mock_trainer_cls: MagicMock,
) -> None:
    mock_auto_tokenizer.from_pretrained.return_value = _FakeTokenizer()
    mock_trainer = MagicMock()
    mock_trainer.predict.return_value = MagicMock(predictions=np.array([[0.9, 0.1]]))
    mock_trainer_cls.return_value = mock_trainer

    from train_nlp import train_and_evaluate

    hyperparameters = {
        "base_model_name": "distilbert-base-uncased",
        "learning_rate": 0.001,
        "epochs": 3,
        "batch_size": 8,
    }
    train_and_evaluate(
        pd.Series(["a", "b"]),
        pd.Series(["c"]),
        pd.Series(["x", "y"]),
        pd.Series(["x"]),
        hyperparameters,
    )

    _, kwargs = mock_trainer_cls.call_args
    training_args = kwargs["args"]
    assert training_args.num_train_epochs == 3
    assert training_args.per_device_train_batch_size == 8
    assert training_args.learning_rate == 0.001
    assert training_args.optim == "adamw_torch"  # default optimizer="adam"


@patch("train_nlp.Trainer")
@patch("train_nlp.AutoModelForSequenceClassification")
@patch("train_nlp.AutoTokenizer")
def test_train_and_evaluate_maps_sgd_to_the_hf_optim_name(
    mock_auto_tokenizer: MagicMock,
    mock_auto_model: MagicMock,
    mock_trainer_cls: MagicMock,
) -> None:
    mock_auto_tokenizer.from_pretrained.return_value = _FakeTokenizer()
    mock_trainer = MagicMock()
    mock_trainer.predict.return_value = MagicMock(predictions=np.array([[0.9, 0.1]]))
    mock_trainer_cls.return_value = mock_trainer

    from train_nlp import train_and_evaluate

    hyperparameters = {
        "base_model_name": "distilbert-base-uncased",
        "learning_rate": 0.001,
        "epochs": 1,
        "batch_size": 8,
        "optimizer": "sgd",
    }
    train_and_evaluate(
        pd.Series(["a", "b"]),
        pd.Series(["c"]),
        pd.Series(["x", "y"]),
        pd.Series(["x"]),
        hyperparameters,
    )

    _, kwargs = mock_trainer_cls.call_args
    assert kwargs["args"].optim == "sgd"


def test_train_and_evaluate_rejects_unknown_optimizer() -> None:
    from train_nlp import train_and_evaluate

    hyperparameters = {
        "base_model_name": "distilbert-base-uncased",
        "learning_rate": 0.001,
        "epochs": 1,
        "batch_size": 8,
        "optimizer": "rmsprop",
    }
    with pytest.raises(ValueError, match="unknown optimizer"):
        train_and_evaluate(
            pd.Series(["a", "b"]),
            pd.Series(["c"]),
            pd.Series(["x", "y"]),
            pd.Series(["x"]),
            hyperparameters,
        )
