"""Compute evaluation metrics from problem results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProblemResult:
    problem_id: str
    equation1: str
    equation2: str
    gold_answer: bool | None
    predicted_answer: bool | None
    correct: bool | None
    parse_method: str
    raw_response: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    error: str | None = None


@dataclass
class Metrics:
    total: int = 0
    parsed: int = 0
    unparsed: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    raw_accuracy: float = 0.0
    effective_accuracy: float = 0.0
    f1: float = 0.0
    bias: float = 0.0
    parse_rate: float = 0.0
    total_cost: float = 0.0
    cost_per_correct: float = 0.0
    avg_time_s: float = 0.0
    effective_avg_time_s: float = 0.0
    total_tokens: int = 0


def compute_metrics(results: list[ProblemResult]) -> Metrics:
    """Compute all evaluation metrics from a list of problem results."""
    if not results:
        return Metrics()

    m = Metrics()
    m.total = len(results)

    correct_count = 0
    parsed_times = []

    for r in results:
        m.total_cost += r.cost_usd
        m.total_tokens += r.prompt_tokens + r.completion_tokens
        m.avg_time_s += r.latency_s

        if r.predicted_answer is None:
            m.unparsed += 1
            # Unparsed with gold=TRUE counts as FN per challenge spec
            if r.gold_answer is True:
                m.fn += 1
            continue

        m.parsed += 1
        parsed_times.append(r.latency_s)

        # Skip accuracy/confusion matrix when gold answer is unknown
        if r.gold_answer is None:
            continue

        if r.gold_answer and r.predicted_answer:
            m.tp += 1
        elif not r.gold_answer and r.predicted_answer:
            m.fp += 1
        elif r.gold_answer and not r.predicted_answer:
            m.fn += 1
        else:
            m.tn += 1

        if r.correct:
            correct_count += 1

    # Raw accuracy: correct / total (unparsed counted as wrong)
    m.raw_accuracy = correct_count / m.total if m.total > 0 else 0.0

    # Effective accuracy: correct / parsed
    m.effective_accuracy = correct_count / m.parsed if m.parsed > 0 else 0.0

    # F1: 2*TP / (2*TP + FP + FN)
    denom = 2 * m.tp + m.fp + m.fn
    m.f1 = (2 * m.tp / denom) if denom > 0 else 0.0

    # Bias: predicted-TRUE rate minus actual-TRUE rate (on parsed samples)
    if m.parsed > 0:
        predicted_true_rate = (m.tp + m.fp) / m.parsed
        actual_true_rate = (m.tp + m.fn) / m.total  # fn includes unparsed gold=TRUE
        m.bias = predicted_true_rate - actual_true_rate
    else:
        m.bias = 0.0

    # Parse rate
    m.parse_rate = m.parsed / m.total if m.total > 0 else 0.0

    # Cost per correct
    m.cost_per_correct = m.total_cost / correct_count if correct_count > 0 else float("inf")

    # Avg time
    m.avg_time_s = m.avg_time_s / m.total if m.total > 0 else 0.0

    # Effective avg time (only parsed responses)
    m.effective_avg_time_s = (
        sum(parsed_times) / len(parsed_times) if parsed_times else 0.0
    )

    return m
