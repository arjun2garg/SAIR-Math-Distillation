"""Download and manage training/validation datasets."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .problems import Problem, generate_problems_from_etp

HF_API_BASE = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=SAIRfoundation/equational-theories-selected-problems"
)

VALIDATION_CONFIGS = {
    "normal": 1000,
    "hard1": 69,
    "hard2": 200,
    "hard3": 400,
}

TRAINING_HF_CONFIGS = {
    "hard": 200,
}


def _fetch_hf_rows(config: str, total: int) -> list[dict]:
    """Fetch all rows from the HuggingFace datasets-server API, paginating as needed."""
    all_rows = []
    page_size = 100  # API max per request
    offset = 0
    while offset < total:
        length = min(page_size, total - offset)
        url = f"{HF_API_BASE}&config={config}&split=train&offset={offset}&length={length}"
        req = Request(url, headers={"User-Agent": "eq-playground/1.0"})
        with urlopen(req) as resp:
            data = json.loads(resp.read())
        rows = [row["row"] for row in data["rows"]]
        all_rows.extend(rows)
        if len(rows) < length:
            break  # No more data
        offset += length
    return all_rows


def download_validation(data_dir: Path) -> dict:
    """Download validation set from HuggingFace and split into problems + answers.

    Returns manifest dict with counts per config.
    """
    val_dir = data_dir / "validation"
    val_dir.mkdir(parents=True, exist_ok=True)

    problems = []
    answers = {}
    counts = {}

    for config, expected_len in VALIDATION_CONFIGS.items():
        rows = _fetch_hf_rows(config, expected_len)
        counts[config] = len(rows)

        for row in rows:
            pid = str(row["id"])
            problems.append({
                "id": pid,
                "eq1_id": row["eq1_id"],
                "eq2_id": row["eq2_id"],
                "equation1": row["equation1"],
                "equation2": row["equation2"],
                "difficulty": config,
            })
            answers[pid] = row["answer"]

    # Write problems WITHOUT answers
    with open(val_dir / "problems.json", "w") as f:
        json.dump(problems, f, indent=2)

    # Write answers separately
    with open(val_dir / "answers.json", "w") as f:
        json.dump(answers, f, indent=2)

    # Write manifest
    manifest = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "configs": counts,
        "total_problems": len(problems),
    }
    with open(val_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def download_training(
    data_dir: Path,
    equations: dict[int, str],
    outcomes: dict,
    sample_n: int = 5000,
    seed: int = 42,
) -> int:
    """Download training set: HF 'hard' config + sampled ETP problems.

    Returns the total number of training problems generated.
    """
    train_dir = data_dir / "training"
    train_dir.mkdir(parents=True, exist_ok=True)

    # Collect all HF equation pairs to exclude (validation + training HF)
    all_hf_pairs: set[tuple[int, int]] = set()
    hf_problems: list[dict] = []

    # Load validation pairs to exclude
    val_problems_path = data_dir / "validation" / "problems.json"
    if val_problems_path.exists():
        with open(val_problems_path) as f:
            val_data = json.load(f)
        for p in val_data:
            all_hf_pairs.add((p["eq1_id"], p["eq2_id"]))

    # Download HF 'hard' config for training, excluding any that overlap with validation
    val_pairs = set(all_hf_pairs)  # snapshot before adding training pairs
    for config, expected_len in TRAINING_HF_CONFIGS.items():
        rows = _fetch_hf_rows(config, expected_len)
        for row in rows:
            pair = (row["eq1_id"], row["eq2_id"])
            if pair in val_pairs:
                continue  # skip problems that overlap with validation
            all_hf_pairs.add(pair)
            hf_problems.append({
                "id": str(row["id"]),
                "eq1_id": row["eq1_id"],
                "eq2_id": row["eq2_id"],
                "equation1": row["equation1"],
                "equation2": row["equation2"],
                "answer": row["answer"],
                "difficulty": config,
            })

    # Generate ETP problems, excluding all HF pairs
    etp_problems = generate_problems_from_etp(equations, outcomes)
    etp_filtered = [
        p for p in etp_problems
        if _problem_pair(p) not in all_hf_pairs
    ]

    # Sample from ETP to fill remaining slots
    remaining = max(0, sample_n - len(hf_problems))
    rng = random.Random(seed)
    if remaining < len(etp_filtered):
        etp_sampled = rng.sample(etp_filtered, remaining)
    else:
        etp_sampled = etp_filtered

    # Combine HF + ETP samples
    training_data = list(hf_problems)
    for p in etp_sampled:
        eq1_id, eq2_id = _problem_pair(p)
        training_data.append({
            "id": p.id,
            "eq1_id": eq1_id,
            "eq2_id": eq2_id,
            "equation1": p.equation1,
            "equation2": p.equation2,
            "answer": p.answer,
            "difficulty": p.difficulty,
        })

    # Shuffle for good measure
    rng.shuffle(training_data)

    with open(train_dir / "problems.json", "w") as f:
        json.dump(training_data, f, indent=2)

    return len(training_data)


def load_validation_problems(data_dir: Path) -> list[Problem]:
    """Load validation problems WITH answers (for scoring)."""
    val_dir = data_dir / "validation"
    with open(val_dir / "problems.json") as f:
        problems_data = json.load(f)

    answers_path = val_dir / "answers.json"
    if answers_path.exists():
        with open(answers_path) as f:
            answers = json.load(f)
    else:
        answers = {}

    result = []
    for p in problems_data:
        pid = p["id"]
        answer = answers.get(pid)  # None if answers file missing
        result.append(Problem(
            id=pid,
            equation1=p["equation1"],
            equation2=p["equation2"],
            answer=answer,
            difficulty=p.get("difficulty", "standard"),
        ))
    return result


def load_training_problems(data_dir: Path) -> list[Problem]:
    """Load training problems (always includes answers)."""
    with open(data_dir / "training" / "problems.json") as f:
        data = json.load(f)
    return [
        Problem(
            id=str(p["id"]),
            equation1=p["equation1"],
            equation2=p["equation2"],
            answer=p["answer"],
            difficulty=p.get("difficulty", "standard"),
        )
        for p in data
    ]


def _problem_pair(p: Problem) -> tuple[int, int]:
    """Extract (eq1_id, eq2_id) from a Problem ID like '179_3877'."""
    parts = p.id.split("_")
    return (int(parts[0]), int(parts[1]))
