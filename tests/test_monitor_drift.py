"""infra/argo-workflows/training-image/monitor_drift.py — compute_drift_share()
against real (small, fast) Evidently reports, and _trigger_retrain()'s
httpx call, mocked."""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from monitor_drift import _trigger_retrain, compute_drift_share


def test_compute_drift_share_is_high_when_distributions_shift() -> None:
    rng = np.random.default_rng(0)
    reference = pd.DataFrame({"a": rng.normal(0, 1, 200), "b": rng.normal(5, 2, 200)})
    current = pd.DataFrame({"a": rng.normal(6, 1, 200), "b": rng.normal(5, 2, 200)})

    share = compute_drift_share(reference, current)

    # "a" shifted hard, "b" didn't — 1 of 2 columns drifted.
    assert share == pytest.approx(0.5)


def test_compute_drift_share_is_low_when_distributions_match() -> None:
    rng = np.random.default_rng(1)
    reference = pd.DataFrame({"a": rng.normal(0, 1, 300), "b": rng.normal(5, 2, 300)})
    current = pd.DataFrame({"a": rng.normal(0, 1, 300), "b": rng.normal(5, 2, 300)})

    share = compute_drift_share(reference, current)

    assert share == pytest.approx(0.0)


@patch("monitor_drift.httpx.post")
def test_trigger_retrain_posts_the_dev_supplied_body(mock_post: MagicMock) -> None:
    mock_post.return_value = MagicMock(is_error=False)
    body = {
        "model_name": "fraud-detection",
        "dataset_uri": "file:///data.csv",
        "task_type": "classification",
    }

    _trigger_retrain(json.dumps(body), "http://orchestration-api.test")

    mock_post.assert_called_once_with(
        "http://orchestration-api.test/trigger-training", json=body, timeout=30.0
    )


@patch("monitor_drift.sys.exit")
@patch("monitor_drift.httpx.post")
def test_trigger_retrain_exits_nonzero_on_http_error(
    mock_post: MagicMock, mock_exit: MagicMock
) -> None:
    mock_post.return_value = MagicMock(is_error=True, status_code=500, text="boom")

    _trigger_retrain("{}", "http://orchestration-api.test")

    mock_exit.assert_called_once_with(1)
