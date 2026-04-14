"""Combined cascade: previous best (procedural v13) + magma counterexample
rules (decomposed by which magma fired) + extra simple rules.

For every pair (i, j) we run rules in cascade order. The first matching rule
wins; we record (rule_name, prediction). Then we report per-rule:
  - fires (count of pairs where this rule fired first)
  - correct (matches gold)
  - precision = correct / fires

Datasets:
  - full ETP outcomes matrix (~22M pairs, off-diagonal, with known label)
  - validation set, broken down by difficulty

Output:
  data/magma_mining/cascade_v14_report.json
  printed table to stdout
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

from analysis.parse_equation import parse_all_equations  # noqa: E402
from procedural_v2_checker import compute_features, decide_features_v13  # noqa: E402

OUT = ROOT / "data/magma_mining"

# 2-element magma indices in the prior_counterex bucket (verified above):
#   0  = constant-zero      a*b = 0
#   3  = left projection    a*b = a
#   5  = right projection   a*b = b
#   6  = XOR                a*b = a XOR b
#   12 = constant-one       a*b = 1
TOP_MAGMAS = {
    "MAGMA_const_zero":   0,
    "MAGMA_left_proj":    3,
    "MAGMA_right_proj":   5,
    "MAGMA_xor":          6,
    "MAGMA_const_one":   12,
}


def make_refuted(sat_row_a, sat_row_b):
    """Build a (N,N) bool refutation mask from a single magma's sat vector."""
    return sat_row_a[:, None] & ~sat_row_b[None, :]


def main():
    print("Loading equations + features...", flush=True)
    eqs = parse_all_equations(str(ROOT / "data/equations.txt"))
    raw = [e["raw"] for e in eqs]
    feats = [compute_features(r) for r in raw]
    n_eq = len(eqs)
    print(f"  {n_eq} equations", flush=True)

    print("Loading sat_merged_v2 + gold...", flush=True)
    sat = np.load(OUT / "sat_merged_v2.npy")  # (M, N) bool
    print(f"  sat {sat.shape}", flush=True)

    gold = np.load(ROOT / "data/outcomes_bool.npy").astype(bool)  # 1=TRUE
    diag = np.eye(n_eq, dtype=bool)
    valid = ~diag  # exclude self pairs

    # Per-magma refutation masks for the named top magmas
    print("Building per-magma refutation masks...", flush=True)
    magma_masks = {}
    for name, idx in TOP_MAGMAS.items():
        sv = sat[idx]
        magma_masks[name] = sv[:, None] & ~sv[None, :]
        print(f"  {name} (#{idx}): {magma_masks[name].sum():,} pairs",
              flush=True)

    # Full merged_v2 refutation matrix (load if cached, else compute)
    refuted_path = OUT / "refuted_merged_v2.npy"
    print("Loading refuted_merged_v2...", flush=True)
    R_full = np.load(refuted_path)
    print(f"  {R_full.sum():,} pairs", flush=True)

    # MAGMA_other = refuted by full library but NOT by any of the named top magmas
    print("Building MAGMA_other mask...", flush=True)
    union_top = np.zeros_like(R_full)
    for name, mask in magma_masks.items():
        union_top |= mask
    magma_masks["MAGMA_other_library"] = R_full & ~union_top
    print(f"  MAGMA_other_library: {magma_masks['MAGMA_other_library'].sum():,}",
          flush=True)

    # ------------------------------------------------------------------
    # The cascade.
    #
    # We process the matrix one row (Eq1) at a time. For each row we
    # precompute the v13 decision for every Eq2 (it depends only on i for
    # most rules but several check f2 too). To keep things vectorized we
    # split the cascade into two layers:
    #   1. v13 sound TRUE rules (D1..D5b, D5c/D5d/D5e, D9bS variants)
    #      These are checked per pair via the existing decide_features_v13.
    #      We tag the rule name as v13's choice.
    #   2. If v13 returned FALSE (D6, D7*, D8*, D9old, D10s*, D10) we *only*
    #      keep its TRUE-side answer; we override the FALSE-side with our
    #      magma cascade. The magma rule is sound, so it strictly dominates
    #      heuristic FALSE.
    # Order of rules in the report (and the assignment ordering when more
    # than one fires):
    #   1. v13 TRUE rules (D1, D2, D3, D4, D5, D5b, D5c, D5d, D5e, D9old)
    #   2. MAGMA_const_zero
    #   3. MAGMA_left_proj
    #   4. MAGMA_right_proj
    #   5. MAGMA_xor
    #   6. MAGMA_const_one
    #   7. MAGMA_other_library
    #   8. v13 FALSE rules (D6, D7, D7b, D7c, D8, D8b, D10s1, D10s2)
    #   9. DEFAULT_FALSE
    # ------------------------------------------------------------------

    SOUND_TRUE_RULES_V13 = {
        "D1", "D2", "D3", "D4", "D5", "D5b", "D5c", "D5d", "D5e",
        "D9", "D9b", "D9bS", "D9bSS", "D4d",
    }
    # D9old is heuristic — handled separately at end of cascade.
    TRUE_RULES_V13 = SOUND_TRUE_RULES_V13

    rule_order = [
        "D1", "D2", "D3", "D4", "D5", "D5b", "D5c", "D5d", "D5e",             # sound TRUE
        "MAGMA_const_zero", "MAGMA_left_proj", "MAGMA_right_proj",
        "MAGMA_xor", "MAGMA_const_one", "MAGMA_other_library",                # FALSE (sound)
        "D6", "D7", "D7b", "D7c", "D8", "D8b", "D10s1", "D10s2",              # FALSE (v13 sound)
        "D9old",                                                              # heuristic TRUE last
        "DEFAULT_FALSE",
    ]

    print("\nRunning cascade on full ETP matrix...", flush=True)
    t0 = time.time()
    fires = {r: 0 for r in rule_order}
    correct = {r: 0 for r in rule_order}
    by_pred = {r: {"true_pred": 0, "false_pred": 0} for r in rule_order}

    # Pre-decode v13 per (i, j) is O(N^2) calls. Speed it up by computing
    # one row at a time and only calling per cell.
    for i in range(n_eq):
        f1 = feats[i]
        gold_row = gold[i]                # bool, len N
        valid_row = valid[i]              # exclude self
        # Per-row magma masks
        row_masks = {name: magma_masks[name][i] for name in
                     ["MAGMA_const_zero", "MAGMA_left_proj", "MAGMA_right_proj",
                      "MAGMA_xor", "MAGMA_const_one", "MAGMA_other_library"]}
        # Track which Eq2 indices have already been claimed by a higher-priority rule
        claimed = ~valid_row.copy()       # diagonal already excluded

        # ---- v13 TRUE rules (per-pair eval) ----
        # We need decide_features_v13 per j, but only when not yet claimed.
        # Group: walk j once.
        for j in range(n_eq):
            if claimed[j]:
                continue
            rule, ans = decide_features_v13(f1, feats[j])
            if ans is True and rule in TRUE_RULES_V13:
                fires[rule] = fires.get(rule, 0) + 1
                if rule not in correct:
                    correct[rule] = 0
                if gold_row[j]:
                    correct[rule] += 1
                claimed[j] = True

        # ---- magma rules (vectorized over remaining j) ----
        for mname in ["MAGMA_const_zero", "MAGMA_left_proj", "MAGMA_right_proj",
                      "MAGMA_xor", "MAGMA_const_one", "MAGMA_other_library"]:
            mask_row = row_masks[mname] & ~claimed
            cnt = int(mask_row.sum())
            if cnt:
                fires[mname] += cnt
                # Magma rule predicts FALSE; correct iff gold==False
                correct[mname] += int(((~gold_row) & mask_row).sum())
                claimed |= mask_row

        # ---- v13 sound FALSE rules ----
        for j in range(n_eq):
            if claimed[j]:
                continue
            rule, ans = decide_features_v13(f1, feats[j])
            if ans is False and rule != "D10":
                fires[rule] = fires.get(rule, 0) + 1
                if rule not in correct:
                    correct[rule] = 0
                if not gold_row[j]:
                    correct[rule] += 1
                claimed[j] = True

        # ---- D9old heuristic TRUE (now at end, just before default) ----
        for j in range(n_eq):
            if claimed[j]:
                continue
            rule, ans = decide_features_v13(f1, feats[j])
            if rule == "D9old":
                fires["D9old"] += 1
                if gold_row[j]:
                    correct["D9old"] += 1
                claimed[j] = True

        # ---- default FALSE for everything left ----
        rest = (~claimed).sum()
        if rest:
            fires["DEFAULT_FALSE"] += int(rest)
            correct["DEFAULT_FALSE"] += int(((~gold_row) & ~claimed).sum())

        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{n_eq} rows, {time.time()-t0:.0f}s", flush=True)

    total_pairs = n_eq * (n_eq - 1)
    print(f"\nDone in {time.time()-t0:.0f}s. Total pairs={total_pairs:,}",
          flush=True)

    # ----- Print per-rule report -----
    print("\n=== Cascade v14: per-rule firing on full ETP ===", flush=True)
    print(f"{'rule':<22} {'fires':>12} {'%pairs':>8} {'correct':>12} "
          f"{'precision':>10}", flush=True)
    summary_rows = []
    total_correct = 0
    total_fires = 0
    for r in rule_order:
        f = fires.get(r, 0)
        c = correct.get(r, 0)
        p = c / f if f else float("nan")
        total_fires += f
        total_correct += c
        print(f"{r:<22} {f:>12,} {f/total_pairs:>7.2%} {c:>12,} {p:>10.4f}",
              flush=True)
        summary_rows.append({"rule": r, "fires": f, "correct": c,
                             "precision": p})
    overall_acc = total_correct / total_fires if total_fires else float("nan")
    print(f"{'TOTAL':<22} {total_fires:>12,} {'':>8} {total_correct:>12,} "
          f"{overall_acc:>10.4f}", flush=True)

    # ----- Aggregate coverage / precision breakdown -----
    # Sound = all rules except the D9old heuristic and the DEFAULT bucket.
    SOUND = [r for r in rule_order if r not in ("D9old", "DEFAULT_FALSE")]
    sound_f = sum(fires[r] for r in SOUND)
    sound_c = sum(correct[r] for r in SOUND)
    non_def_f = total_fires - fires["DEFAULT_FALSE"]
    non_def_c = total_correct - correct["DEFAULT_FALSE"]
    pct = lambda n, d: f"{n/d:.4%}" if d else "n/a"
    print("\n=== Cascade v14 aggregate on full ETP ===", flush=True)
    print(f"  Sound rules only (ex-D9old heuristic):")
    print(f"    coverage:  {sound_f:>14,} / {total_pairs:,} = "
          f"{pct(sound_f, total_pairs)}")
    print(f"    precision: {sound_c:>14,} / {sound_f:,} = "
          f"{pct(sound_c, sound_f)}")
    print(f"  All non-DEFAULT rules (sound + D9old heuristic):")
    print(f"    coverage:  {non_def_f:>14,} = {pct(non_def_f, total_pairs)}")
    print(f"    precision: {pct(non_def_c, non_def_f)}")
    print(f"  DEFAULT bucket:")
    print(f"    coverage:  {fires['DEFAULT_FALSE']:,} = "
          f"{pct(fires['DEFAULT_FALSE'], total_pairs)}")
    print(f"    accuracy:  "
          f"{pct(correct['DEFAULT_FALSE'], fires['DEFAULT_FALSE'])}")

    # ----- Validation set evaluation -----
    print("\n=== Cascade v14: validation set ===", flush=True)
    problems = json.load(open(ROOT / "data/validation/problems.json"))
    answers = json.load(open(ROOT / "data/validation/answers.json"))
    val_fires = defaultdict(lambda: defaultdict(int))
    val_correct = defaultdict(lambda: defaultdict(int))
    val_totals = defaultdict(int)

    for p in problems:
        i = p["eq1_id"] - 1
        j = p["eq2_id"] - 1
        gt = answers[p["id"]]
        diff_lvl = p["difficulty"]
        val_totals[diff_lvl] += 1
        f1 = feats[i]; f2 = feats[j]
        rule, ans = decide_features_v13(f1, f2)
        if ans is True and rule in TRUE_RULES_V13:
            chosen = rule; pred = True
        else:
            # try magma rules in order
            chosen = None
            for mname in ["MAGMA_const_zero", "MAGMA_left_proj", "MAGMA_right_proj",
                          "MAGMA_xor", "MAGMA_const_one", "MAGMA_other_library"]:
                if magma_masks[mname][i, j]:
                    chosen = mname; pred = False
                    break
            if chosen is None:
                if ans is False and rule != "D10":
                    chosen = rule; pred = False
                elif rule == "D9old":
                    chosen = "D9old"; pred = True
                else:
                    chosen = "DEFAULT_FALSE"; pred = False
        val_fires[diff_lvl][chosen] += 1
        if pred == gt:
            val_correct[diff_lvl][chosen] += 1

    val_summary = {}
    for diff_lvl in sorted(val_totals):
        print(f"\n--- {diff_lvl} (n={val_totals[diff_lvl]}) ---", flush=True)
        print(f"{'rule':<22} {'fires':>6} {'correct':>8} {'prec':>8}",
              flush=True)
        diff_total_correct = 0
        rows = []
        for r in rule_order:
            f = val_fires[diff_lvl].get(r, 0)
            if f == 0:
                continue
            c = val_correct[diff_lvl].get(r, 0)
            p = c / f
            print(f"{r:<22} {f:>6} {c:>8} {p:>8.3f}", flush=True)
            diff_total_correct += c
            rows.append({"rule": r, "fires": f, "correct": c, "precision": p})
        acc = diff_total_correct / val_totals[diff_lvl]
        print(f"  overall accuracy: {acc:.4f} "
              f"({diff_total_correct}/{val_totals[diff_lvl]})", flush=True)
        val_summary[diff_lvl] = {"n": val_totals[diff_lvl],
                                  "accuracy": acc, "rows": rows}

    # ----- Save report -----
    report = {
        "etp": {"total_pairs": total_pairs,
                 "overall_accuracy": overall_acc,
                 "sound_coverage":     sound_f / total_pairs,
                 "sound_precision":    (sound_c / sound_f) if sound_f else None,
                 "non_default_coverage":  non_def_f / total_pairs,
                 "non_default_precision": (non_def_c / non_def_f)
                                           if non_def_f else None,
                 "default_coverage":   fires["DEFAULT_FALSE"] / total_pairs,
                 "default_accuracy":   (correct["DEFAULT_FALSE"]
                                        / fires["DEFAULT_FALSE"])
                                        if fires["DEFAULT_FALSE"] else None,
                 "rules": summary_rows},
        "validation": val_summary,
        "rule_order": rule_order,
    }
    json.dump(report, open(OUT / "cascade_v14_report.json", "w"), indent=2,
              default=float)
    print(f"\nsaved {OUT / 'cascade_v14_report.json'}", flush=True)


if __name__ == "__main__":
    main()
