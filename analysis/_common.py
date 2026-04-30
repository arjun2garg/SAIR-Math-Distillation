"""Shared utilities for programmatic cheatsheet evaluation.

Each cheatsheet checker imports from this module to:
  - Load all 4694 equations and their parsed features (one shot, cached).
  - Get a library of named witness magmas covering what cheatsheets reference.
  - Compute (i,j) FALSE-witness masks for any subset of magmas.
  - Run a per-pair predict function across all HF splits + the full 22M ETP
    cross-product, with a standardized rule-by-rule breakdown output.

A "predict function" has the signature:
    predict(eq1_id, eq2_id, parsed, magma_hits, ctx) -> rule_name (str)
where rule_name comes from a fixed RULE_ORDER list and the checker also
declares which rule names imply TRUE vs FALSE.

The full-ETP run is vectorized: see `run_full_etp_vectorized` for details.
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))

from parse_equation import parse_all_equations, Op, Var  # noqa: E402
from magma_counterexamples import compile_equation, satisfaction_vector  # noqa: E402

EQ_PATH = ROOT / "data" / "equations.txt"
SAIR_EVAL_DIR = ROOT / "data" / "sair_eval"
ETP_CACHE = ROOT / "data" / "full_etp_cache.pkl"
ETP_GOLD_NPY = ROOT / "data" / "outcomes_bool.npy"

SPLITS = [
    "normal", "hard", "hard1", "hard2", "hard3",
    "evaluation_normal", "evaluation_hard", "evaluation_extra_hard",
    "evaluation_order5",
]


# ---------------------------------------------------------------------------
# 1. Equation context (parsed once, shared across sub-agent runs)
# ---------------------------------------------------------------------------

@dataclass
class ETPContext:
    eqs_raw: list[dict]          # parse_all_equations() output (parse trees + features)
    parsed: list[dict]           # alias for eqs_raw (same dicts)
    compiled: list               # compile_equation() per equation
    n_eq: int                    # 4694
    gold: np.ndarray | None      # (4694,4694) bool, None if cache missing
    sat_cache: dict              # name -> bool[n_eq] satisfaction vector


def load_etp_context(load_gold: bool = True) -> ETPContext:
    """Load parsed equations and (optionally) the 4694×4694 ETP gold matrix.

    Gold matrix sources, in priority order:
      1. `data/full_etp_cache.pkl` (~163 MB, contains gold + sat + refuted).
      2. `data/outcomes_bool.npy` (~22 MB, gold only — canonical ETP source).
      3. None — full-ETP runs are unavailable but per-split runs still work.
    """
    eqs_raw = parse_all_equations(str(EQ_PATH))
    compiled = [compile_equation(e["lhs"], e["rhs"]) for e in eqs_raw]
    gold = None
    if load_gold:
        if ETP_CACHE.exists():
            with open(ETP_CACHE, "rb") as f:
                cache = pickle.load(f)
            gold = cache["gold"]
        elif ETP_GOLD_NPY.exists():
            gold = np.load(ETP_GOLD_NPY).astype(bool)
    return ETPContext(eqs_raw=eqs_raw, parsed=eqs_raw, compiled=compiled,
                      n_eq=len(eqs_raw), gold=gold, sat_cache={})


def get_sat_vector(ctx: ETPContext, name: str, table: np.ndarray) -> np.ndarray:
    """Compute (or recall) the satisfaction vector for the magma named `name`."""
    if name in ctx.sat_cache:
        return ctx.sat_cache[name]
    sv = satisfaction_vector(table, ctx.compiled)
    ctx.sat_cache[name] = sv
    return sv


# ---------------------------------------------------------------------------
# 2. Witness-magma library
#    Includes every small magma referenced by any of the 7 cheatsheets.
#    For magmas larger than order 3, vars-≤3 + size-≤3 evaluation can take
#    longer; satisfaction_vector handles arbitrary order.
# ---------------------------------------------------------------------------

def _table(rows):
    return np.array(rows, dtype=np.int8)


# --- Order-2 magmas ---
M_LEFT_PROJ_2 = _table([[0, 0], [1, 1]])               # x*y = x  (left-zero / left-projection, |S|=2)
M_RIGHT_PROJ_2 = _table([[0, 1], [0, 1]])              # x*y = y
M_CONST_ZERO_2 = _table([[0, 0], [0, 0]])              # x*y = 0
M_XOR_2 = _table([[0, 1], [1, 0]])                     # x XOR y
M_LEFT_NEG_2 = _table([[1, 1], [0, 0]])                # x*y = NOT x
M_RIGHT_NEG_2 = _table([[1, 0], [1, 0]])               # x*y = NOT y
M_NAND_2 = _table([[1, 1], [1, 0]])                    # x*y = NAND(x,y) = 1 - x*y in {0,1}
M_AND_2 = _table([[0, 0], [0, 1]])                     # x*y = AND
M_OR_2 = _table([[0, 1], [1, 1]])                      # x*y = OR
M_IMPL_2 = _table([[1, 1], [0, 1]])                    # x*y = x→y = NOT x OR y

# --- Order-3 magmas ---
M_LEFT_PROJ_3 = _table([[0, 0, 0], [1, 1, 1], [2, 2, 2]])    # x*y = x
M_RIGHT_PROJ_3 = _table([[0, 1, 2], [0, 1, 2], [0, 1, 2]])    # x*y = y
M_CONST_ZERO_3 = _table([[0, 0, 0], [0, 0, 0], [0, 0, 0]])    # x*y = 0
M_LEFT_CYC3 = _table([[1, 1, 1], [2, 2, 2], [0, 0, 0]])       # x*y = x+1 mod 3
M_RIGHT_CYC3 = _table([[1, 2, 0], [1, 2, 0], [1, 2, 0]])      # x*y = y+1 mod 3
M_SPIKE_ZERO = _table([[0, 2, 0], [0, 0, 0], [0, 0, 0]])      # zero except 0*1=2
M_MAX_3 = _table([[0, 1, 2], [1, 1, 2], [2, 2, 2]])           # max-semilattice
M_MIN_3 = _table([[0, 0, 0], [0, 1, 1], [0, 1, 2]])           # min-semilattice
M_BCK_3 = _table([[0, 0, 0], [1, 0, 0], [2, 1, 0]])           # BCK / set difference
M_RPS_3 = _table([[0, 1, 0], [1, 1, 2], [0, 2, 2]])           # rock-paper-scissors
M_NILP_3 = _table([[0, 0, 0], [0, 0, 0], [1, 0, 0]])          # nilpotent (2*0=1, else 0)
M_AFFINE_2X_MINUS_Y_3 = _table([[0, 2, 1], [2, 1, 0], [1, 0, 2]])   # x*y = 2x-y mod 3
M_SQUAG_3 = _table([[0, 2, 1], [2, 1, 0], [1, 0, 2]])         # 2x+2y mod 3 (Steiner squag)
M_IMPL_3 = _table([[1, 1, 1], [0, 1, 1], [0, 0, 1]])          # min(1, 1-x+y) on {0,1,2}
M_KNUTH_INNER_HALVES_3 = _table([[0, 1, 2], [0, 1, 2], [0, 1, 2]])  # placeholder; real Knuth on order 4

# --- Order-4 magmas ---
# Knuth central groupoid on {0,1}x{0,1} encoded as 0=(0,0),1=(0,1),2=(1,0),3=(1,1)
# (a,b)*(c,d) = (b,c) -> we encode b->lo bit, c->hi bit
def _knuth_central_4():
    def pack(b, a): return 2 * a + b  # (a,b) -> a*2+b (so a=hi-bit, b=lo-bit)
    T = np.zeros((4, 4), dtype=np.int8)
    for ab in range(4):
        a, b = ab >> 1, ab & 1
        for cd in range(4):
            c, d = cd >> 1, cd & 1
            T[ab, cd] = pack(c, b)  # result is (b,c)
    return T


M_KNUTH_CENTRAL_4 = _knuth_central_4()
# Order-4 Rectangular Band: (a,b)*(c,d) = (a,d)
def _rect_band_4():
    T = np.zeros((4, 4), dtype=np.int8)
    for ab in range(4):
        a, b = ab >> 1, ab & 1
        for cd in range(4):
            c, d = cd >> 1, cd & 1
            T[ab, cd] = (a << 1) | d
    return T


M_RECT_BAND_4 = _rect_band_4()


# --- Affine over Z_n: x*y = a*x + b*y mod n ---
def affine_table(a: int, b: int, n: int) -> np.ndarray:
    T = np.zeros((n, n), dtype=np.int8)
    for x in range(n):
        for y in range(n):
            T[x, y] = (a * x + b * y) % n
    return T


# Curated registry. Sub-agent checkers can reach in for the magmas their
# cheatsheet names. Add to this dict if a cheatsheet uses something exotic.
MAGMA_LIB = {
    # Order 2
    "L1_leftproj2": M_LEFT_PROJ_2,
    "L2_rightproj2": M_RIGHT_PROJ_2,
    "L3_constzero2": M_CONST_ZERO_2,
    "M1_xor": M_XOR_2,
    "M6_leftneg2": M_LEFT_NEG_2,
    "M7_rightneg2": M_RIGHT_NEG_2,
    "NAND_2": M_NAND_2,
    "AND_2": M_AND_2,
    "OR_2": M_OR_2,
    "IMPL_2": M_IMPL_2,
    # Order 3
    "L1_leftproj3": M_LEFT_PROJ_3,
    "L2_rightproj3": M_RIGHT_PROJ_3,
    "L3_constzero3": M_CONST_ZERO_3,
    "M2_leftcyc3": M_LEFT_CYC3,
    "M3_rightcyc3": M_RIGHT_CYC3,
    "M4_spikezero": M_SPIKE_ZERO,
    "MAX_3": M_MAX_3,
    "MIN_3": M_MIN_3,
    "BCK_3": M_BCK_3,
    "RPS_3": M_RPS_3,
    "NILP_3": M_NILP_3,
    "AFFINE_2X_MINUS_Y_3": M_AFFINE_2X_MINUS_Y_3,
    "SQUAG_3": M_SQUAG_3,
    "IMPL_3": M_IMPL_3,
    # Order 4
    "KNUTH_CENTRAL_4": M_KNUTH_CENTRAL_4,
    "RECT_BAND_4": M_RECT_BAND_4,
    # Common affines
    "AFFINE_z3_x_plus_y": affine_table(1, 1, 3),
    "AFFINE_z3_x_minus_y": affine_table(1, -1, 3),
    "AFFINE_z4_x_plus_y": affine_table(1, 1, 4),
    "AFFINE_z5_x_plus_y": affine_table(1, 1, 5),
}


# ---------------------------------------------------------------------------
# 3. Witness-mask helpers
# ---------------------------------------------------------------------------

def magma_masks(ctx: ETPContext, names: list[str]) -> dict[str, np.ndarray]:
    """For each named magma, return (n_eq, n_eq) bool array where mask[i,j] is
    True iff the magma satisfies Eq_{i+1} but NOT Eq_{j+1} — i.e., it's a sound
    FALSE witness for Eq_{i+1} -> Eq_{j+1}."""
    out = {}
    for name in names:
        if name not in MAGMA_LIB:
            raise KeyError(f"Magma {name!r} not in MAGMA_LIB. Add it.")
        sv = get_sat_vector(ctx, name, MAGMA_LIB[name])
        out[name] = sv[:, None] & ~sv[None, :]
    return out


def per_pair_magma_hits(masks: dict[str, np.ndarray], i: int, j: int) -> dict[str, bool]:
    return {n: bool(m[i, j]) for n, m in masks.items()}


# ---------------------------------------------------------------------------
# 4. Standardized scalar runner — for HF splits (small).
# ---------------------------------------------------------------------------

def load_split(stem: str) -> list[dict]:
    path = SAIR_EVAL_DIR / f"{stem}.jsonl"
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run_split(stem: str, ctx: ETPContext, magma_names: list[str],
              predict: Callable, true_rules: set[str],
              rule_order: list[str]) -> dict:
    """Run `predict` per problem in the split. predict signature:
        predict(p1, p2, magma_hits) -> rule_name
    Returns a dict with overall stats + per-rule breakdown + raw rows.
    """
    problems = load_split(stem)
    masks = magma_masks(ctx, magma_names)
    rows = []
    for p in problems:
        i = p["eq1_id"] - 1
        j = p["eq2_id"] - 1
        hits = {n: bool(masks[n][i, j]) for n in magma_names}
        rule = predict(ctx.parsed[i], ctx.parsed[j], hits)
        pred = rule in true_rules
        gold = bool(p["answer"])
        rows.append({"id": p.get("id"), "eq1_id": p["eq1_id"], "eq2_id": p["eq2_id"],
                     "gold": gold, "rule": rule, "pred": pred,
                     "correct": pred == gold})
    return summarize(rows, rule_order, true_rules, dataset_name=stem)


# ---------------------------------------------------------------------------
# 5. Vectorized runner for the full 22M ETP cross-product.
#
# Each cheatsheet's cascade can be expressed as:
#   for rule in rule_order:
#       fires = compute fires-mask over (i,j) using parsed features and/or
#               magma masks already in memory
#       firing_rule[fires_unassigned & fires] = rule
#       set rule_pred[fires_unassigned & fires] based on rule's verdict
# We provide a helper to compose this.
# ---------------------------------------------------------------------------

def run_full_etp(ctx: ETPContext, fires_for_rule: Callable[[str], np.ndarray],
                 rule_order: list[str], true_rules: set[str],
                 progress_label: str = "ETP") -> dict:
    """`fires_for_rule(rule_name) -> bool[n_eq, n_eq]` returns the candidate
    fire mask for that rule (irrespective of the cascade).  We then walk
    rule_order: the first rule whose mask is True at (i,j) wins.

    Returns: per-rule breakdown counts + overall accuracy.
    """
    if ctx.gold is None:
        sys.stderr.write(
            "[run_full_etp] ETP gold matrix not available "
            "(neither data/full_etp_cache.pkl nor data/outcomes_bool.npy found).\n"
            "  Skipping full-ETP run. Per-split runs are unaffected.\n")
        return {
            "dataset": "full_etp",
            "n": 0, "n_correct": 0, "accuracy": 0.0,
            "by_rule": {r: {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0}
                        for r in rule_order},
            "rule_order": rule_order, "true_rules": sorted(true_rules),
            "confusion": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "skipped": True,
        }
    n = ctx.n_eq
    assigned = np.zeros((n, n), dtype=bool)
    firing_rule = np.full((n, n), -1, dtype=np.int16)
    pred = np.zeros((n, n), dtype=bool)

    rule_index = {r: idx for idx, r in enumerate(rule_order)}
    by_rule = {r: {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0}
               for r in rule_order}

    for r in rule_order:
        t0 = time.time()
        fires = fires_for_rule(r)
        new = fires & ~assigned
        if not new.any():
            continue
        firing_rule[new] = rule_index[r]
        rule_says_true = r in true_rules
        if rule_says_true:
            pred[new] = True
        # else pred stays False (initialized)
        assigned[new] = True
        # Stats
        gold_new = ctx.gold[new]
        if rule_says_true:
            tp = int(gold_new.sum())
            fp = int((~gold_new).sum())
            by_rule[r]["tp"] = tp
            by_rule[r]["fp"] = fp
            by_rule[r]["n"] = tp + fp
        else:
            tn = int((~gold_new).sum())
            fn = int(gold_new.sum())
            by_rule[r]["tn"] = tn
            by_rule[r]["fn"] = fn
            by_rule[r]["n"] = tn + fn
        sys.stderr.write(f"  [{progress_label}] {r}: fires={by_rule[r]['n']:>10}  "
                         f"({time.time()-t0:5.1f}s)\n")
        sys.stderr.flush()

    # Anything still unassigned must be a default
    if (~assigned).any():
        raise RuntimeError("Cascade did not cover all (i,j) pairs — make sure "
                           "the last rule has a `fires == True` mask.")

    n_correct = int((pred == ctx.gold).sum())
    n_total = pred.size
    tp = int((pred & ctx.gold).sum())
    fp = int((pred & ~ctx.gold).sum())
    tn = int((~pred & ~ctx.gold).sum())
    fn = int((~pred & ctx.gold).sum())
    return {
        "dataset": "full_etp",
        "n": n_total,
        "n_correct": n_correct,
        "accuracy": n_correct / n_total,
        "by_rule": by_rule,
        "rule_order": rule_order,
        "true_rules": sorted(true_rules),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


# ---------------------------------------------------------------------------
# 6. Summary helper for split runs (rows -> stats dict)
# ---------------------------------------------------------------------------

def summarize(rows: list[dict], rule_order: list[str], true_rules: set[str],
              dataset_name: str) -> dict:
    n = len(rows)
    n_correct = sum(1 for r in rows if r["correct"])
    by_rule = {r: {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0}
               for r in rule_order}
    for r in rows:
        s = by_rule.setdefault(r["rule"], {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0})
        s["n"] += 1
        if r["pred"] and r["gold"]:
            s["tp"] += 1
        elif (not r["pred"]) and (not r["gold"]):
            s["tn"] += 1
        elif r["pred"] and not r["gold"]:
            s["fp"] += 1
        else:
            s["fn"] += 1
    tp = sum(1 for r in rows if r["pred"] and r["gold"])
    fp = sum(1 for r in rows if r["pred"] and not r["gold"])
    tn = sum(1 for r in rows if not r["pred"] and not r["gold"])
    fn = sum(1 for r in rows if not r["pred"] and r["gold"])
    return {
        "dataset": dataset_name,
        "n": n,
        "n_correct": n_correct,
        "accuracy": n_correct / n if n else 0.0,
        "by_rule": by_rule,
        "rule_order": rule_order,
        "true_rules": sorted(true_rules),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# 7. Pretty-print a summary
# ---------------------------------------------------------------------------

def print_summary(s: dict | None, file=sys.stdout):
    if s is None:
        return
    if s.get("skipped"):
        print(f"\n[{s['dataset']}] skipped (ETP gold matrix not available).",
              file=file)
        return
    n, nc = s["n"], s["n_correct"]
    print(f"\n[{s['dataset']}] n={n}  accuracy={nc}/{n} = {nc/n*100:.2f}%", file=file)
    cf = s["confusion"]
    print(f"  TRUE-precision = {cf['tp']}/{cf['tp']+cf['fp']} = "
          f"{(cf['tp']/(cf['tp']+cf['fp'])*100) if (cf['tp']+cf['fp']) else 0:.1f}% | "
          f"TRUE-recall = {cf['tp']}/{cf['tp']+cf['fn']} = "
          f"{(cf['tp']/(cf['tp']+cf['fn'])*100) if (cf['tp']+cf['fn']) else 0:.1f}%",
          file=file)
    print(f"{'rule':<14} {'verdict':<7} {'fires':>12} {'correct':>12} "
          f"{'wrong':>12} {'precision':>10}", file=file)
    print('-' * 72, file=file)
    for rule in s["rule_order"]:
        bs = s["by_rule"].get(rule, {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0})
        if bs["n"] == 0:
            continue
        verdict = "TRUE" if rule in s["true_rules"] else "FALSE"
        correct = bs["tp"] + bs["tn"]
        wrong = bs["fp"] + bs["fn"]
        prec = correct / bs["n"] * 100
        print(f"{rule:<14} {verdict:<7} {bs['n']:>12} {correct:>12} "
              f"{wrong:>12} {prec:>9.1f}%", file=file)


# ---------------------------------------------------------------------------
# 8. Save helper
# ---------------------------------------------------------------------------

def save_summary(s: dict | None, out_path: Path, drop_rows: bool = False):
    if s is None:
        return
    s2 = dict(s)
    if drop_rows and "rows" in s2:
        s2.pop("rows")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(s2, f, indent=2)
