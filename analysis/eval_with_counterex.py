"""Stack the magma-counterexample REFUTED rule on top of v13 and re-evaluate.

Counterexample test:
  - Compile the input equation pair into satisfaction-check functions over
    each magma in our library.
  - If any magma satisfies eq1 but not eq2 -> sound FALSE.
  - Otherwise fall through to v13 cascade.

For canonical (4694) equations we use the precomputed sat matrix; for OOD
equations (e.g. parts of community_bench) we compile on-the-fly.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "analysis"))
from procedural_v2_checker import compute_features, decide_features_v13  # noqa: E402
from parse_equation import parse_equation  # noqa: E402
from magma_counterexamples import (  # noqa: E402
    compile_equation,
    structured_magmas,
    random_magmas,
    all_magmas_n,
)

import os
EQS_PATH = REPO / "data/equations.txt"
# Pre-built sound refutation matrix. Default to the pushed artifact (Phase 11).
REFUTED_PATH = Path(os.environ.get(
    "REFUTED_PATH", str(REPO / "data/magma_mining/refuted_pushed.npy")))


# ---------------------------------------------------------------------------
# Magma library — must mirror what build() in magma_counterexamples.py used
# ---------------------------------------------------------------------------

def build_magma_library():
    Ts = []
    for T in all_magmas_n(2):
        Ts.append(T)
    for _, T in structured_magmas(3):
        Ts.append(T)
    for T in random_magmas(3, 2000, seed=3):
        Ts.append(T)
    for _, T in structured_magmas(4):
        Ts.append(T)
    for T in random_magmas(4, 2000, seed=4):
        Ts.append(T)
    for _, T in structured_magmas(5):
        Ts.append(T)
    for T in random_magmas(5, 1000, seed=5):
        Ts.append(T)
    return Ts


# ---------------------------------------------------------------------------
# Compiled equation cache
# ---------------------------------------------------------------------------

class CounterexLookup:
    """Pure refutation-matrix lookup. No on-the-fly magma evaluation: if
    either equation is OOD (not in the canonical 4694 set) we just say
    'no information' and let the cascade fall through. This preserves
    soundness even though the underlying magma bank used to build the
    matrix is no longer reconstructible from code."""

    def __init__(self):
        self.R = np.load(REFUTED_PATH)  # (4694, 4694) bool
        eqs = [l.strip() for l in EQS_PATH.read_text().splitlines() if l.strip()]
        self.canon_idx: dict[str, int] = {}
        for i, e in enumerate(eqs):
            f = parse_equation(e)
            self.canon_idx[f["canonical"]] = i

    def refuted(self, eq1, p1, eq2, p2) -> bool:
        i = self.canon_idx.get(p1["canonical"])
        if i is None:
            return False
        j = self.canon_idx.get(p2["canonical"])
        if j is None:
            return False
        return bool(self.R[i, j])


# ---------------------------------------------------------------------------
# Stacked decider
# ---------------------------------------------------------------------------

def make_decider(ctx: CounterexLookup):
    def decide(eq1_str, eq2_str, p1, p2, f1, f2):
        if ctx.refuted(eq1_str, p1, eq2_str, p2):
            return "Dctx", False
        return decide_features_v13(f1, f2)
    return decide


# ---------------------------------------------------------------------------
# Eval driver
# ---------------------------------------------------------------------------

def evaluate(name, pairs, decide):
    parsed_cache: dict[str, tuple] = {}
    rules: Counter = Counter()
    rules_correct: Counter = Counter()
    n = 0
    correct = 0
    err = 0

    for eq1, eq2, gold in pairs:
        try:
            t1 = parsed_cache.get(eq1)
            if t1 is None:
                p = parse_equation(eq1)
                f = compute_features(eq1)
                parsed_cache[eq1] = (p, f)
                t1 = (p, f)
            t2 = parsed_cache.get(eq2)
            if t2 is None:
                p = parse_equation(eq2)
                f = compute_features(eq2)
                parsed_cache[eq2] = (p, f)
                t2 = (p, f)
            p1, f1 = t1
            p2, f2 = t2
            rule, ans = decide(eq1, eq2, p1, p2, f1, f2)
        except Exception as e:
            err += 1
            continue
        n += 1
        rules[rule] += 1
        if ans == gold:
            correct += 1
            rules_correct[rule] += 1

    print(f"\n=== {name}  ({n} pairs, {err} errors) ===")
    print(f"  accuracy: {correct}/{n} = {correct/n:.4f}")
    for r in sorted(rules):
        tot = rules[r]
        ok = rules_correct[r]
        print(f"    {r:8s}: fired {tot:>9d}   correct {ok:>9d}  ({ok/tot:.4f})")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_full_lean():
    eqs = [l.strip() for l in EQS_PATH.read_text().splitlines() if l.strip()]
    gold = np.load(REPO / "data/outcomes_bool.npy").astype(bool)
    n = len(eqs)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            yield eqs[i], eqs[j], bool(gold[i, j])


def load_validation():
    problems = json.loads((REPO / "data/validation/problems.json").read_text())
    answers = json.loads((REPO / "data/validation/answers.json").read_text())
    for p in problems:
        yield p["equation1"], p["equation2"], bool(answers[p["id"]])


def load_community():
    data = json.loads((REPO / "data/community_bench.json").read_text())
    for p in data:
        yield p["equation1"], p["equation2"], bool(p["answer"])


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Loading counterexample lookup ({REFUTED_PATH.name})…")
    t0 = time.time()
    ctx = CounterexLookup()
    print(f"  refuted={ctx.R.sum():,} pairs, {time.time()-t0:.1f}s")

    decide = make_decider(ctx)
    which = sys.argv[1] if len(sys.argv) > 1 else "small"

    if which in ("community", "small", "all"):
        evaluate("Community benchmark (200)", load_community(), decide)
    if which in ("validation", "small", "all"):
        evaluate("Validation set (1669)", load_validation(), decide)
    if which in ("lean", "all"):
        evaluate("Full Lean graph (~22M)", load_full_lean(), decide)
