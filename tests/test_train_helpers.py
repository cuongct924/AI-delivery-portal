"""infra/argo-workflows/training-image/train.py — the pure helper functions
(encoding/imputation/scaling/splitting), tested directly since they hold
the actual per-run decision logic (mục 2's "cơ chế ML thuần kỹ thuật" bucket
— what train.py automates instead of asking Dev)."""

from typing import cast

import numpy as np
import pandas as pd
from algorithm_registry import AlgorithmSpec
from sklearn.linear_model import LogisticRegression
from train import _encode_categoricals, _handle_missing_values, _scale_features, _split

_SCALING_SPEC = AlgorithmSpec(
    LogisticRegression, requires_scaling=True, handles_missing_natively=False
)
_NATIVE_MISSING_SPEC = AlgorithmSpec(
    LogisticRegression, requires_scaling=False, handles_missing_natively=True
)


def test_encode_categoricals_turns_object_columns_numeric() -> None:
    df = pd.DataFrame({"category": ["a", "b", "a"], "number": [1, 2, 3]})
    encoded = _encode_categoricals(df)
    assert pd.api.types.is_numeric_dtype(encoded["category"])
    assert pd.api.types.is_numeric_dtype(encoded["number"])


def test_encode_categoricals_keeps_missing_as_nan_not_sentinel() -> None:
    df = pd.DataFrame({"category": ["a", None, "b"]})
    encoded = _encode_categoricals(df)
    assert encoded["category"].isna().sum() == 1
    assert -1 not in encoded["category"].values


def test_handle_missing_values_imputes_when_algorithm_needs_it() -> None:
    train = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    test = pd.DataFrame({"x": [np.nan]})
    imputed_train, imputed_test = _handle_missing_values(train, test, _SCALING_SPEC)
    assert imputed_train["x"].isna().sum() == 0
    assert imputed_test["x"].isna().sum() == 0


def test_handle_missing_values_leaves_nan_for_native_handling_algorithm() -> None:
    train = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    test = pd.DataFrame({"x": [np.nan]})
    imputed_train, imputed_test = _handle_missing_values(train, test, _NATIVE_MISSING_SPEC)
    assert imputed_train["x"].isna().sum() == 1
    assert imputed_test["x"].isna().sum() == 1


def test_scale_features_standardizes_when_algorithm_requires_it() -> None:
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    test = pd.DataFrame({"x": [3.0]})
    scaled_train, _ = _scale_features(train, test, _SCALING_SPEC)
    assert abs(scaled_train["x"].mean()) < 1e-9


def test_scale_features_leaves_tree_based_features_untouched() -> None:
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    test = pd.DataFrame({"x": [4.0]})
    scaled_train, _ = _scale_features(train, test, _NATIVE_MISSING_SPEC)
    assert list(scaled_train["x"]) == [1.0, 2.0, 3.0]


def test_split_with_time_column_never_shuffles() -> None:
    df = pd.DataFrame({"t": [5, 1, 3, 2, 4, 0], "y": [0, 1, 0, 1, 0, 1]})
    features = pd.DataFrame({"t": df["t"]})
    labels = cast(pd.Series, df["y"])
    train_x, test_x, _, _ = _split(df, features, labels, "classification", time_column="t")
    # Every training-split timestamp must precede every test-split timestamp.
    assert train_x["t"].max() < test_x["t"].min()


def test_split_without_time_column_returns_disjoint_train_test() -> None:
    df = pd.DataFrame({"x": range(100), "y": [0, 1] * 50})
    features = pd.DataFrame({"x": df["x"]})
    labels = cast(pd.Series, df["y"])
    train_x, test_x, train_y, test_y = _split(
        df, features, labels, "classification", time_column=None
    )
    assert set(train_x.index).isdisjoint(set(test_x.index))
    assert len(train_x) == len(train_y)
    assert len(test_x) == len(test_y)
