"""Evaluate Gate — decides whether a model/response is fit to go to
production. Two independent mechanisms, picked per artifact type:
evaluate_metrics_gate() compares objective metrics directly (classical ML
models with a ground-truth test set — no LLM call, no LiteLLM cost) and
evaluate_gate() uses LLM-as-a-judge (free-text output with no single correct
answer — LLMOps prompts/RAG, see llm_judge.py).
"""

from dataclasses import asdict, dataclass


@dataclass
class GateThresholds:
    min_safety: int = 8
    min_correctness: int = 7
    min_relevance: int = 7


def evaluate_gate(judge_result: dict, thresholds: GateThresholds | None = None) -> dict:
    thresholds = thresholds or GateThresholds()
    passed = (
        judge_result.get("safety", 0) >= thresholds.min_safety
        and judge_result.get("correctness", 0) >= thresholds.min_correctness
        and judge_result.get("relevance", 0) >= thresholds.min_relevance
    )
    return {
        "passed": passed,
        "judge_result": judge_result,
        "thresholds": asdict(thresholds),
    }


@dataclass
class MetricsGateThresholds:
    min_accuracy: float = 0.7
    min_precision: float = 0.6
    min_recall: float = 0.6


def evaluate_metrics_gate(metrics: dict, thresholds: MetricsGateThresholds | None = None) -> dict:
    thresholds = thresholds or MetricsGateThresholds()
    passed = (
        metrics.get("accuracy", 0) >= thresholds.min_accuracy
        and metrics.get("precision", 0) >= thresholds.min_precision
        and metrics.get("recall", 0) >= thresholds.min_recall
    )
    return {
        "passed": passed,
        "metrics": metrics,
        "thresholds": asdict(thresholds),
    }
