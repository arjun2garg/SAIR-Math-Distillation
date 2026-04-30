"""Programmatic ("ceiling") checker for the pi.txt cheatsheet.

Implements the deterministic cascade exactly as written in
`cheatsheets/pi.txt`:

  Step 1 (TRUE shortcuts):
      X1  Both sides of B literally identical
      X2  A and B same up to renaming + side-swap
      X3  One side of A is a lone variable absent from the other side

  Step 2 (Forced-behavior — F-rules split into F*_TRUE / F*_FALSE):
      F1  Eq1 = `x = x*y` shape  ->  TRUE iff LP(B), else FALSE
      F2  Eq1 = `x = y*x` shape  ->  TRUE iff RP(B), else FALSE
      F3  Both sides of A are products with same LEFT child, different right
          children -> TRUE iff `(leftmost(B.lhs), ldepth(B.lhs))
                              == (leftmost(B.rhs), ldepth(B.rhs))`
      F4  Both sides of A are products with same RIGHT child, different left
          children -> TRUE iff `(rightmost, rdepth)` pairs match on B

  Step 3 (Affine refutation A1..A10):
      For each probe, compute affine form of A.lhs and A.rhs.
      If they match, compute affine forms of B.lhs and B.rhs.
      If those differ, answer FALSE.

  Step 4 (Structural reject H1..H6 — see pi.txt for exact predicates).

  DEFAULT_TRUE: if nothing fires, return TRUE.

Two entry points:
    run_on_split(stem, ctx, feats)    -> per-split scalar evaluation
    run_full_etp_summary(ctx, feats)  -> vectorized 4694x4694 evaluation

Driver (`python3 analysis/pi_checker.py`) runs all 9 SAIR splits and
the full ETP, writing results to `analysis/results/pi/`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))

from parse_equation import Op, Var, parse_equation as _parse_eq  # noqa: E402

from _common import (  # noqa: E402
    ETPContext,
    SPLITS,
    load_etp_context,
    load_split,
    print_summary,
    run_full_etp,
    save_summary,
    summarize,
)


# ---------------------------------------------------------------------------
# 1. Cascade name list & verdicts
# ---------------------------------------------------------------------------

A_PROBES = [
    ("A1",  (0, 1, 1, 3)),
    ("A2",  (1, 0, 1, 3)),
    ("A3",  (1, 1, 0, 3)),
    ("A4",  (1, -1, 0, 3)),
    ("A5",  (-1, -1, 0, 3)),
    ("A6",  (-1, 2, 0, 4)),
    ("A7",  (1, 2, 0, 4)),
    ("A8",  (2, 1, 0, 4)),
    ("A9",  (2, 1, 1, 4)),
    ("A10", (-2, -2, 0, 5)),
]


RULE_ORDER = (
    ["X1", "X2", "X3"]
    + ["F1_TRUE", "F1_FALSE", "F2_TRUE", "F2_FALSE",
       "F3_TRUE", "F3_FALSE", "F4_TRUE", "F4_FALSE"]
    + [name for name, _ in A_PROBES]
    + ["H1", "H2", "H3", "H4", "H5", "H6"]
    + ["DEFAULT_TRUE"]
)

TRUE_RULES = {"X1", "X2", "X3",
              "F1_TRUE", "F2_TRUE", "F3_TRUE", "F4_TRUE",
              "DEFAULT_TRUE"}


# ---------------------------------------------------------------------------
# 2. Tree helpers (same shape as reza_jamei_checker)
# ---------------------------------------------------------------------------

def _is_var(n):
    return isinstance(n, Var)


def leaves(node):
    if isinstance(node, Var):
        return [node.name]
    return leaves(node.left) + leaves(node.right)


def leftmost(node):
    while isinstance(node, Op):
        node = node.left
    return node.name


def rightmost(node):
    while isinstance(node, Op):
        node = node.right
    return node.name


def left_depth(node):
    """Number of left-edges from the root to the leftmost leaf."""
    d = 0
    while isinstance(node, Op):
        d += 1
        node = node.left
    return d


def right_depth(node):
    d = 0
    while isinstance(node, Op):
        d += 1
        node = node.right
    return d


def all_vars(node):
    if isinstance(node, Var):
        return {node.name}
    return all_vars(node.left) | all_vars(node.right)


def tree_eq(a, b):
    if isinstance(a, Var) and isinstance(b, Var):
        return a.name == b.name
    if isinstance(a, Op) and isinstance(b, Op):
        return tree_eq(a.left, b.left) and tree_eq(a.right, b.right)
    return False


def canonicalize_equation(lhs, rhs):
    """Symmetric canonical form: rename vars by first-appearance under both
    side-orders; return the lexicographically smaller of the two reprs."""
    var_pool = "xyzwuv" + "abcdefghijklmnopqrst"

    def go(a, b):
        mapping = {}

        def assign(n):
            if isinstance(n, Var):
                if n.name not in mapping:
                    mapping[n.name] = var_pool[len(mapping)]
            else:
                assign(n.left)
                assign(n.right)

        def rebuild(n):
            if isinstance(n, Var):
                return mapping[n.name]
            return (rebuild(n.left), rebuild(n.right))

        assign(a)
        assign(b)
        return (rebuild(a), rebuild(b))

    f = go(lhs, rhs)
    g = go(rhs, lhs)
    return f if repr(f) <= repr(g) else g


# ---------------------------------------------------------------------------
# 3. Step 1 / Step 2 source-shape predicates (per equation)
# ---------------------------------------------------------------------------

def x1_eq2_flag(p):
    """Eq2's two sides literally identical."""
    return tree_eq(p["lhs"], p["rhs"])


def x3_eq1_flag(p):
    """One side of Eq1 is a lone variable absent from the other side."""
    L, R = p["lhs"], p["rhs"]
    if _is_var(L) and L.name not in all_vars(R):
        return True
    if _is_var(R) and R.name not in all_vars(L):
        return True
    return False


def f1_eq1_flag(p):
    """Eq1 is `x = x*y` (or `x*y = x`) up to renaming, x != y."""
    L, R = p["lhs"], p["rhs"]
    for A, B in ((L, R), (R, L)):
        if _is_var(A) and isinstance(B, Op) and _is_var(B.left) and _is_var(B.right):
            if A.name == B.left.name and B.left.name != B.right.name:
                return True
    return False


def f2_eq1_flag(p):
    """Eq1 is `x = y*x` (or `y*x = x`), x != y."""
    L, R = p["lhs"], p["rhs"]
    for A, B in ((L, R), (R, L)):
        if _is_var(A) and isinstance(B, Op) and _is_var(B.left) and _is_var(B.right):
            if A.name == B.right.name and B.left.name != B.right.name:
                return True
    return False


def f3_eq1_flag(p):
    """Both sides of Eq1 are binary products with same LEFT child but different
    RIGHT children. (Children may be trees, not just vars.)"""
    L, R = p["lhs"], p["rhs"]
    if not (isinstance(L, Op) and isinstance(R, Op)):
        return False
    return tree_eq(L.left, R.left) and not tree_eq(L.right, R.right)


def f4_eq1_flag(p):
    """Both sides of Eq1 are binary products with same RIGHT child but different
    LEFT children."""
    L, R = p["lhs"], p["rhs"]
    if not (isinstance(L, Op) and isinstance(R, Op)):
        return False
    return tree_eq(L.right, R.right) and not tree_eq(L.left, R.left)


def lp_flag(p):
    """LP(E): leftmost leaves of L and R agree."""
    return leftmost(p["lhs"]) == leftmost(p["rhs"])


def rp_flag(p):
    return rightmost(p["lhs"]) == rightmost(p["rhs"])


def f3_eq2_flag(p):
    """For B: pair (leftmost leaf, left depth) matches on the two sides."""
    return (leftmost(p["lhs"]) == leftmost(p["rhs"])
            and left_depth(p["lhs"]) == left_depth(p["rhs"]))


def f4_eq2_flag(p):
    return (rightmost(p["lhs"]) == rightmost(p["rhs"])
            and right_depth(p["lhs"]) == right_depth(p["rhs"]))


# ---------------------------------------------------------------------------
# 4. Affine probes
# ---------------------------------------------------------------------------

def _affine_form(node, var_index, p, q, c, m):
    """Return (coeffs, const) where coeffs is a tuple of length len(var_index)
    and const is an int, all mod m."""
    if isinstance(node, Var):
        idx = var_index[node.name]
        coeffs = [0] * len(var_index)
        coeffs[idx] = 1 % m
        return tuple(coeffs), 0 % m
    pv, pc = _affine_form(node.left, var_index, p, q, c, m)
    qv, qc = _affine_form(node.right, var_index, p, q, c, m)
    out = tuple((p * a + q * b) % m for a, b in zip(pv, qv))
    const = (p * pc + q * qc + c) % m
    return out, const


def affine_holds_eq(p_eq, p, q, c, m):
    """For a single equation (lhs = rhs), return True iff the affine forms
    of LHS and RHS agree (i.e. the equation holds as a polynomial identity
    under the affine probe)."""
    lhs, rhs = p_eq["lhs"], p_eq["rhs"]
    vs = all_vars(lhs) | all_vars(rhs)
    var_index = {v: i for i, v in enumerate(sorted(vs))}
    if not var_index:
        return True
    fl = _affine_form(lhs, var_index, p, q, c, m)
    fr = _affine_form(rhs, var_index, p, q, c, m)
    return fl == fr


# ---------------------------------------------------------------------------
# 5. Step 4 features (kind, shortest_len, occ, dup, vars, bare)
# ---------------------------------------------------------------------------

def _all_paths(node, var_name, prefix=""):
    """Return list of path-strings ('L'/'R') from root to each occurrence of
    `var_name`."""
    if isinstance(node, Var):
        return [prefix] if node.name == var_name else []
    return (_all_paths(node.left, var_name, prefix + "L")
            + _all_paths(node.right, var_name, prefix + "R"))


def step4_features(p):
    """Compute (kind, shortest_len, occ, dup, vars, bare, lp, rp) for an eq."""
    L, R = p["lhs"], p["rhs"]
    leafL = leaves(L)
    leafR = leaves(R)
    vars_set = set(leafL) | set(leafR)
    n_vars = len(vars_set)
    dup = (len(leafL) + len(leafR)) - n_vars
    LP = leftmost(L) == leftmost(R)
    RP = rightmost(L) == rightmost(R)

    # Bare detection
    bare = False
    bare_var = None
    nonbare_side = None
    if _is_var(L) and not _is_var(R):
        bare = True
        bare_var = L.name
        nonbare_side = R
    elif _is_var(R) and not _is_var(L):
        bare = True
        bare_var = R.name
        nonbare_side = L

    if not bare:
        return {
            "kind": "N",
            "shortest_len": -1,
            "occ": 0,
            "dup": dup,
            "vars": n_vars,
            "bare": False,
            "lp": LP,
            "rp": RP,
        }

    # bare case — gather all occurrence paths in non-bare side (using L/R from
    # the *equation's* L and R sides).  Per pi.txt, "all occurrence paths of x
    # in non-bare side (using L and R)"; non-bare side here is a single tree,
    # so we recurse into it tracking L/R edges.
    paths = _all_paths(nonbare_side, bare_var, "")

    if not paths:
        return {
            "kind": "X",
            "shortest_len": -1,
            "occ": 0,
            "dup": dup,
            "vars": n_vars,
            "bare": True,
            "lp": LP,
            "rp": RP,
        }

    # First path = leftmost-DFS first occurrence (the order returned by
    # _all_paths is left-to-right DFS, so paths[0] is "first").
    first = paths[0]
    if all(ch == "L" for ch in first):
        kind = "L"
    elif all(ch == "R" for ch in first):
        kind = "R"
    else:
        kind = "M"
    shortest_len = min(len(p_) for p_ in paths)
    occ = len(paths)
    return {
        "kind": kind,
        "shortest_len": shortest_len,
        "occ": occ,
        "dup": dup,
        "vars": n_vars,
        "bare": True,
        "lp": LP,
        "rp": RP,
    }


# ---------------------------------------------------------------------------
# 6. Per-equation feature tables (used both for split and full-ETP)
# ---------------------------------------------------------------------------

def _per_eq_features(ctx: ETPContext):
    n = ctx.n_eq
    parsed = ctx.parsed

    # Step 1 / Step 2 source flags
    x1_eq2 = np.array([x1_eq2_flag(p) for p in parsed], dtype=bool)
    x3_eq1 = np.array([x3_eq1_flag(p) for p in parsed], dtype=bool)

    f1_eq1 = np.array([f1_eq1_flag(p) for p in parsed], dtype=bool)
    f2_eq1 = np.array([f2_eq1_flag(p) for p in parsed], dtype=bool)
    f3_eq1 = np.array([f3_eq1_flag(p) for p in parsed], dtype=bool)
    f4_eq1 = np.array([f4_eq1_flag(p) for p in parsed], dtype=bool)

    # Eq2-side condition flags
    LP = np.array([lp_flag(p) for p in parsed], dtype=bool)
    RP = np.array([rp_flag(p) for p in parsed], dtype=bool)
    f3_eq2 = np.array([f3_eq2_flag(p) for p in parsed], dtype=bool)
    f4_eq2 = np.array([f4_eq2_flag(p) for p in parsed], dtype=bool)

    # X2 canonical equation form
    x2_canon = np.empty(n, dtype=object)
    for i, p in enumerate(parsed):
        x2_canon[i] = canonicalize_equation(p["lhs"], p["rhs"])

    # Affine probe holds-vectors
    aff_holds = {}
    for name, (p_, q_, c_, m_) in A_PROBES:
        vec = np.zeros(n, dtype=bool)
        for i, eq in enumerate(parsed):
            vec[i] = affine_holds_eq(eq, p_, q_, c_, m_)
        aff_holds[name] = vec

    # Step 4 features per equation
    s4 = [step4_features(p) for p in parsed]
    s4_kind = np.array([d["kind"] for d in s4])  # 'L','R','M','X','N'
    s4_len = np.array([d["shortest_len"] for d in s4], dtype=np.int32)
    s4_occ = np.array([d["occ"] for d in s4], dtype=np.int32)
    s4_dup = np.array([d["dup"] for d in s4], dtype=np.int32)
    s4_vars = np.array([d["vars"] for d in s4], dtype=np.int32)
    s4_bare = np.array([d["bare"] for d in s4], dtype=bool)

    return {
        "x1_eq2": x1_eq2,
        "x3_eq1": x3_eq1,
        "f1_eq1": f1_eq1, "f2_eq1": f2_eq1,
        "f3_eq1": f3_eq1, "f4_eq1": f4_eq1,
        "LP": LP, "RP": RP,
        "f3_eq2": f3_eq2, "f4_eq2": f4_eq2,
        "x2_canon": x2_canon,
        "aff_holds": aff_holds,
        "s4_kind": s4_kind,
        "s4_len": s4_len,
        "s4_occ": s4_occ,
        "s4_dup": s4_dup,
        "s4_vars": s4_vars,
        "s4_bare": s4_bare,
        "s4_dicts": s4,
    }


# ---------------------------------------------------------------------------
# 7. Scalar predict (for per-split runs; need to handle out-of-range eq IDs
#    from evaluation_order5 etc. by recomputing features on the fly)
# ---------------------------------------------------------------------------

def _features_for_eq(p):
    """Compute the small per-equation feature dict needed by predict_scalar."""
    return {
        "x1_eq2": x1_eq2_flag(p),
        "x3_eq1": x3_eq1_flag(p),
        "f1_eq1": f1_eq1_flag(p),
        "f2_eq1": f2_eq1_flag(p),
        "f3_eq1": f3_eq1_flag(p),
        "f4_eq1": f4_eq1_flag(p),
        "lp": lp_flag(p),
        "rp": rp_flag(p),
        "f3_eq2": f3_eq2_flag(p),
        "f4_eq2": f4_eq2_flag(p),
        "x2_canon": canonicalize_equation(p["lhs"], p["rhs"]),
        "aff_holds": {name: affine_holds_eq(p, *probe)
                      for name, probe in A_PROBES},
        "s4": step4_features(p),
    }


def predict_scalar(p1f, p2f):
    # Step 1
    if p1f["x1_eq2"] is None:
        pass
    if p2f["x1_eq2"]:
        return "X1"
    if p1f["x2_canon"] == p2f["x2_canon"]:
        return "X2"
    if p1f["x3_eq1"]:
        return "X3"

    # Step 2 — F-rules. Cascade order (F1 before F2 before F3 before F4)
    if p1f["f1_eq1"]:
        return "F1_TRUE" if p2f["lp"] else "F1_FALSE"
    if p1f["f2_eq1"]:
        return "F2_TRUE" if p2f["rp"] else "F2_FALSE"
    if p1f["f3_eq1"]:
        return "F3_TRUE" if p2f["f3_eq2"] else "F3_FALSE"
    if p1f["f4_eq1"]:
        return "F4_TRUE" if p2f["f4_eq2"] else "F4_FALSE"

    # Step 3 — Affine. For each probe in order, if A.lhs and A.rhs match
    # under the probe (holds_eq[i]) and B's forms differ (holds_eq[j] is
    # False), return that probe's name (FALSE).
    for name, _ in A_PROBES:
        if p1f["aff_holds"][name] and not p2f["aff_holds"][name]:
            return name

    # Step 4 — H1..H6
    s = p1f["s4"]
    t = p2f["s4"]
    s_kind, s_len, s_occ = s["kind"], s["shortest_len"], s["occ"]
    s_dup, s_vars, s_bare = s["dup"], s["vars"], s["bare"]
    rp_a = s["rp"]
    t_kind, t_occ, t_vars = t["kind"], t["occ"], t["vars"]
    t_dup, t_bare = t["dup"], t["bare"]

    # H1: s_kind = M, s_vars >= 4, t_kind = X
    if s_kind == "M" and s_vars >= 4 and t_kind == "X":
        return "H1"
    # H2: s_kind = L, s_len = 1, s_dup >= 3, t_bare = FALSE, t_dup >= 3, t_vars <= 3
    if (s_kind == "L" and s_len == 1 and s_dup >= 3
            and (not t_bare) and t_dup >= 3 and t_vars <= 3):
        return "H2"
    # H3: s_kind = M, s_occ = 2, RP(A) false
    if s_kind == "M" and s_occ == 2 and (not rp_a):
        return "H3"
    # H4: s_len = 1, s_occ = 3
    if s_len == 1 and s_occ == 3:
        return "H4"
    # H5: s_kind = M, s_len = 3, s_occ = 2
    if s_kind == "M" and s_len == 3 and s_occ == 2:
        return "H5"
    # H6: s_kind = L, t_occ = 2, t_vars = 4
    if s_kind == "L" and t_occ == 2 and t_vars == 4:
        return "H6"

    return "DEFAULT_TRUE"


# ---------------------------------------------------------------------------
# 8. Per-split runner
# ---------------------------------------------------------------------------

def run_on_split(stem: str, ctx: ETPContext, ctx_features_cache: dict) -> dict:
    """ctx_features_cache: dict i -> _features_for_eq(parsed[i]); built lazily.
    For out-of-range IDs (e.g. evaluation_order5), we parse equations from the
    split row's own strings."""
    problems = load_split(stem)
    rows = []
    for p in problems:
        i_id = p["eq1_id"]
        j_id = p["eq2_id"]
        i = i_id - 1
        j = j_id - 1
        if 0 <= i < ctx.n_eq:
            if i not in ctx_features_cache:
                ctx_features_cache[i] = _features_for_eq(ctx.parsed[i])
            p1f = ctx_features_cache[i]
        else:
            p1 = _parse_eq(p["equation1"])
            p1f = _features_for_eq(p1)
        if 0 <= j < ctx.n_eq:
            if j not in ctx_features_cache:
                ctx_features_cache[j] = _features_for_eq(ctx.parsed[j])
            p2f = ctx_features_cache[j]
        else:
            p2 = _parse_eq(p["equation2"])
            p2f = _features_for_eq(p2)
        rule = predict_scalar(p1f, p2f)
        pred = rule in TRUE_RULES
        gold = bool(p["answer"])
        rows.append({
            "id": p.get("id"),
            "eq1_id": i_id,
            "eq2_id": j_id,
            "gold": gold,
            "rule": rule,
            "pred": pred,
            "correct": pred == gold,
        })
    return summarize(rows, RULE_ORDER, TRUE_RULES, dataset_name=stem)


# ---------------------------------------------------------------------------
# 9. Vectorized full-ETP runner
# ---------------------------------------------------------------------------

def build_fires_for_rule(ctx: ETPContext, feats: dict):
    n = ctx.n_eq

    # X2 mask: i and j share the same canonical form
    canon_to_i = {}
    for i, c in enumerate(feats["x2_canon"]):
        canon_to_i.setdefault(c, []).append(i)

    x2_mask_cache = {"m": None}

    def get_x2_mask():
        if x2_mask_cache["m"] is not None:
            return x2_mask_cache["m"]
        m = np.zeros((n, n), dtype=bool)
        for canon, idxs in canon_to_i.items():
            arr = np.array(idxs, dtype=np.int64)
            ii, jj = np.meshgrid(arr, arr, indexing="ij")
            m[ii.ravel(), jj.ravel()] = True
        x2_mask_cache["m"] = m
        return m

    def fires_for_rule(name: str) -> np.ndarray:
        if name == "X1":
            return np.broadcast_to(feats["x1_eq2"][None, :], (n, n)).copy()
        if name == "X2":
            return get_x2_mask()
        if name == "X3":
            return np.broadcast_to(feats["x3_eq1"][:, None], (n, n)).copy()

        if name == "F1_TRUE":
            return feats["f1_eq1"][:, None] & feats["LP"][None, :]
        if name == "F1_FALSE":
            return feats["f1_eq1"][:, None] & ~feats["LP"][None, :]
        if name == "F2_TRUE":
            return feats["f2_eq1"][:, None] & feats["RP"][None, :]
        if name == "F2_FALSE":
            return feats["f2_eq1"][:, None] & ~feats["RP"][None, :]
        if name == "F3_TRUE":
            return feats["f3_eq1"][:, None] & feats["f3_eq2"][None, :]
        if name == "F3_FALSE":
            return feats["f3_eq1"][:, None] & ~feats["f3_eq2"][None, :]
        if name == "F4_TRUE":
            return feats["f4_eq1"][:, None] & feats["f4_eq2"][None, :]
        if name == "F4_FALSE":
            return feats["f4_eq1"][:, None] & ~feats["f4_eq2"][None, :]

        if name in feats["aff_holds"]:
            h = feats["aff_holds"][name]
            return h[:, None] & ~h[None, :]

        # Step 4 H rules — Eq1-only (or Eq1+Eq2-feature) predicates.
        s_kind = feats["s4_kind"]
        s_len = feats["s4_len"]
        s_occ = feats["s4_occ"]
        s_dup = feats["s4_dup"]
        s_vars = feats["s4_vars"]
        s_bare = feats["s4_bare"]
        # rp_a is the s4 entry's "rp" but stored only in dicts; compute array
        # from feats["RP"] (which is the per-equation RP value) — they're the
        # same definition.
        rp_a = feats["RP"]
        t_kind = s_kind  # alias when applied to j
        t_occ = s_occ
        t_vars = s_vars
        t_dup = s_dup
        t_bare = s_bare

        if name == "H1":
            flag_s = (s_kind == "M") & (s_vars >= 4)
            flag_t = (t_kind == "X")
            return flag_s[:, None] & flag_t[None, :]
        if name == "H2":
            flag_s = (s_kind == "L") & (s_len == 1) & (s_dup >= 3)
            flag_t = (~t_bare) & (t_dup >= 3) & (t_vars <= 3)
            return flag_s[:, None] & flag_t[None, :]
        if name == "H3":
            flag = (s_kind == "M") & (s_occ == 2) & (~rp_a)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "H4":
            flag = (s_len == 1) & (s_occ == 3)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "H5":
            flag = (s_kind == "M") & (s_len == 3) & (s_occ == 2)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "H6":
            flag_s = (s_kind == "L")
            flag_t = (t_occ == 2) & (t_vars == 4)
            return flag_s[:, None] & flag_t[None, :]
        if name == "DEFAULT_TRUE":
            return np.ones((n, n), dtype=bool)
        raise KeyError(f"Unknown rule {name!r}")

    return fires_for_rule


def run_full_etp_summary(ctx: ETPContext, feats: dict | None = None) -> dict:
    if feats is None:
        feats = _per_eq_features(ctx)
    fires_for_rule = build_fires_for_rule(ctx, feats)
    return run_full_etp(ctx, fires_for_rule, RULE_ORDER, TRUE_RULES,
                        progress_label="pi-ETP")


# ---------------------------------------------------------------------------
# 10. Driver
# ---------------------------------------------------------------------------

def _md_table_for_split(s: dict) -> str:
    n, nc = s["n"], s["n_correct"]
    cf = s["confusion"]
    out = [f"### `{s['dataset']}`  —  accuracy {nc}/{n} = {nc/n*100:.2f}%"]
    out.append(f"")
    out.append(f"Confusion: TP={cf['tp']}, FP={cf['fp']}, TN={cf['tn']}, FN={cf['fn']}")
    out.append(f"")
    out.append("| rule | verdict | fires | correct | wrong | precision |")
    out.append("|------|---------|------:|--------:|------:|----------:|")
    for rule in s["rule_order"]:
        bs = s["by_rule"].get(rule, {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0})
        if bs["n"] == 0:
            continue
        verdict = "TRUE" if rule in s["true_rules"] else "FALSE"
        correct = bs["tp"] + bs["tn"]
        wrong = bs["fp"] + bs["fn"]
        prec = correct / bs["n"] * 100
        out.append(f"| {rule} | {verdict} | {bs['n']} | {correct} | {wrong} | {prec:.1f}% |")
    out.append("")
    return "\n".join(out)


def main():
    out_dir = ROOT / "analysis" / "results" / "pi"
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.stderr.write("Loading ETP context (parse + compile + gold)...\n")
    t0 = time.time()
    ctx = load_etp_context(load_gold=True)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s "
                     f"(n_eq={ctx.n_eq}, gold loaded={ctx.gold is not None})\n")

    sys.stderr.write("Computing per-equation features (Step 1-4 invariants)...\n")
    t0 = time.time()
    feats = _per_eq_features(ctx)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s\n")

    summaries = {}

    sys.stderr.write("\n=== Splits ===\n")
    feature_cache: dict = {}  # i -> per-eq feature dict
    for stem in SPLITS:
        sys.stderr.write(f"  running {stem}...\n")
        s = run_on_split(stem, ctx, feature_cache)
        save_summary(s, out_dir / f"{stem}.json", drop_rows=False)
        summaries[stem] = {k: v for k, v in s.items() if k != "rows"}
        print_summary(s)

    sys.stderr.write("\n=== Full ETP (4694x4694 = 22M pairs) ===\n")
    t0 = time.time()
    full = run_full_etp_summary(ctx, feats)
    sys.stderr.write(f"  full ETP done in {time.time()-t0:.1f}s\n")
    save_summary(full, out_dir / "full_etp.json", drop_rows=True)
    if not full.get("skipped"):
        summaries["full_etp"] = full
    print_summary(full)

    combined = {
        "splits": {stem: summaries[stem] for stem in SPLITS},
        "full_etp": full,
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(combined, f, indent=2)

    md = ["# pi.txt programmatic checker — summary", ""]
    md.append("## Overall accuracy")
    md.append("")
    md.append("| dataset | n | accuracy |")
    md.append("|---------|--:|---------:|")
    for stem in SPLITS:
        s = summaries[stem]
        md.append(f"| {stem} | {s['n']} | {s['n_correct']}/{s['n']} = {s['n_correct']/s['n']*100:.2f}% |")
    md.append(f"| full_etp | {full['n']} | {full['n_correct']}/{full['n']} = {full['n_correct']/full['n']*100:.4f}% |")
    md.append("")
    md.append("## Per-split rule breakdown")
    md.append("")
    for stem in SPLITS:
        md.append(_md_table_for_split(summaries[stem]))
    md.append("## Full ETP rule breakdown")
    md.append("")
    md.append(_md_table_for_split(full))

    with open(out_dir / "SUMMARY.md", "w") as f:
        f.write("\n".join(md))

    sys.stderr.write(f"\nResults saved to {out_dir}\n")


if __name__ == "__main__":
    main()
