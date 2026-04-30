"""Programmatic checker for the arjun_garg cheatsheet (`cheatsheets/arjun_garg.txt`).

Runs the cascade across every HF SAIR split plus the full 4694×4694 = 22M
ETP cross-product.

Cascade order (TRUE rules in {T1, T3, T4, B2a, B2b}; everything else FALSE):
  L1, L2, L3, M1, M2, M3, M4, M6, M7, D8, T1, T3, T4, F1, B1, B2a, B2b, B2c
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))

from _common import (load_etp_context, magma_masks, run_full_etp, run_split,
                     summarize, save_summary, print_summary, SPLITS,
                     MAGMA_LIB, get_sat_vector)
from parse_equation import Op, Var

OUT_DIR = ROOT / "analysis" / "results" / "arjun_garg"

RULE_ORDER = ["L1", "L2", "L3",
              "M1", "M2", "M3", "M4", "M6", "M7",
              "D8",
              "T1", "T3", "T4",
              "F1",
              "B1", "B2a", "B2b", "B2c"]
TRUE_RULES = {"T1", "T3", "T4", "B2a", "B2b"}

# arjun_garg's MAGMA_ORDER is L1, L2, L3, M1, M2, M3, M4, M6, M7
# Each is a small Cayley table. Use the names from MAGMA_LIB (they line up).
MAGMA_NAMES = {
    "L1": "L1_leftproj2",
    "L2": "L2_rightproj2",
    "L3": "L3_constzero2",
    "M1": "M1_xor",
    "M2": "M2_leftcyc3",
    "M3": "M3_rightcyc3",
    "M4": "M4_spikezero",
    "M6": "M6_leftneg2",
    "M7": "M7_rightneg2",
}


# ---------------------------------------------------------------------------
# Per-equation feature helpers (scalar, used in run_split)
# ---------------------------------------------------------------------------

def _count_var(node, v):
    if isinstance(node, Var):
        return 1 if node.name == v else 0
    return _count_var(node.left, v) + _count_var(node.right, v)


def lhs_var(p):
    return p["lhs"].name if p.get("lhs_is_var") else None


def rhs_var(p):
    return p["rhs"].name if p.get("rhs_is_var") else None


def t1_fires(p2):
    return p2.get("lhs_is_var") and p2.get("rhs_is_var") and lhs_var(p2) == rhs_var(p2)


def t3_fires(p1):
    return p1.get("lhs_is_var") and p1.get("rhs_is_var") and lhs_var(p1) != rhs_var(p1)


def t4_fires(p1):
    if not p1.get("lhs_is_var"):
        return False
    return lhs_var(p1) not in p1.get("rhs_vars", set())


def f1_fires(p1):
    vars_eq1 = set(p1.get("lhs_vars", set())) | set(p1.get("rhs_vars", set()))
    return len(vars_eq1) <= 2


def compute_MSV(p1):
    lhs_vars = p1.get("lhs_vars", set())
    rhs_vars = p1.get("rhs_vars", set())
    all_vars = lhs_vars | rhs_vars
    if not all_vars:
        return (0, 0, 0)
    M = min(_count_var(p1["lhs"], v) + _count_var(p1["rhs"], v) for v in all_vars)
    S = p1.get("n_ops_lhs", 0)
    V = len(lhs_vars)
    return M, S, V


def b_rule(p1):
    M, S, V = compute_MSV(p1)
    if M >= 2:
        return "B1"
    if S == 0:
        return "B2a"
    if S == 1 and V == 2:
        return "B2b"
    return "B2c"


def lm_var(node):
    while isinstance(node, Op):
        node = node.left
    return node.name


def is_left_spine(node):
    if isinstance(node, Var):
        return False
    cur = node
    while isinstance(cur, Op):
        if not isinstance(cur.right, Var):
            return False
        cur = cur.left
    return isinstance(cur, Var)


def n_ops(node):
    if isinstance(node, Var):
        return 0
    return 1 + n_ops(node.left) + n_ops(node.right)


def d8_fires(p1, p2):
    if not (p1.get("lhs_is_var") and p2.get("lhs_is_var")):
        return False
    if not (is_left_spine(p1["rhs"]) and is_left_spine(p2["rhs"])):
        return False
    if lhs_var(p1) != lm_var(p1["rhs"]):
        return False
    if lhs_var(p2) != lm_var(p2["rhs"]):
        return False
    n = n_ops(p1["rhs"])
    m = n_ops(p2["rhs"])
    if n == 0:
        return False
    return (m % n) != 0


def predict(p1, p2, magma_hits):
    for rule, magma in MAGMA_NAMES.items():
        if magma_hits.get(magma):
            return rule
    if d8_fires(p1, p2):
        return "D8"
    if t1_fires(p2):
        return "T1"
    if t3_fires(p1):
        return "T3"
    if t4_fires(p1):
        return "T4"
    if f1_fires(p1):
        return "F1"
    return b_rule(p1)


def run_split_local(stem, ctx):
    """Scalar per-problem run on a HF split. Splits like `evaluation_order5`
    reference equation IDs outside the 4694-equation cache; for those we parse
    the equation strings directly and compute magma satisfaction on the fly."""
    from _common import load_split, magma_masks
    from parse_equation import parse_equation as _parse_eq
    from magma_counterexamples import compile_equation as _compile_eq
    masks = magma_masks(ctx, list(MAGMA_NAMES.values()))
    sat_vecs = {n: ctx.sat_cache[n] for n in MAGMA_NAMES.values()}
    rows = []
    for p in load_split(stem):
        i_id, j_id = p["eq1_id"], p["eq2_id"]
        i, j = i_id - 1, j_id - 1
        if 0 <= i < ctx.n_eq:
            p1 = ctx.parsed[i]
            sat1 = {n: bool(sat_vecs[n][i]) for n in MAGMA_NAMES.values()}
        else:
            p1 = _parse_eq(p["equation1"])
            c1 = _compile_eq(p1["lhs"], p1["rhs"])
            sat1 = {n: bool(c1(MAGMA_LIB[n])) for n in MAGMA_NAMES.values()}
        if 0 <= j < ctx.n_eq:
            p2 = ctx.parsed[j]
            sat2 = {n: bool(sat_vecs[n][j]) for n in MAGMA_NAMES.values()}
        else:
            p2 = _parse_eq(p["equation2"])
            c2 = _compile_eq(p2["lhs"], p2["rhs"])
            sat2 = {n: bool(c2(MAGMA_LIB[n])) for n in MAGMA_NAMES.values()}
        magma_hits = {n: (sat1[n] and not sat2[n]) for n in MAGMA_NAMES.values()}
        rule = predict(p1, p2, magma_hits)
        pred = rule in TRUE_RULES
        gold = bool(p["answer"])
        rows.append({"id": p.get("id"), "eq1_id": i_id, "eq2_id": j_id,
                     "gold": gold, "rule": rule, "pred": pred,
                     "correct": pred == gold})
    return summarize(rows, RULE_ORDER, TRUE_RULES, dataset_name=stem)


# ---------------------------------------------------------------------------
# Vectorized full-ETP fires
# ---------------------------------------------------------------------------

def build_full_etp_fires(ctx):
    """Pre-compute per-rule (4694,4694) bool fire-masks and return a closure
    `fires_for_rule(rule_name) -> bool[n,n]`. This is vectorized for speed."""
    n = ctx.n_eq
    parsed = ctx.parsed

    # Magma masks (sound FALSE witnesses). For L1 we use the order-2 left-proj
    # magma — same satisfaction set as arjun_garg's L1 rule.
    masks = magma_masks(ctx, list(MAGMA_NAMES.values()))

    # Per-eq bool features (n,) arrays
    f_lhs_is_var = np.array([bool(p.get("lhs_is_var")) for p in parsed])
    f_rhs_is_var = np.array([bool(p.get("rhs_is_var")) for p in parsed])
    f_lhs_var = [lhs_var(p) for p in parsed]
    f_rhs_var = [rhs_var(p) for p in parsed]

    # T1: Eq2.LHS bare AND Eq2.RHS bare AND same letter — depends on j only.
    t1_eq = np.array([(p.get("lhs_is_var") and p.get("rhs_is_var")
                       and lhs_var(p) == rhs_var(p)) for p in parsed])
    # T3: Eq1.LHS bare AND Eq1.RHS bare AND DIFFERENT letters — depends on i only.
    t3_eq = np.array([(p.get("lhs_is_var") and p.get("rhs_is_var")
                       and lhs_var(p) != rhs_var(p)) for p in parsed])
    # T4: Eq1.LHS bare AND letter NOT in Eq1.RHS_vars — depends on i only.
    def _t4(p):
        if not p.get("lhs_is_var"):
            return False
        return lhs_var(p) not in p.get("rhs_vars", set())
    t4_eq = np.array([_t4(p) for p in parsed])
    # F1: |vars(Eq1)| ≤ 2 — depends on i only.
    f1_eq = np.array([len(p.get("lhs_vars", set()) | p.get("rhs_vars", set())) <= 2
                      for p in parsed])

    # B-rule features
    M_arr = np.zeros(n, dtype=np.int8)
    S_arr = np.zeros(n, dtype=np.int8)
    V_arr = np.zeros(n, dtype=np.int8)
    for i, p in enumerate(parsed):
        M, S, V = compute_MSV(p)
        M_arr[i] = min(M, 127)
        S_arr[i] = min(S, 127)
        V_arr[i] = min(V, 127)

    # D8: depends on (i,j). Build as scalar precompute since D8 is rare.
    # Pre-compute per-eq spine features.
    is_lspine = np.zeros(n, dtype=bool)
    rhs_lm_var = [None] * n
    rhs_n_ops = np.zeros(n, dtype=np.int16)
    for i, p in enumerate(parsed):
        rhs = p["rhs"]
        if is_left_spine(rhs):
            is_lspine[i] = True
            rhs_lm_var[i] = lm_var(rhs)
            rhs_n_ops[i] = n_ops(rhs)
    d8_eligible_eq1 = f_lhs_is_var & is_lspine & np.array(
        [(f_lhs_var[i] is not None and rhs_lm_var[i] is not None
          and f_lhs_var[i] == rhs_lm_var[i]) for i in range(n)])
    d8_eligible_eq2 = f_lhs_is_var & is_lspine & np.array(
        [(f_lhs_var[j] is not None and rhs_lm_var[j] is not None
          and f_lhs_var[j] == rhs_lm_var[j]) for j in range(n)])

    # D8 mask: outer product of eligibility, then m % n != 0 with n = rhs_n_ops[i].
    def _d8_mask():
        elig = d8_eligible_eq1[:, None] & d8_eligible_eq2[None, :]
        if not elig.any():
            return np.zeros((n, n), dtype=bool)
        # Build divisibility test via broadcasting. n_i must be > 0.
        n_i = rhs_n_ops[:, None]  # shape (n,1)
        m_j = rhs_n_ops[None, :]  # shape (1,n)
        with np.errstate(divide='ignore', invalid='ignore'):
            divides = np.where(n_i > 0, (m_j % np.where(n_i == 0, 1, n_i)) == 0, False)
        return elig & ~divides

    cache = {}

    def fires_for_rule(rule):
        if rule in cache:
            return cache[rule]
        if rule in MAGMA_NAMES:
            mask = masks[MAGMA_NAMES[rule]]
        elif rule == "D8":
            mask = _d8_mask()
        elif rule == "T1":
            # Depends on j only (Eq2). Mask[i,j] = t1_eq[j].
            mask = np.broadcast_to(t1_eq[None, :], (n, n)).copy()
        elif rule == "T3":
            mask = np.broadcast_to(t3_eq[:, None], (n, n)).copy()
        elif rule == "T4":
            mask = np.broadcast_to(t4_eq[:, None], (n, n)).copy()
        elif rule == "F1":
            mask = np.broadcast_to(f1_eq[:, None], (n, n)).copy()
        elif rule == "B1":
            # B1: M >= 2  (else fall-through to B2*)
            b1 = (M_arr >= 2)
            mask = np.broadcast_to(b1[:, None], (n, n)).copy()
        elif rule == "B2a":
            # M=1 AND S=0
            b2a = (M_arr <= 1) & (S_arr == 0)
            mask = np.broadcast_to(b2a[:, None], (n, n)).copy()
        elif rule == "B2b":
            # M=1 AND S=1 AND V=2
            b2b = (M_arr <= 1) & (S_arr == 1) & (V_arr == 2)
            mask = np.broadcast_to(b2b[:, None], (n, n)).copy()
        elif rule == "B2c":
            # everything else under M=1
            b2c = (M_arr <= 1) & ~((S_arr == 0) | ((S_arr == 1) & (V_arr == 2)))
            # B2c has to also account for M>=2 NOT routed here; B1 absorbs those.
            mask = np.broadcast_to(b2c[:, None], (n, n)).copy()
        else:
            raise KeyError(rule)
        cache[rule] = mask
        return mask

    return fires_for_rule


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    print("Loading ETP context…", file=sys.stderr)
    ctx = load_etp_context(load_gold=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries = {}

    for split in SPLITS:
        s = run_split_local(split, ctx)
        print_summary(s)
        save_summary(s, OUT_DIR / f"{split}.json", drop_rows=False)
        summaries[split] = {"n": s["n"], "n_correct": s["n_correct"],
                            "accuracy": s["accuracy"], "by_rule": s["by_rule"],
                            "confusion": s["confusion"]}

    print("\n=== Full ETP run (22M pairs) ===", file=sys.stderr)
    fires = build_full_etp_fires(ctx)
    s_etp = run_full_etp(ctx, fires, RULE_ORDER, TRUE_RULES, progress_label="arjun_garg ETP")
    print_summary(s_etp)
    save_summary(s_etp, OUT_DIR / "full_etp.json", drop_rows=True)
    if s_etp is not None and not s_etp.get("skipped"):
        summaries["full_etp"] = {"n": s_etp["n"], "n_correct": s_etp["n_correct"],
                                 "accuracy": s_etp["accuracy"],
                                 "by_rule": s_etp["by_rule"],
                                 "confusion": s_etp["confusion"]}

    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summaries, f, indent=2)

    # Markdown summary
    md = ["# arjun_garg programmatic checker — summary", "",
          "## Overall accuracy", "",
          "| dataset | n | accuracy |", "|---|---:|---:|"]
    for split, s in summaries.items():
        n, nc = s["n"], s["n_correct"]
        md.append(f"| {split} | {n} | {nc}/{n} = {nc/n*100:.4f}% |")
    md.append("")
    md.append("## Per-split rule breakdown")
    for split, s in summaries.items():
        md.append(f"\n### `{split}`  —  accuracy {s['n_correct']}/{s['n']} = {s['n_correct']/s['n']*100:.2f}%")
        cf = s["confusion"]
        md.append(f"\nConfusion: TP={cf['tp']}, FP={cf['fp']}, TN={cf['tn']}, FN={cf['fn']}\n")
        md.append("| rule | verdict | fires | correct | wrong | precision |")
        md.append("|------|---------|------:|--------:|------:|----------:|")
        for rule in RULE_ORDER:
            bs = s["by_rule"].get(rule)
            if not bs or bs.get("n", 0) == 0:
                continue
            verdict = "TRUE" if rule in TRUE_RULES else "FALSE"
            correct = bs["tp"] + bs["tn"]
            wrong = bs["fp"] + bs["fn"]
            prec = correct / bs["n"] * 100
            md.append(f"| {rule} | {verdict} | {bs['n']} | {correct} | {wrong} | {prec:.1f}% |")
    (OUT_DIR / "SUMMARY.md").write_text("\n".join(md))
    print(f"\nWrote {OUT_DIR/'SUMMARY.md'}")


if __name__ == "__main__":
    main()
