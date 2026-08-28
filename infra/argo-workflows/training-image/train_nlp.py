"""Text classification training (Phase 6, mục 6g,
docs/mlops-lifecycle-software-template.md) — fine-tunes a pretrained
HuggingFace sequence-classification model with `transformers.Trainer`. Same
role as `train_dl.py`/`byoc_runner.py`: a separate script `train.py`
dispatches into, not a rewrite of the shared split/gate/register flow.
"""

from typing import Any, cast

import numpy as np
import pandas as pd
from datasets import Dataset
from metrics import compute_metrics
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


def train_and_evaluate(
    train_text: pd.Series,
    test_text: pd.Series,
    train_labels: pd.Series,
    test_labels: pd.Series,
    hyperparameters: dict[str, object],
) -> tuple[Any, dict[str, float]]:
    """Fine-tunes `hyperparameters["base_model_name"]` for single-label text
    classification and evaluates it on the held-out split.

    Args:
        train_text: Raw text column, train split — never run through
            `train.py`'s `_encode_categoricals()` (mục 6g.3), which would
            corrupt it into category codes.
        test_text: Raw text column, test split.
        train_labels: Label column (string classes), train split.
        test_labels: Label column, test split.
        hyperparameters: `base_model_name` (HuggingFace Hub model id),
            `learning_rate`, `epochs`, `batch_size` — mục 6g.2.

    Returns:
        (transformers model, metrics) — `metrics` from the same
        `compute_metrics("classification", ...)` the sklearn/DL paths use.
    """
    base_model_name = cast(str, hyperparameters["base_model_name"])
    # Both splits' label sets combined so a class only present in the test
    # split still gets a stable code, and codes agree between splits.
    label_dtype = pd.CategoricalDtype(categories=sorted(set(train_labels) | set(test_labels)))
    train_label_ids = train_labels.astype(label_dtype).cat.codes
    test_label_ids = test_labels.astype(label_dtype).cat.codes
    num_labels = len(label_dtype.categories)

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model_name, num_labels=num_labels
    )

    def _tokenize(batch: dict[str, list[str]]) -> Any:
        return tokenizer(batch["text"], truncation=True, padding=True)

    train_dataset = Dataset.from_dict(
        {"text": train_text.tolist(), "label": train_label_ids.tolist()}
    ).map(_tokenize, batched=True)
    test_dataset = Dataset.from_dict(
        {"text": test_text.tolist(), "label": test_label_ids.tolist()}
    ).map(_tokenize, batched=True)

    training_args = TrainingArguments(
        output_dir="/tmp/nlp-trainer",
        num_train_epochs=int(cast(int, hyperparameters["epochs"])),
        per_device_train_batch_size=int(cast(int, hyperparameters["batch_size"])),
        per_device_eval_batch_size=int(cast(int, hyperparameters["batch_size"])),
        learning_rate=float(cast(float, hyperparameters["learning_rate"])),
        eval_strategy="epoch",
        logging_strategy="epoch",
        # train.py already owns the mlflow.start_run() for this job — the
        # Trainer's own MLflow integration would open a conflicting 2nd run.
        report_to=[],
        disable_tqdm=True,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        processing_class=tokenizer,
    )
    trainer.train()

    # datasets.Dataset's stub isn't parametrized the way Trainer.predict()
    # expects, and PredictionOutput.predictions is typed as a tuple to
    # account for multi-output models — this one only has 1 output head.
    predictions = trainer.predict(cast(Any, test_dataset))
    predicted_ids = cast(np.ndarray, predictions.predictions).argmax(axis=-1)
    metrics = compute_metrics("classification", test_label_ids, predicted_ids)
    return {"model": model, "tokenizer": tokenizer}, metrics
