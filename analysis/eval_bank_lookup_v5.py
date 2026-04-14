"""Evaluate the bank_lookup_v5 cheatsheet rules deterministically on the full
ETP matrix and on the hard3 validation slice.

Runs *only* the rules that bank_lookup_v5.txt instructs an LLM to apply, in
the same cascade order, using the exact magmas specified in the cheatsheet
(no magma-bank approximation). Rules that are part of the larger cascade_v14
but not in the cheatsheet (D6, D7*, MAGMA_const_one, the sound D9/D9b/D9bS/
D9bSS variants) are intentionally not fired here — they route to DEFAULT.

Rule mapping (bank_lookup_v5 family name → underlying predicate):
  T1  → D1                          (v13 rule)
  T2  → D2                          (v13 rule)
  T3  → D3, D4, D4d                 (v13 rules)
  L1  → LEFT PROJECTION magma  T[a,b]=a on {0,1}
  L2  → RIGHT PROJECTION magma T[a,b]=b on {0,1}
  L3  → CONSTANT ZERO magma    T[a,b]=0 on {0,1}
  M1  → XOR on {0,1}           T[a,b]=(a+b)%2
  M2  → LEFT-CYCLE on {0,1,2}  T[a,b]=(a+1)%3
  M3  → RIGHT-CYCLE on {0,1,2} T[a,b]=(b+1)%3
  M4  → SPIKE-ZERO on {0,1,2}  T[0,1]=2, else 0
  M5  → AND/MIN on {0,1}       T[a,b]=min(a,b)
  M6  → LEFT NEGATION on {0,1} T[a,b]=1-a
  M7  → RIGHT NEGATION on {0,1} T[a,b]=1-b
  D8  → D8, D8b                     (v13 rules)
  D10 → D10s1, D10s2                (v13 rules)
  D9  → D9old                       (heuristic)
  D5  → D5, D5c, D5d, D5e           (v13 rules)
  D5b → D5b                         (v13 rule)
  DEFAULT → TRUE

Output:
  data/magma_mining/eval_bank_lookup_v5_report.json
  printed per-rule table + aggregate sound / heuristic / overall coverage.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))

from parse_equation import parse_all_equations  # noqa: E402
from procedural_v2_checker import compute_features, decide_features_v13  # noqa: E402
from magma_counterexamples import compile_equation, satisfaction_vector  # noqa: E402

OUT = ROOT / "data/magma_mining"

# Explicit op tables for each cheatsheet magma.
V5_MAGMAS = {
    "L1": np.array([[0, 0], [1, 1]], dtype=np.int8),                  # a◇b=a
    "L2": np.array([[0, 1], [0, 1]], dtype=np.int8),                  # a◇b=b
    "L3": np.array([[0, 0], [0, 0]], dtype=np.int8),                  # a◇b=0
    "M1": np.array([[0, 1], [1, 0]], dtype=np.int8),                  # XOR
    "M2": np.array([[1, 1, 1], [2, 2, 2], [0, 0, 0]], dtype=np.int8), # (a+1)%3
    "M3": np.array([[1, 2, 0], [1, 2, 0], [1, 2, 0]], dtype=np.int8), # (b+1)%3
    "M4": np.array([[0, 2, 0], [0, 0, 0], [0, 0, 0]], dtype=np.int8), # spike-0
    "M5": np.array([[0, 0], [0, 1]], dtype=np.int8),                  # min
    "M6": np.array([[1, 1], [0, 0]], dtype=np.int8),                  # 1-a
    "M7": np.array([[1, 0], [1, 0]], dtype=np.int8),                  # 1-b
}
MAGMA_ORDER = ["L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]

V13_TO_V5_TRUE = {
    "D1": "T1", "D2": "T2",
    "D3": "T3", "D4": "T3", "D4d": "T3",
    "D5": "D5", "D5c": "D5", "D5d": "D5", "D5e": "D5",
    "D5b": "D5b",
    "D9old": "D9",
}
V13_TO_V5_FALSE = {
    "D8": "D8", "D8b": "D8",
    "D10s1": "D10", "D10s2": "D10",
}

# Cheatsheet cascade order (first match wins).
V5_RULE_ORDER = [
    "T1", "T2", "T3",
    "L1", "L2", "L3",
    "M1", "M2", "M3", "M4", "M5", "M6", "M7",
    "D8", "D10",
    "D9",                 # heuristic TRUE (per cheatsheet, before D5/D5b)
    "D5", "D5b",
    "DEFAULT",
]

V5_TRUE_RULES  = {"T1", "T2", "T3", "D5", "D5b", "D9", "DEFAULT"}
V5_FALSE_RULES = {"L1", "L2", "L3",
                  "M1", "M2", "M3", "M4", "M5", "M6", "M7",
                  "D8", "D10"}

V5_SOUND_RULES = [r for r in V5_RULE_ORDER if r not in ("D9", "DEFAULT")]


def classify_pair(magma_hits, v13_rule, v13_ans):
    """Return the v5 family name that claims this pair."""
    # T1, T2, T3 — sound TRUE rules from v13
    if v13_ans is True and v13_rule in ("D1", "D2", "D3", "D4", "D4d"):
        return V13_TO_V5_TRUE[v13_rule]
    # L1, L2, L3, M1..M7 — magma witnesses, checked in cheatsheet order
    for name in MAGMA_ORDER:
        if magma_hits.get(name):
            return name
    # D8, D10 — sound FALSE from v13
    if v13_ans is False and v13_rule in V13_TO_V5_FALSE:
        return V13_TO_V5_FALSE[v13_rule]
    # D9 heuristic TRUE
    if v13_rule == "D9old":
        return "D9"
    # D5, D5b (after D9 per cheatsheet)
    if v13_ans is True and v13_rule in ("D5", "D5c", "D5d", "D5e"):
        return "D5"
    if v13_ans is True and v13_rule == "D5b":
        return "D5b"
    return "DEFAULT"


def build_magma_mask(sat_row_a, sat_row_b):
    """Pair (i, j) refuted by magma iff Eq_i satisfies and Eq_j doesn't."""
    return sat_row_a[:, None] & ~sat_row_b[None, :]


def main():
    print("Loading equations + features...", flush=True)
    eqs_raw = parse_all_equations(str(ROOT / "data/equations.txt"))
    raw = [e["raw"] for e in eqs_raw]
    feats = [compute_features(r) for r in raw]
    n_eq = len(eqs_raw)
    print(f"  {n_eq} equations", flush=True)

    # Compile equations once for magma satisfaction checking.
    print("Compiling equations for magma evaluation...", flush=True)
    t_compile = time.time()
    compiled = [compile_equation(e["lhs"], e["rhs"]) for e in eqs_raw]
    print(f"  done in {time.time()-t_compile:.1f}s", flush=True)

    # Compute sat vectors for each v5 magma.
    print("Evaluating bank_lookup_v5 magmas...", flush=True)
    sat_vecs = {}
    for name in MAGMA_ORDER:
        t0 = time.time()
        sat_vecs[name] = satisfaction_vector(V5_MAGMAS[name], compiled)
        print(f"  {name} ({V5_MAGMAS[name].shape[0]}-elem): "
              f"{sat_vecs[name].sum():,} equations satisfy "
              f"({time.time()-t0:.1f}s)", flush=True)

    print("Loading gold...", flush=True)
    gold = np.load(ROOT / "data/outcomes_bool.npy").astype(bool)
    diag = np.eye(n_eq, dtype=bool)
    valid = ~diag

    # Per-magma (N, N) pair refutation masks (boolean).
    print("Building per-magma pair masks...", flush=True)
    magma_masks = {}
    for name in MAGMA_ORDER:
        magma_masks[name] = build_magma_mask(sat_vecs[name], sat_vecs[name])
        print(f"  {name}: {magma_masks[name].sum():,} pairs", flush=True)

    fires = {r: 0 for r in V5_RULE_ORDER}
    correct = {r: 0 for r in V5_RULE_ORDER}

    print("\nRunning bank_lookup_v5 cascade on full ETP matrix...", flush=True)
    t0 = time.time()
    for i in range(n_eq):
        f1 = feats[i]
        gold_row = gold[i]
        valid_row = valid[i]
        row_magmas = {name: magma_masks[name][i] for name in MAGMA_ORDER}

        for j in range(n_eq):
            if not valid_row[j]:
                continue
            magma_hits = {name: bool(row_magmas[name][j]) for name in MAGMA_ORDER}
            if any(magma_hits.values()):
                chosen = classify_pair(magma_hits, "__none__", None)
            else:
                v13_rule, v13_ans = decide_features_v13(f1, feats[j])
                chosen = classify_pair(magma_hits, v13_rule, v13_ans)
            fires[chosen] += 1
            pred = chosen in V5_TRUE_RULES
            if pred == bool(gold_row[j]):
                correct[chosen] += 1
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{n_eq} rows, {time.time()-t0:.0f}s", flush=True)

    total_pairs = n_eq * (n_eq - 1)
    print(f"\nDone in {time.time()-t0:.0f}s. Total pairs={total_pairs:,}",
          flush=True)

    # ---- per-rule table ----
    print("\n=== bank_lookup_v5: per-rule firing on full ETP ===", flush=True)
    print(f"{'rule':<10} {'fires':>12} {'%pairs':>8} {'correct':>12} "
          f"{'precision':>10}", flush=True)
    rows = []
    for r in V5_RULE_ORDER:
        f = fires[r]
        c = correct[r]
        p = c / f if f else float("nan")
        print(f"{r:<10} {f:>12,} {f/total_pairs:>7.2%} {c:>12,} {p:>10.4f}",
              flush=True)
        rows.append({"rule": r, "fires": f, "correct": c, "precision": p})

    # ---- aggregate summary ----
    sound_fires   = sum(fires[r]   for r in V5_SOUND_RULES)
    sound_correct = sum(correct[r] for r in V5_SOUND_RULES)
    heur_fires    = fires["D9"]
    heur_correct  = correct["D9"]
    default_fires = fires["DEFAULT"]
    default_correct = correct["DEFAULT"]
    all_fires     = sound_fires + heur_fires + default_fires
    all_correct   = sound_correct + heur_correct + default_correct

    def pct(n, d): return f"{n/d:.4%}" if d else "n/a"

    print("\n=== bank_lookup_v5 aggregate on full ETP ===", flush=True)
    print(f"  Sound rules only (T1..D10, ex-D9 heuristic):")
    print(f"    coverage:  {sound_fires:>14,} / {total_pairs:,} = "
          f"{pct(sound_fires, total_pairs)}")
    print(f"    precision: {sound_correct:>14,} / {sound_fires:,} = "
          f"{pct(sound_correct, sound_fires)}")
    print(f"  Sound + D9 heuristic:")
    print(f"    coverage:  {sound_fires+heur_fires:>14,} = "
          f"{pct(sound_fires+heur_fires, total_pairs)}")
    print(f"    precision: "
          f"{pct(sound_correct+heur_correct, sound_fires+heur_fires)}")
    print(f"  DEFAULT bucket (v5 predicts TRUE):")
    print(f"    coverage:  {default_fires:>14,} = "
          f"{pct(default_fires, total_pairs)}")
    print(f"    accuracy:  {pct(default_correct, default_fires)}")
    print(f"  Overall accuracy: "
          f"{pct(all_correct, all_fires)} ({all_correct:,}/{all_fires:,})")

    # ---- validation set breakdown ----
    print("\n=== bank_lookup_v5 on validation set ===", flush=True)
    problems = json.load(open(ROOT / "data/validation/problems.json"))
    answers  = json.load(open(ROOT / "data/validation/answers.json"))
    val_fires   = defaultdict(lambda: defaultdict(int))
    val_correct = defaultdict(lambda: defaultdict(int))
    val_totals  = defaultdict(int)

    for p in problems:
        i = p["eq1_id"] - 1
        j = p["eq2_id"] - 1
        gt = answers[p["id"]]
        diff = p["difficulty"]
        val_totals[diff] += 1
        f1 = feats[i]; f2 = feats[j]
        magma_hits = {name: bool(magma_masks[name][i, j]) for name in MAGMA_ORDER}
        if any(magma_hits.values()):
            chosen = classify_pair(magma_hits, "__none__", None)
        else:
            v13_rule, v13_ans = decide_features_v13(f1, f2)
            chosen = classify_pair(magma_hits, v13_rule, v13_ans)
        val_fires[diff][chosen] += 1
        pred = chosen in V5_TRUE_RULES
        if pred == gt:
            val_correct[diff][chosen] += 1

    val_summary = {}
    for diff in sorted(val_totals):
        n = val_totals[diff]
        print(f"\n--- {diff} (n={n}) ---", flush=True)
        print(f"{'rule':<10} {'fires':>6} {'correct':>8} {'prec':>8}",
              flush=True)
        diff_correct = 0
        drows = []
        for r in V5_RULE_ORDER:
            f = val_fires[diff].get(r, 0)
            if f == 0:
                continue
            c = val_correct[diff].get(r, 0)
            print(f"{r:<10} {f:>6} {c:>8} {c/f:>8.3f}", flush=True)
            diff_correct += c
            drows.append({"rule": r, "fires": f, "correct": c,
                          "precision": c / f})
        sound_f = sum(val_fires[diff].get(r, 0) for r in V5_SOUND_RULES)
        sound_c = sum(val_correct[diff].get(r, 0) for r in V5_SOUND_RULES)
        heur_f = val_fires[diff].get("D9", 0)
        print(f"  sound coverage:     {sound_f}/{n} = {pct(sound_f, n)}  "
              f"precision: {pct(sound_c, sound_f)}")
        print(f"  sound + D9 heur:    {sound_f+heur_f}/{n} = "
              f"{pct(sound_f+heur_f, n)}")
        print(f"  overall accuracy:   {diff_correct}/{n} = "
              f"{pct(diff_correct, n)}")
        val_summary[diff] = {"n": n,
                             "accuracy": diff_correct / n,
                             "sound_coverage": sound_f / n,
                             "sound_precision": (sound_c / sound_f)
                                                 if sound_f else None,
                             "rows": drows}

    report = {
        "etp": {"total_pairs": total_pairs,
                "rules": rows,
                "sound_coverage": sound_fires / total_pairs,
                "sound_precision": (sound_correct / sound_fires)
                                     if sound_fires else None,
                "heuristic_coverage": heur_fires / total_pairs,
                "heuristic_precision": (heur_correct / heur_fires)
                                        if heur_fires else None,
                "default_coverage": default_fires / total_pairs,
                "default_accuracy": (default_correct / default_fires)
                                     if default_fires else None,
                "overall_accuracy": all_correct / all_fires},
        "validation": val_summary,
        "rule_order": V5_RULE_ORDER,
    }
    json.dump(report, open(OUT / "eval_bank_lookup_v5_report.json", "w"),
              indent=2, default=float)
    print(f"\nsaved {OUT / 'eval_bank_lookup_v5_report.json'}", flush=True)


if __name__ == "__main__":
    main()
