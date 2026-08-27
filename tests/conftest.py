"""pytest collects (imports) every test module in this directory before
running any of them. Importing torch here first, before pytest reaches a
module that imports xgboost/lightgbm (algorithm_registry.py, transitively:
tests/test_algorithm_registry.py, tests/test_models_router.py, ...), avoids
a macOS-only segfault — loading xgboost/lightgbm's OpenMP runtime before
torch's own crashes on the first CrossEntropyLoss call in this process.
Harmless on Linux (the actual training-image target)."""

import torch  # noqa: F401
