"""Format and save evaluation results."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import RunConfig
from .metrics import Metrics, ProblemResult


def _result_dict(r: ProblemResult, hide_answers: bool = False) -> dict:
    """Build a dict for one result, optionally hiding gold answers."""
    d = {
        "problem_id": r.problem_id,
        "equation1": r.equation1,
        "equation2": r.equation2,
        "predicted_answer": r.predicted_answer,
        "parse_method": r.parse_method,
        "raw_response": r.raw_response,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "cost_usd": r.cost_usd,
        "latency_s": r.latency_s,
        "error": r.error,
    }
    if not hide_answers:
        d["gold_answer"] = r.gold_answer
        d["correct"] = r.correct
    return d


def print_metrics(metrics: Metrics) -> None:
    """Print metrics table to terminal."""
    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Total problems:       {metrics.total}")
    print(f"  Parsed:               {metrics.parsed}")
    print(f"  Unparsed:             {metrics.unparsed}")
    print("-" * 60)
    print(f"  Raw Accuracy:         {metrics.raw_accuracy:.4f}")
    print(f"  Effective Accuracy:   {metrics.effective_accuracy:.4f}")
    print(f"  F1 Score:             {metrics.f1:.4f}")
    print(f"  Bias:                 {metrics.bias:+.4f}")
    print(f"  Parse Success Rate:   {metrics.parse_rate:.4f}")
    print("-" * 60)
    print(f"  Confusion Matrix:")
    print(f"    TP={metrics.tp}  FP={metrics.fp}")
    print(f"    FN={metrics.fn}  TN={metrics.tn}")
    print(f"    Unparsed={metrics.unparsed}")
    print("-" * 60)
    print(f"  Total Cost:           ${metrics.total_cost:.4f}")
    print(f"  Cost per Correct:     ${metrics.cost_per_correct:.4f}")
    print(f"  Total Tokens:         {metrics.total_tokens}")
    print(f"  Avg Time:             {metrics.avg_time_s:.2f}s")
    print(f"  Effective Avg Time:   {metrics.effective_avg_time_s:.2f}s")
    print("=" * 60 + "\n")


def save_results(
    results: list[ProblemResult],
    metrics: Metrics,
    config: RunConfig,
    cheatsheet_path: str,
    cheatsheet_content: str,
    output_dir: Path,
    write_csv: bool = False,
    hide_answers: bool = False,
) -> Path:
    """Save full results to JSON (and optionally CSV)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    model_short = config.model.split("/")[-1]
    cs_name = Path(cheatsheet_path).stem
    base_name = f"{timestamp}_{model_short}_{cs_name}"

    cheatsheet_hash = hashlib.sha256(cheatsheet_content.encode()).hexdigest()[:16]

    data = {
        "run_id": base_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "concurrency": config.concurrency,
        },
        "cheatsheet_path": cheatsheet_path,
        "cheatsheet_hash": cheatsheet_hash,
        "cheatsheet_size_bytes": len(cheatsheet_content.encode()),
        "metrics": {
            "total": metrics.total,
            "parsed": metrics.parsed,
            "unparsed": metrics.unparsed,
            "tp": metrics.tp,
            "fp": metrics.fp,
            "fn": metrics.fn,
            "tn": metrics.tn,
            "raw_accuracy": metrics.raw_accuracy,
            "effective_accuracy": metrics.effective_accuracy,
            "f1": metrics.f1,
            "bias": metrics.bias,
            "parse_rate": metrics.parse_rate,
            "total_cost": metrics.total_cost,
            "cost_per_correct": metrics.cost_per_correct,
            "avg_time_s": metrics.avg_time_s,
            "effective_avg_time_s": metrics.effective_avg_time_s,
            "total_tokens": metrics.total_tokens,
        },
        "results": [
            _result_dict(r, hide_answers=hide_answers)
            for r in results
        ],
    }

    if hide_answers:
        data["problem_set"] = "validation"

    json_path = output_dir / f"{base_name}.json"
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    if write_csv:
        csv_path = output_dir / f"{base_name}.csv"
        fieldnames = [
            "problem_id", "equation1", "equation2",
            "predicted_answer", "parse_method",
            "prompt_tokens", "completion_tokens", "cost_usd", "latency_s",
        ]
        if not hide_answers:
            fieldnames.insert(3, "gold_answer")
            fieldnames.insert(5, "correct")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = {
                    "problem_id": r.problem_id,
                    "equation1": r.equation1,
                    "equation2": r.equation2,
                    "predicted_answer": r.predicted_answer,
                    "parse_method": r.parse_method,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "cost_usd": r.cost_usd,
                    "latency_s": r.latency_s,
                }
                if not hide_answers:
                    row["gold_answer"] = r.gold_answer
                    row["correct"] = r.correct
                writer.writerow(row)

    return json_path


def load_and_print_report(path: Path) -> None:
    """Load a saved result JSON and print its metrics."""
    with open(path) as f:
        data = json.load(f)

    m = data["metrics"]
    print(f"\nReport: {data['run_id']}")
    print(f"Model:  {data['config']['model']}")
    print(f"Time:   {data['timestamp']}")

    metrics = Metrics(
        total=m["total"], parsed=m["parsed"], unparsed=m["unparsed"],
        tp=m["tp"], fp=m["fp"], fn=m["fn"], tn=m["tn"],
        raw_accuracy=m["raw_accuracy"], effective_accuracy=m["effective_accuracy"],
        f1=m["f1"], bias=m["bias"], parse_rate=m["parse_rate"],
        total_cost=m["total_cost"], cost_per_correct=m["cost_per_correct"],
        avg_time_s=m["avg_time_s"], effective_avg_time_s=m["effective_avg_time_s"],
        total_tokens=m["total_tokens"],
    )
    print_metrics(metrics)
