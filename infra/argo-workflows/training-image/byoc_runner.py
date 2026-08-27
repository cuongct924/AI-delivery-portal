"""BYOC (Bring-Your-Own-Code) support for Golden Path #1 (mục 6b.3,
docs/mlops-lifecycle-software-template.md) — Dev supplies a Git repo + a
path to a file exposing a fixed-signature `train()` function. The platform
clones the repo, dynamically imports that file, and calls `train()` with the
already-loaded dataset and a free-form JSON config dict.

No custom Docker image: this runs inside the same training-image as
everything else, sandboxed only by the least-privilege ServiceAccount
already in place (mục 3.1) — not by anything new at the container/cluster
level.
"""

import importlib.util
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pandas as pd

TrainFunction = Callable[[pd.DataFrame, dict[str, Any]], tuple[Any, dict[str, float]]]


def clone_repo(repo_url: str, dest: Path) -> None:
    """Shallow-clones `repo_url` into `dest`.

    Raises:
        subprocess.CalledProcessError: any git failure (bad URL, no network,
            private repo without credentials) — git's own stderr ends up in
            the Argo pod log via the top-level exception handler in
            `train.py`.
    """
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def load_train_function(entrypoint_path: Path) -> TrainFunction:
    """Dynamically imports the Dev's entrypoint file and returns its
    `train` attribute.

    Args:
        entrypoint_path: Path to the Dev's Python file, already cloned.

    Returns:
        The `train(dataset, config) -> (model, metrics)` callable.

    Raises:
        RuntimeError: the file doesn't exist, or doesn't define a callable
            `train` — enforced here so a Dev mistake fails with a clear
            message instead of a traceback deep inside the call site.
    """
    if not entrypoint_path.is_file():
        raise RuntimeError(f"entrypoint file not found: {entrypoint_path}")
    spec = importlib.util.spec_from_file_location("byoc_entrypoint", entrypoint_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load entrypoint module from {entrypoint_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    train_fn = getattr(module, "train", None)
    if train_fn is None or not callable(train_fn):
        raise RuntimeError(
            f"{entrypoint_path} must define a callable `train(dataset, config)` function"
        )
    # Can't statically verify a dynamically-imported function's signature —
    # run_custom_training() validates the actual return shape at runtime.
    return cast(TrainFunction, train_fn)


def run_custom_training(
    dataset: pd.DataFrame,
    config: dict[str, Any],
    code_repo_url: str,
    entrypoint_path: str,
    workdir: Path,
) -> tuple[Any, dict[str, float]]:
    """Runs the full BYOC flow: clone, import, call.

    Args:
        dataset: The raw dataset loaded from `DATASET_URI`, unmodified —
            BYOC bypasses the platform's own split/impute/scale steps
            entirely, the Dev's `train()` owns that.
        config: Free-form hyperparameters the Dev defined, plus a reserved
            `target_column` key the platform injects (see `train.py`).
        code_repo_url: Git repo URL to clone.
        entrypoint_path: Path, relative to the repo root, to the file
            defining `train()`.
        workdir: Empty directory to clone into.

    Returns:
        (model, metrics) — metrics coerced to `dict[str, float]`.

    Raises:
        RuntimeError: `train()` didn't return the contracted shape, or the
            returned model has no `.predict()` — required by
            `pyfunc_wrapper.GenericPyfuncWrapper` for serving.
    """
    clone_repo(code_repo_url, workdir)
    train_fn = load_train_function(workdir / entrypoint_path)
    result = train_fn(dataset, config)
    if not (isinstance(result, tuple) and len(result) == 2):
        raise RuntimeError(
            f"train() in {entrypoint_path} must return (model, metrics) — got {result!r}"
        )
    model, metrics = result
    if not isinstance(metrics, dict) or not all(
        isinstance(k, str) and isinstance(v, int | float) for k, v in metrics.items()
    ):
        raise RuntimeError(
            f"train() in {entrypoint_path} must return metrics as dict[str, float] — "
            f"got {metrics!r}"
        )
    if not hasattr(model, "predict"):
        raise RuntimeError(
            f"train() in {entrypoint_path} must return a model exposing .predict(X) — "
            "required by the platform's generic serving wrapper (mục 6b.1)"
        )
    return model, {name: float(value) for name, value in metrics.items()}
