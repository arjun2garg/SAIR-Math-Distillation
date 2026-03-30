"""Load and filter problem sets for equational theory evaluation."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Problem:
    id: str
    equation1: str
    equation2: str
    answer: bool | None = None  # True = implication holds, False = does not, None = hidden
    difficulty: str = "standard"


def load_equations(path: Path) -> dict[int, str]:
    """Load equations.txt — one equation per line, line number (1-indexed) is the ID."""
    equations = {}
    with open(path) as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                equations[i] = line
    return equations


def load_outcomes(path: Path) -> dict:
    """Load outcomes.json with 'equations' list and 'outcomes' matrix."""
    with open(path) as f:
        return json.load(f)


_TRUE_OUTCOMES = {"explicit_proof_true", "implicit_proof_true"}
_FALSE_OUTCOMES = {"explicit_proof_false", "implicit_proof_false"}


def generate_problems_from_etp(
    equations: dict[int, str],
    outcomes: dict,
    equation_ids: list[int] | None = None,
) -> list[Problem]:
    """Generate Problem objects from the ETP equations + outcomes matrix.

    If equation_ids is given, only generate pairs involving those equation IDs.
    Only includes problems with definitive (proven) outcomes.
    """
    eq_list = outcomes["equations"]  # ["Equation1", "Equation2", ...]
    matrix = outcomes["outcomes"]  # matrix[i][j] = outcome string

    if equation_ids is not None:
        id_set = set(equation_ids)
    else:
        id_set = None

    problems = []
    for i in range(len(eq_list)):
        eq1_id = i + 1
        if id_set is not None and eq1_id not in id_set:
            continue
        for j in range(len(eq_list)):
            if i == j:
                continue
            eq2_id = j + 1
            outcome = matrix[i][j]
            if outcome in _TRUE_OUTCOMES:
                answer = True
            elif outcome in _FALSE_OUTCOMES:
                answer = False
            else:
                continue

            if eq1_id not in equations or eq2_id not in equations:
                continue

            problems.append(Problem(
                id=f"{eq1_id}_{eq2_id}",
                equation1=equations[eq1_id],
                equation2=equations[eq2_id],
                answer=answer,
            ))

    return problems


def load_problems_json(path: Path) -> list[Problem]:
    """Load problems from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return [
        Problem(
            id=str(p["id"]),
            equation1=p["equation1"],
            equation2=p["equation2"],
            answer=_parse_bool(p["answer"]),
            difficulty=p.get("difficulty", "standard"),
        )
        for p in data
    ]


def load_problems_csv(path: Path) -> list[Problem]:
    """Load problems from a CSV file."""
    problems = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            problems.append(Problem(
                id=str(row["id"]),
                equation1=row["equation1"],
                equation2=row["equation2"],
                answer=_parse_bool(row["answer"]),
                difficulty=row.get("difficulty", "standard"),
            ))
    return problems


def load_problems(path: Path) -> list[Problem]:
    """Load problems from JSON or CSV based on file extension."""
    if path.suffix == ".json":
        return load_problems_json(path)
    elif path.suffix == ".csv":
        return load_problems_csv(path)
    else:
        raise ValueError(f"Unsupported problem file format: {path.suffix}")


def select_problems(
    problems: list[Problem],
    indices: list[int] | None = None,
    sample_n: int | None = None,
    difficulty: str | None = None,
    seed: int | None = None,
) -> list[Problem]:
    """Filter and sample problems."""
    result = problems

    if difficulty:
        result = [p for p in result if p.difficulty == difficulty]

    if indices is not None:
        result = [result[i] for i in indices if i < len(result)]

    if sample_n is not None and sample_n < len(result):
        rng = random.Random(seed)
        result = rng.sample(result, sample_n)

    return result


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    raise ValueError(f"Cannot parse as boolean: {value!r}")
