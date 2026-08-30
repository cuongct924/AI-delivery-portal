"""pytest collects (imports) every test module in this directory before
running any of them. Importing torch here first, before pytest reaches a
module that imports xgboost/lightgbm (algorithm_registry.py, transitively:
tests/test_algorithm_registry.py, tests/test_models_router.py, ...), avoids
a macOS-only segfault — loading xgboost/lightgbm's OpenMP runtime before
torch's own crashes on the first CrossEntropyLoss call in this process.
Harmless on Linux (the actual training-image target).

Importing mlflow.pyfunc here first, for the same collection-order reason:
tests/test_mlflow_adapter.py and tests/test_models_router.py both do
`sys.modules.setdefault("mlflow", MagicMock())` at module level (to skip
mlflow's real, heavy import for their own unit tests) — since pytest
collects every module before running any test, that stub otherwise wins the
race and poisons `sys.modules["mlflow"]` for the whole session. Plain
`mlflow.log_metric(...)`-style calls elsewhere degrade harmlessly to a mock
call either way, but `pyfunc_wrapper.GenericPyfuncWrapper` subclasses
`mlflow.pyfunc.PythonModel` — a mocked, non-type attribute can't be
subclassed correctly, so it needs the real module loaded first.

Setting LLMOPS_REGISTRY_PATH before anything imports routers.prompts/
routers.rag/routers.chat, for a similar reason: each of those constructs a
module-level JsonFileVersionRegistryAdapter() singleton at import time,
which reads this env var in __init__. Left unset, all 3 would default to
the same real `.state/llmops-registry.json` relative to whatever the test
run's cwd happens to be — a file that outlives the test run and pollutes
the next one (tests/test_prompts_router.py's seeded-prompt assertions
would silently start reading stale state from a previous run instead of a
fresh seed). Redirecting to a fresh temp file gives every test run a clean
slate; not cleaned up afterwards since it's outside the repo entirely."""

import os
import tempfile

os.environ.setdefault(
    "LLMOPS_REGISTRY_PATH", os.path.join(tempfile.mkdtemp(), "llmops-registry.json")
)

import mlflow.pyfunc  # noqa: F401, E402
import torch  # noqa: F401, E402
