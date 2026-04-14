"""Evaluate procedural_v2_checker (v0 vs v1) on three datasets:
  1. Full Lean implication graph (data/outcomes.json + data/equations.txt)
  2. Validation set (data/validation/{problems,answers}.json)
  3. Community benchmark (data/community_bench.json)

Reports accuracy, rule-firing distribution, and v0→v1 flip stats for each.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from procedural_v2_checker import (  # noqa: E402
    compute_features,
    decide_features,
    decide_features_v0,
    decide_features_v2,
    decide_features_v4,
    decide_features_v5,
    decide_features_v6,
)

REPO = Path(__file__).resolve().parent.parent

# A label is "true" if it ends with "_true". Conjectures (~186) excluded.
TRUE_LABELS = {"implicit_proof_true", "explicit_proof_true"}
FALSE_LABELS = {"implicit_proof_false", "explicit_proof_false"}


def evaluate(name: str, pairs):
    """pairs: iterable of (eq1, eq2, gold_bool). Returns summary dict."""
    t0 = time.time()
    feats_cache: dict[str, dict] = {}

    def feats(eq):
        f = feats_cache.get(eq)
        if f is None:
            f = compute_features(eq)
            feats_cache[eq] = f
        return f

    n = 0
    parse_err = 0
    v0_correct = 0
    v1_correct = 0
    v2_correct = 0
    v4_correct = 0
    v4_rules: Counter[str] = Counter()
    v4_rule_correct: Counter[str] = Counter()
    v5_correct = 0
    v5_rules: Counter[str] = Counter()
    v5_rule_correct: Counter[str] = Counter()
    v6_correct = 0
    v6_rules: Counter[str] = Counter()
    v6_rule_correct: Counter[str] = Counter()
    v0_rules: Counter[str] = Counter()
    v1_rules: Counter[str] = Counter()
    flips_to_correct = 0
    flips_to_wrong = 0
    # Per-rule correctness for v1
    v1_rule_correct: Counter[str] = Counter()

    for eq1, eq2, gold in pairs:
        try:
            f1 = feats(eq1)
            f2 = feats(eq2)
            v0_rule, v0_ans = decide_features_v0(f1, f2)
            v1_rule, v1_ans = decide_features(f1, f2)
            _, v2_ans = decide_features_v2(f1, f2)
            v4_rule, v4_ans = decide_features_v4(f1, f2)
            v5_rule, v5_ans = decide_features_v5(f1, f2)
            v6_rule, v6_ans = decide_features_v6(f1, f2)
        except Exception:
            parse_err += 1
            continue
        n += 1
        v0_rules[v0_rule] += 1
        v1_rules[v1_rule] += 1
        if v0_ans == gold:
            v0_correct += 1
        if v1_ans == gold:
            v1_correct += 1
            v1_rule_correct[v1_rule] += 1
        if v2_ans == gold:
            v2_correct += 1
        v4_rules[v4_rule] += 1
        if v4_ans == gold:
            v4_correct += 1
            v4_rule_correct[v4_rule] += 1
        v5_rules[v5_rule] += 1
        if v5_ans == gold:
            v5_correct += 1
            v5_rule_correct[v5_rule] += 1
        v6_rules[v6_rule] += 1
        if v6_ans == gold:
            v6_correct += 1
            v6_rule_correct[v6_rule] += 1
        if v0_ans != v1_ans:
            if v1_ans == gold:
                flips_to_correct += 1
            else:
                flips_to_wrong += 1

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}\n{name}  ({n} pairs, {parse_err} parse errors, {elapsed:.1f}s)")
    print(f"  v0 accuracy            : {v0_correct}/{n} = {v0_correct / n:.4f}")
    print(f"  v1 accuracy (full)     : {v1_correct}/{n} = {v1_correct / n:.4f}")
    print(f"  v2 accuracy (sound only): {v2_correct}/{n} = {v2_correct / n:.4f}")
    print(f"  v4 accuracy (v2 + old D9): {v4_correct}/{n} = {v4_correct / n:.4f}")
    print("  v4 per-rule:")
    for r in sorted(v4_rules):
        tot = v4_rules[r]; ok = v4_rule_correct[r]
        print(f"    {r:6s}: fired {tot:>9d}   correct {ok:>9d}  ({ok / tot:.4f})")
    print(f"  v5 accuracy (v2 + D9bS + old D9): {v5_correct}/{n} = {v5_correct / n:.4f}")
    print(f"  v6 accuracy (v2 + D9bSS + old D9): {v6_correct}/{n} = {v6_correct / n:.4f}")
    print("  v5 / v6 contributing rules:")
    for r in ("D9bS", "D9bSS", "D9old"):
        for tag, rules, rcorr in (("v5", v5_rules, v5_rule_correct), ("v6", v6_rules, v6_rule_correct)):
            if rules.get(r):
                tot = rules[r]; ok = rcorr[r]
                print(f"    [{tag}] {r:6s}: {tot:>8d}   correct {ok:>8d}  ({ok / tot:.3f})")
    print(f"  Δ correct  : {v1_correct - v0_correct:+d}")
    print(f"  Flips v0→v1: {flips_to_correct + flips_to_wrong}  "
          f"(→correct {flips_to_correct}, →wrong {flips_to_wrong})")
    print(f"  v1 rule firing distribution (rule: fired, of which correct):")
    for r in sorted(v1_rules):
        fired = v1_rules[r]
        ok = v1_rule_correct[r]
        print(f"    {r:5s}: {fired:>8d}   correct {ok:>8d}  ({ok / fired:.3f})")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_full_lean():
    eqs = [line.strip() for line in (REPO / "data/equations.txt").read_text().splitlines() if line.strip()]
    data = json.loads((REPO / "data/outcomes.json").read_text())
    outcomes = data["outcomes"]
    assert len(outcomes) == len(eqs)
    n = len(eqs)
    for i in range(n):
        row = outcomes[i]
        for j in range(n):
            v = row[j]
            if v in TRUE_LABELS:
                yield eqs[i], eqs[j], True
            elif v in FALSE_LABELS:
                yield eqs[i], eqs[j], False
            # else: conjecture/unknown — skip


def load_validation():
    problems = json.loads((REPO / "data/validation/problems.json").read_text())
    answers = json.loads((REPO / "data/validation/answers.json").read_text())
    for p in problems:
        yield p["equation1"], p["equation2"], bool(answers[p["id"]])


def load_community():
    data = json.loads((REPO / "data/community_bench.json").read_text())
    for p in data:
        yield p["equation1"], p["equation2"], bool(p["answer"])


if __name__ == "__main__":
    evaluate("Community benchmark (200)", load_community())
    evaluate("Validation set (1669)", load_validation())
    evaluate("Full Lean implication graph (~22M)", load_full_lean())
