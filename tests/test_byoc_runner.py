"""infra/argo-workflows/training-image/byoc_runner.py — clone + dynamic
import + contract validation, exercised without a real git remote or MLflow
server."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from byoc_runner import clone_repo, load_train_function, run_custom_training


def _write_entrypoint(path: Path, body: str) -> None:
    path.write_text(body)


def test_clone_repo_shells_out_to_git_clone(tmp_path: Path) -> None:
    dest = tmp_path / "repo"
    with patch("byoc_runner.subprocess.run") as mock_run:
        clone_repo("https://github.com/dev/repo", dest)

    mock_run.assert_called_once_with(
        ["git", "clone", "--depth", "1", "https://github.com/dev/repo", str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_clone_repo_propagates_git_failure(tmp_path: Path) -> None:
    dest = tmp_path / "repo"
    with (
        patch(
            "byoc_runner.subprocess.run",
            side_effect=subprocess.CalledProcessError(128, "git clone"),
        ),
        pytest.raises(subprocess.CalledProcessError),
    ):
        clone_repo("https://github.com/dev/does-not-exist", dest)


def test_load_train_function_returns_the_train_callable(tmp_path: Path) -> None:
    entrypoint = tmp_path / "my_train.py"
    _write_entrypoint(
        entrypoint,
        "def train(dataset, config):\n    return object(), {'accuracy': 1.0}\n",
    )

    train_fn = load_train_function(entrypoint)
    model, metrics = train_fn(pd.DataFrame(), {})
    assert metrics == {"accuracy": 1.0}


def test_load_train_function_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="entrypoint file not found"):
        load_train_function(tmp_path / "missing.py")


def test_load_train_function_no_train_attribute_raises(tmp_path: Path) -> None:
    entrypoint = tmp_path / "my_train.py"
    _write_entrypoint(entrypoint, "def not_train():\n    pass\n")

    with pytest.raises(RuntimeError, match="must define a callable `train"):
        load_train_function(entrypoint)


def test_run_custom_training_end_to_end(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"

    def fake_clone(repo_url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        _write_entrypoint(
            dest / "my_train.py",
            "def train(dataset, config):\n"
            "    model = type('M', (), {'predict': lambda self, x: x})()\n"
            "    return model, {'accuracy': 0.9}\n",
        )

    with patch("byoc_runner.clone_repo", side_effect=fake_clone):
        model, metrics = run_custom_training(
            pd.DataFrame({"a": [1]}),
            {"target_column": "label"},
            "https://github.com/dev/repo",
            "my_train.py",
            workdir,
        )

    assert metrics == {"accuracy": 0.9}
    assert hasattr(model, "predict")


def test_run_custom_training_rejects_non_tuple_return(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"

    def fake_clone(repo_url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        _write_entrypoint(dest / "my_train.py", "def train(dataset, config):\n    return 42\n")

    with (
        patch("byoc_runner.clone_repo", side_effect=fake_clone),
        pytest.raises(RuntimeError, match="must return \\(model, metrics\\)"),
    ):
        run_custom_training(pd.DataFrame(), {}, "url", "my_train.py", workdir)


def test_run_custom_training_rejects_non_numeric_metrics(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"

    def fake_clone(repo_url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        _write_entrypoint(
            dest / "my_train.py",
            "def train(dataset, config):\n    return object(), {'accuracy': 'high'}\n",
        )

    with (
        patch("byoc_runner.clone_repo", side_effect=fake_clone),
        pytest.raises(RuntimeError, match="dict\\[str, float\\]"),
    ):
        run_custom_training(pd.DataFrame(), {}, "url", "my_train.py", workdir)


def test_run_custom_training_rejects_model_without_predict(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"

    def fake_clone(repo_url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        _write_entrypoint(
            dest / "my_train.py",
            "def train(dataset, config):\n    return object(), {'accuracy': 0.9}\n",
        )

    with (
        patch("byoc_runner.clone_repo", side_effect=fake_clone),
        pytest.raises(RuntimeError, match="must return a model exposing .predict"),
    ):
        run_custom_training(pd.DataFrame(), {}, "url", "my_train.py", workdir)
