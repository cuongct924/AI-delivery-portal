"""infra/argo-workflows/training-image/train.py — main()'s ARCHITECTURE
dispatch. Mocks mlflow (module + submodule imports) and train_dl's
train_and_evaluate so this runs with no MLflow server and no real training,
exercising only the branching logic itself.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

_BASE_ENV = {
    "TASK_TYPE": "regression",
    "TARGET_COLUMN": "target",
    "ID_COLUMNS": "",
    "MODE": "train",
    "BASE_MODEL_URI": "",
    "TIME_COLUMN": "",
}


def _write_dataset(tmp_path: Path) -> Path:
    csv_path = tmp_path / "data.csv"
    df = pd.DataFrame(
        {
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "f2": [6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
            "target": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )
    df.to_csv(csv_path, index=False)
    (tmp_path / "data.csv.dvc").write_text("outs:\n- md5: deadbeef\n  path: data.csv\n")
    return csv_path


def _set_env(
    monkeypatch: pytest.MonkeyPatch, csv_path: Path, tmp_path: Path, **overrides: str
) -> None:
    env = {**_BASE_ENV, "DATASET_URI": f"file://{csv_path}", **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("ARCHITECTURE", raising=False)
    monkeypatch.chdir(tmp_path)


@patch("train.mlflow_sklearn")
@patch("train.mlflow_data")
@patch("train.mlflow")
def test_main_sklearn_branch_unchanged_when_architecture_unset(
    mock_mlflow: MagicMock,
    mock_mlflow_data: MagicMock,
    mock_mlflow_sklearn: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = _write_dataset(tmp_path)
    mock_mlflow.start_run.return_value.__enter__.return_value.info.run_id = "run-1"
    mock_dl = MagicMock(side_effect=AssertionError("DL path must not run for architecture=sklearn"))
    monkeypatch.setattr("train.train_dl_and_evaluate", mock_dl)
    _set_env(monkeypatch, csv_path, tmp_path, ALGORITHM="LinearRegression")

    import train

    train.main()

    mock_mlflow_sklearn.log_model.assert_called_once()
    mock_dl.assert_not_called()


@patch("train.mlflow_pytorch")
@patch("train.mlflow_data")
@patch("train.mlflow")
def test_main_dl_branch_dispatches_to_train_dl_when_architecture_set(
    mock_mlflow: MagicMock,
    mock_mlflow_data: MagicMock,
    mock_mlflow_pytorch: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = _write_dataset(tmp_path)
    mock_mlflow.start_run.return_value.__enter__.return_value.info.run_id = "run-2"
    fake_model = MagicMock()
    mock_dl = MagicMock(
        return_value=(fake_model, {"r2": 0.9, "mean_absolute_percentage_error": 0.1})
    )
    monkeypatch.setattr("train.train_dl_and_evaluate", mock_dl)
    _set_env(
        monkeypatch,
        csv_path,
        tmp_path,
        LEARNING_RATE="0.01",
        EPOCHS="1",
        BATCH_SIZE="4",
        HIDDEN_LAYERS="8,4",
        DROPOUT="0.0",
    )
    monkeypatch.setenv("ARCHITECTURE", "mlp")

    import train

    train.main()

    mock_dl.assert_called_once()
    called_args = mock_dl.call_args.args
    assert called_args[4] == "regression"  # task_type
    assert called_args[5] == "mlp"  # architecture
    mock_mlflow_pytorch.log_model.assert_called_once_with(fake_model, artifact_path="model")


def test_main_requires_algorithm_when_architecture_is_sklearn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = _write_dataset(tmp_path)
    _set_env(monkeypatch, csv_path, tmp_path)  # no ALGORITHM set

    import train

    with pytest.raises(RuntimeError, match="ALGORITHM is required"):
        train.main()


def test_main_rejects_dl_architecture_for_clustering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = _write_dataset(tmp_path)
    _set_env(monkeypatch, csv_path, tmp_path, TASK_TYPE="clustering", TARGET_COLUMN="")
    monkeypatch.setenv("ARCHITECTURE", "lstm")

    import train

    with pytest.raises(RuntimeError, match="does not support task_type='clustering'"):
        train.main()
