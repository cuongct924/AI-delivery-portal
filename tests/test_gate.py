"""services/orchestration-api/evaluations/gate.py — pure logic, no external
dependency (dataclasses), runs right away with nothing extra to install."""

from evaluations.gate import (
    GateThresholds,
    MetricsGateThresholds,
    evaluate_gate,
    evaluate_metrics_gate,
)


def test_evaluate_gate_passes_when_all_thresholds_met():
    judge_result = {"safety": 9, "correctness": 8, "relevance": 8}
    result = evaluate_gate(judge_result)
    assert result["passed"] is True


def test_evaluate_gate_fails_when_safety_below_threshold():
    judge_result = {"safety": 5, "correctness": 9, "relevance": 9}
    result = evaluate_gate(judge_result)
    assert result["passed"] is False


def test_evaluate_gate_respects_custom_thresholds():
    judge_result = {"safety": 6, "correctness": 6, "relevance": 6}
    thresholds = GateThresholds(min_safety=5, min_correctness=5, min_relevance=5)
    result = evaluate_gate(judge_result, thresholds)
    assert result["passed"] is True


def test_evaluate_metrics_gate_passes_when_all_thresholds_met():
    metrics = {"accuracy": 0.9, "precision": 0.8, "recall": 0.8}
    result = evaluate_metrics_gate(metrics)
    assert result["passed"] is True


def test_evaluate_metrics_gate_fails_when_accuracy_below_threshold():
    metrics = {"accuracy": 0.4, "precision": 0.9, "recall": 0.9}
    result = evaluate_metrics_gate(metrics)
    assert result["passed"] is False


def test_evaluate_metrics_gate_respects_custom_thresholds():
    metrics = {"accuracy": 0.5, "precision": 0.5, "recall": 0.5}
    thresholds = MetricsGateThresholds(min_accuracy=0.5, min_precision=0.5, min_recall=0.5)
    result = evaluate_metrics_gate(metrics, thresholds)
    assert result["passed"] is True
