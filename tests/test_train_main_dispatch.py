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


def test_main_hpo_branch_dispatches_to_run_hpo_when_search_strategy_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with (
        patch("train.mlflow_pytorch") as mock_mlflow_pytorch,
        patch("train.mlflow_data"),
        patch("train.mlflow") as mock_mlflow,
    ):
        csv_path = _write_dataset(tmp_path)
        mock_mlflow.start_run.return_value.__enter__.return_value.info.run_id = "run-hpo"
        fake_model = MagicMock()
        mock_run_hpo = MagicMock(
            return_value=(fake_model, {"r2": 0.95}, {"learning_rate": 0.01, "epochs": 10})
        )
        monkeypatch.setattr("train.run_hpo", mock_run_hpo)
        monkeypatch.setattr("train.train_dl_and_evaluate", MagicMock(side_effect=AssertionError))
        _set_env(
            monkeypatch,
            csv_path,
            tmp_path,
            LEARNING_RATE="0.01",
            EPOCHS="10",
            BATCH_SIZE="4",
            HIDDEN_LAYERS="8,4",
            DROPOUT="0.0",
            SEARCH_STRATEGY="bayesian",
            NUM_TRIALS="5",
            SEARCH_SPACE_JSON='{"learning_rate": {"low": 0.001, "high": 0.1}}',
            OBJECTIVE_METRIC="r2",
            OBJECTIVE_DIRECTION="maximize",
        )
        monkeypatch.setenv("ARCHITECTURE", "mlp")

        import train

        train.main()

        mock_run_hpo.assert_called_once()
        mock_mlflow_pytorch.log_model.assert_called_once_with(fake_model, artifact_path="model")
        mock_mlflow.log_param.assert_any_call("search_strategy", "bayesian")


def test_main_rejects_search_strategy_for_sklearn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = _write_dataset(tmp_path)
    _set_env(monkeypatch, csv_path, tmp_path, ALGORITHM="LinearRegression", SEARCH_STRATEGY="grid")

    import train

    with pytest.raises(RuntimeError, match="SEARCH_STRATEGY != 'fixed' requires ARCHITECTURE"):
        train.main()


@patch("train.mlflow_pyfunc")
@patch("train.mlflow_data")
@patch("train.mlflow")
def test_main_byoc_branch_dispatches_to_run_custom_training(
    mock_mlflow: MagicMock,
    mock_mlflow_data: MagicMock,
    mock_mlflow_pyfunc: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = _write_dataset(tmp_path)
    mock_mlflow.start_run.return_value.__enter__.return_value.info.run_id = "run-3"
    fake_model = MagicMock()
    mock_run_custom = MagicMock(return_value=(fake_model, {"accuracy": 0.95}))
    monkeypatch.setattr("train.run_custom_training", mock_run_custom)
    _set_env(
        monkeypatch,
        csv_path,
        tmp_path,
        TASK_TYPE="classification",
        ALGORITHM="custom",
        CODE_REPO_URL="https://github.com/dev/repo",
        ENTRYPOINT_PATH="my_train.py",
        CUSTOM_CONFIG='{"lr": 0.01}',
    )

    import train

    train.main()

    mock_run_custom.assert_called_once()
    call_args = mock_run_custom.call_args.args
    assert call_args[1] == {"lr": 0.01, "target_column": "target"}  # config, incl. injected key
    assert call_args[2] == "https://github.com/dev/repo"
    assert call_args[3] == "my_train.py"
    mock_mlflow.log_metric.assert_called_once_with("accuracy", 0.95)
    mock_mlflow_pyfunc.log_model.assert_called_once()
    assert mock_mlflow_pyfunc.log_model.call_args.kwargs["artifact_path"] == "model"


def test_main_byoc_requires_code_repo_url_and_entrypoint_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = _write_dataset(tmp_path)
    _set_env(monkeypatch, csv_path, tmp_path, ALGORITHM="custom")

    import train

    with pytest.raises(RuntimeError, match="CODE_REPO_URL and ENTRYPOINT_PATH are required"):
        train.main()


def test_main_byoc_rejects_finetune_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = _write_dataset(tmp_path)
    _set_env(
        monkeypatch,
        csv_path,
        tmp_path,
        ALGORITHM="custom",
        MODE="finetune",
        CODE_REPO_URL="https://github.com/dev/repo",
        ENTRYPOINT_PATH="my_train.py",
    )

    import train

    with pytest.raises(RuntimeError, match="does not support MODE=finetune"):
        train.main()


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
