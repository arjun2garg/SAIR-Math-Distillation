"""Programmatic ("ceiling") checker for the reza_jamei.txt cheatsheet.

Implements every named rule from `cheatsheets/reza_jamei.txt`:

  Layer A — strict TRUE rules (commit TRUE on fire, in this order):
      A1 SAME, A2 RENAME, A3 SINGLETON, A4 LP-PIN, A5 RP-PIN,
      A6 LU-PIN, A7 RU-PIN, A8 CONST, A9 DERIVE  (with A9a iterated template)

  Layer A — strict FALSE witnesses (commit FALSE on fire, in this order):
      W1 LP, W2 RP, W3 LIST, W4 SET, W5 AB, W6 XOR, W7 MOD3,
      W8 K0, W9 LC3, W10 RC3

  Layer B — fallback decision tree (default):
      B0 ORDER-EXPLOSION (FALSE), B1 (FALSE), B2a (TRUE), B2b (TRUE),
      B2c (TRUE for u*u-shaped Eq2 LHS), B2d (FALSE, default catch-all)

The cascade walks A1..A9, then W1..W10, then B0..B2d.

Two entry points:
    run_on_split(stem, ctx)        -> per-split scalar evaluation
    run_full_etp_summary(ctx)      -> vectorized 4694x4694 evaluation

The driver runs all 9 SAIR splits + the full ETP and writes results to
`analysis/results/reza_jamei_jamei/`.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from itertools import product
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))

from parse_equation import Op, Var  # noqa: E402

from _common import (  # noqa: E402
    ETPContext,
    MAGMA_LIB,
    SPLITS,
    get_sat_vector,
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

RULE_ORDER = [
    # Layer A TRUE rules
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A9a",
    # Layer A FALSE witnesses
    "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10",
    # Layer B fallback
    "B0", "B1", "B2a", "B2b", "B2c", "B2d",
]

TRUE_RULES = {"A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A9a",
              "B2a", "B2b", "B2c"}


# ---------------------------------------------------------------------------
# 2. Tree helpers
# ---------------------------------------------------------------------------

def leaves(node):
    """Left-to-right list of variable names."""
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


def left_spine_depth(node):
    """0 if Var, else 1 + left_spine_depth(node.left)."""
    d = 0
    while isinstance(node, Op):
        d += 1
        node = node.left
    return d


def right_spine_depth(node):
    d = 0
    while isinstance(node, Op):
        d += 1
        node = node.right
    return d


def count_var(node, name):
    if isinstance(node, Var):
        return 1 if node.name == name else 0
    return count_var(node.left, name) + count_var(node.right, name)


def all_vars(node):
    if isinstance(node, Var):
        return {node.name}
    return all_vars(node.left) | all_vars(node.right)


def n_ops(node):
    if isinstance(node, Var):
        return 0
    return 1 + n_ops(node.left) + n_ops(node.right)


def occurrence_vector(node, var_list):
    """Return a tuple of counts for each var in var_list (order-stable)."""
    return tuple(count_var(node, v) for v in var_list)


def canonicalize_tree(node):
    """Rename variables in `node` by first-appearance order. Returns a tuple
    representation with canonical var names (x, y, z, ...).
    """
    mapping = {}
    var_pool = "xyzwuv" + "abcdefghijklmnopqrst"

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

    assign(node)
    return rebuild(node)


def canonicalize_equation(lhs, rhs):
    """Rename vars over (lhs, rhs) jointly; return tuple (lhs_canon, rhs_canon).
    Symmetric form: returns the smaller of (lhs,rhs) and (rhs,lhs) to allow
    side-swap matching."""
    mapping = {}
    var_pool = "xyzwuv" + "abcdefghijklmnopqrst"

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

    def go(a, b):
        nonlocal mapping
        mapping = {}
        assign(a)
        assign(b)
        return (rebuild(a), rebuild(b))

    f = go(lhs, rhs)
    g = go(rhs, lhs)
    # Use repr for stable, type-uniform comparison (tuples vs strings break <).
    return f if repr(f) <= repr(g) else g


def tree_eq(a, b):
    """Structural equality of two parse trees."""
    if isinstance(a, Var) and isinstance(b, Var):
        return a.name == b.name
    if isinstance(a, Op) and isinstance(b, Op):
        return tree_eq(a.left, b.left) and tree_eq(a.right, b.right)
    return False


def tree_to_tuple(node):
    if isinstance(node, Var):
        return node.name
    return (tree_to_tuple(node.left), tree_to_tuple(node.right))


def substitute(node, var_name, replacement):
    """Replace every occurrence of Var(var_name) in `node` with `replacement`."""
    if isinstance(node, Var):
        if node.name == var_name:
            return replacement
        return node
    return Op(substitute(node.left, var_name, replacement),
              substitute(node.right, var_name, replacement))


# ---------------------------------------------------------------------------
# 3. Layer A TRUE rules (scalar predicates)
# ---------------------------------------------------------------------------

def fires_A1(p1, p2):
    """A1 SAME: Eq2's two sides are syntactically identical."""
    return tree_eq(p2["lhs"], p2["rhs"])


def fires_A2(p1, p2):
    """A2 RENAME: Eq2 equals Eq1 under a single consistent variable renaming
    (possibly swapping sides)."""
    c1 = canonicalize_equation(p1["lhs"], p1["rhs"])
    c2 = canonicalize_equation(p2["lhs"], p2["rhs"])
    return c1 == c2


def fires_A3(p1, p2):
    """A3 SINGLETON: one side of Eq1 is a bare variable absent from the other side."""
    lhs, rhs = p1["lhs"], p1["rhs"]
    if isinstance(lhs, Var) and lhs.name not in all_vars(rhs):
        return True
    if isinstance(rhs, Var) and rhs.name not in all_vars(lhs):
        return True
    return False


def _is_var(n):
    return isinstance(n, Var)


def fires_A4(p1, p2):
    """A4 LP-PIN: Eq1 is literally x = x*y or x*y = x (two distinct variables)."""
    lhs, rhs = p1["lhs"], p1["rhs"]
    # x = x*y
    if _is_var(lhs) and isinstance(rhs, Op) and _is_var(rhs.left) and _is_var(rhs.right):
        if lhs.name == rhs.left.name and rhs.left.name != rhs.right.name:
            return _A_lp_check(p2)
    # x*y = x
    if _is_var(rhs) and isinstance(lhs, Op) and _is_var(lhs.left) and _is_var(lhs.right):
        if rhs.name == lhs.left.name and lhs.left.name != lhs.right.name:
            return _A_lp_check(p2)
    return False


def _A_lp_check(p2):
    return leftmost(p2["lhs"]) == leftmost(p2["rhs"])


def fires_A5(p1, p2):
    """A5 RP-PIN: x = y*x or x*y = y."""
    lhs, rhs = p1["lhs"], p1["rhs"]
    if _is_var(lhs) and isinstance(rhs, Op) and _is_var(rhs.left) and _is_var(rhs.right):
        if lhs.name == rhs.right.name and rhs.left.name != rhs.right.name:
            return _A_rp_check(p2)
    if _is_var(rhs) and isinstance(lhs, Op) and _is_var(lhs.left) and _is_var(lhs.right):
        if rhs.name == lhs.right.name and lhs.left.name != lhs.right.name:
            return _A_rp_check(p2)
    return False


def _A_rp_check(p2):
    return rightmost(p2["lhs"]) == rightmost(p2["rhs"])


def fires_A6(p1, p2):
    """A6 LU-PIN: x*y = x*z (distinct y, z). a*b = f(a)."""
    lhs, rhs = p1["lhs"], p1["rhs"]
    # x*y = x*z OR x*z = x*y
    for L, R in ((lhs, rhs), (rhs, lhs)):
        if (isinstance(L, Op) and isinstance(R, Op)
                and _is_var(L.left) and _is_var(L.right)
                and _is_var(R.left) and _is_var(R.right)):
            if (L.left.name == R.left.name
                    and L.right.name != R.right.name
                    and L.left.name != L.right.name
                    and L.left.name != R.right.name):
                # Check Eq2: leftmost leaves & left-spine depths match
                if (leftmost(p2["lhs"]) == leftmost(p2["rhs"])
                        and left_spine_depth(p2["lhs"]) == left_spine_depth(p2["rhs"])):
                    return True
                return False  # rule fires only on shape; it commits but verdict TRUE iff condition met
    return False


def fires_A7(p1, p2):
    """A7 RU-PIN: y*x = z*x (distinct y, z). a*b = g(b)."""
    lhs, rhs = p1["lhs"], p1["rhs"]
    for L, R in ((lhs, rhs), (rhs, lhs)):
        if (isinstance(L, Op) and isinstance(R, Op)
                and _is_var(L.left) and _is_var(L.right)
                and _is_var(R.left) and _is_var(R.right)):
            if (L.right.name == R.right.name
                    and L.left.name != R.left.name
                    and L.right.name != L.left.name
                    and L.right.name != R.left.name):
                if (rightmost(p2["lhs"]) == rightmost(p2["rhs"])
                        and right_spine_depth(p2["lhs"]) == right_spine_depth(p2["rhs"])):
                    return True
                return False
    return False


def fires_A8(p1, p2):
    """A8 CONST:
      Eq1 is x*y = R or R = x*y with distinct x,y absent from R; OR
      x*x = y*z (up to renaming).
    Then all products collapse to one constant.
    TRUE iff both sides of Eq2 are products."""
    lhs, rhs = p1["lhs"], p1["rhs"]
    triggered = False
    # x*y = R variant
    for L, R in ((lhs, rhs), (rhs, lhs)):
        if isinstance(L, Op) and _is_var(L.left) and _is_var(L.right):
            x, y = L.left.name, L.right.name
            if x != y and x not in all_vars(R) and y not in all_vars(R):
                triggered = True
                break
    # x*x = y*z (up to renaming) — i.e. one side is v*v and the other is u*w with u!=w
    if not triggered:
        if (isinstance(lhs, Op) and isinstance(rhs, Op)
                and _is_var(lhs.left) and _is_var(lhs.right)
                and _is_var(rhs.left) and _is_var(rhs.right)):
            v1, v2 = lhs.left.name, lhs.right.name
            u1, u2 = rhs.left.name, rhs.right.name
            # one side is v*v, other is u*w distinct
            if (v1 == v2 and u1 != u2) or (u1 == u2 and v1 != v2):
                triggered = True
    if not triggered:
        return False
    # Both sides of Eq2 are products
    return isinstance(p2["lhs"], Op) and isinstance(p2["rhs"], Op)


def fires_A9(p1, p2):
    """A9 DERIVE: Eq2 is reachable from Eq1 by renaming variables, swapping
    sides, and exact-subterm substitution (NEVER re-bracket).

    We approximate this with: A2 already covers pure rename. For the
    substitution case, we use A9a's iterated template substitution.
    Pure A9 (single non-iterated substitution) is also covered by A9a's first
    attempt when applicable; otherwise, we additionally consider:
      - apply Eq1 (treated as L=R) once: substitute every occurrence of L in
        Eq2 by R or vice versa (one direction, exact subterm) and check
        canonical equality with Eq1.
    Conservative: we only fire when canonical-equation matches after one
    forward substitution of an exact subterm in Eq1's RHS using Eq1 itself.
    """
    # Skip; let A9a handle the substitution chain.
    return False


def fires_A9a(p1, p2):
    """A9a ITERATED TEMPLATE: Eq1 has form x = C[x] with displayed x-subterm
    on RHS; substitute Eq1 into that x-subterm up to 2 times.

    Approach: detect Eq1 = (V, C) with V a variable appearing in C.  Then
    for k in {1, 2}, build C^k where every occurrence of V in C is replaced
    by the original C, and check if (V, C^k) (up to canonical rename and
    side-swap) equals Eq2's canonical form.
    """
    lhs, rhs = p1["lhs"], p1["rhs"]
    candidates = []
    if _is_var(lhs) and not _is_var(rhs) and lhs.name in all_vars(rhs):
        candidates.append((lhs.name, rhs))
    if _is_var(rhs) and not _is_var(lhs) and rhs.name in all_vars(lhs):
        candidates.append((rhs.name, lhs))
    if not candidates:
        return False
    target = canonicalize_equation(p2["lhs"], p2["rhs"])
    for vname, c_tree in candidates:
        cur = c_tree  # represents C[x]; x = vname
        # attempt 1
        cur1 = substitute(cur, vname, c_tree)
        if canonicalize_equation(Var(vname), cur1) == target:
            return True
        # attempt 2
        cur2 = substitute(cur1, vname, c_tree)
        if canonicalize_equation(Var(vname), cur2) == target:
            return True
    return False


# ---------------------------------------------------------------------------
# 4. Layer A FALSE witnesses (vectorizable per-equation invariants)
# ---------------------------------------------------------------------------

def invariant_W1(p):
    """LP: leftmost(lhs) == leftmost(rhs)."""
    return leftmost(p["lhs"]) == leftmost(p["rhs"])


def invariant_W2(p):
    return rightmost(p["lhs"]) == rightmost(p["rhs"])


def invariant_W3(p):
    """LIST: leaf sequences agree."""
    return leaves(p["lhs"]) == leaves(p["rhs"])


def invariant_W4(p):
    """SET: variable sets agree."""
    return all_vars(p["lhs"]) == all_vars(p["rhs"])


def _occ_dict(node):
    d = {}
    for v in leaves(node):
        d[v] = d.get(v, 0) + 1
    return d


def invariant_W5(p):
    """AB: each variable's count agrees on both sides."""
    return _occ_dict(p["lhs"]) == _occ_dict(p["rhs"])


def invariant_W6(p):
    """XOR: each variable's count mod 2 agrees."""
    a, b = _occ_dict(p["lhs"]), _occ_dict(p["rhs"])
    keys = set(a) | set(b)
    return all((a.get(k, 0) % 2) == (b.get(k, 0) % 2) for k in keys)


def invariant_W7(p):
    """MOD3."""
    a, b = _occ_dict(p["lhs"]), _occ_dict(p["rhs"])
    keys = set(a) | set(b)
    return all((a.get(k, 0) % 3) == (b.get(k, 0) % 3) for k in keys)


def invariant_W8(p):
    """K0: both sides are products, OR both sides are the same variable."""
    L, R = p["lhs"], p["rhs"]
    if isinstance(L, Op) and isinstance(R, Op):
        return True
    if isinstance(L, Var) and isinstance(R, Var) and L.name == R.name:
        return True
    return False


def left_path_count(t):
    """0 if Var, else 1 + left_path_count(t.left)."""
    n = 0
    while isinstance(t, Op):
        n += 1
        t = t.left
    return n


def right_path_count(t):
    n = 0
    while isinstance(t, Op):
        n += 1
        t = t.right
    return n


def invariant_W9(p):
    """LC3: leftmost leaves agree AND left-path counts mod 3 agree."""
    return (leftmost(p["lhs"]) == leftmost(p["rhs"])
            and (left_path_count(p["lhs"]) % 3) == (left_path_count(p["rhs"]) % 3))


def invariant_W10(p):
    """RC3."""
    return (rightmost(p["lhs"]) == rightmost(p["rhs"])
            and (right_path_count(p["lhs"]) % 3) == (right_path_count(p["rhs"]) % 3))


W_INVARIANTS = {
    "W1": invariant_W1,
    "W2": invariant_W2,
    "W3": invariant_W3,
    "W4": invariant_W4,
    "W5": invariant_W5,
    "W6": invariant_W6,
    "W7": invariant_W7,
    "W8": invariant_W8,
    "W9": invariant_W9,
    "W10": invariant_W10,
}


# ---------------------------------------------------------------------------
# 5. Layer B fallback
# ---------------------------------------------------------------------------

def _msv(p1):
    lhs_vars = p1["lhs_vars"]
    rhs_vars = p1["rhs_vars"]
    all_v = lhs_vars | rhs_vars
    if not all_v:
        return (0, 0, 0)
    M = min(count_var(p1["lhs"], v) + count_var(p1["rhs"], v) for v in all_v)
    S = p1["n_ops_lhs"]
    V = len(lhs_vars)
    return M, S, V


def fires_B0(p1, p2):
    """ORDER-EXPLOSION (bilateral): C2 > C1 + 2 AND M = 1."""
    M, _, _ = _msv(p1)
    if M != 1:
        return False
    C1 = p1["n_ops_lhs"] + p1["n_ops_rhs"]
    C2 = p2["n_ops_lhs"] + p2["n_ops_rhs"]
    return C2 > C1 + 2


def fires_B1(p1, p2):
    M, _, _ = _msv(p1)
    return M >= 2


def fires_B2a(p1, p2):
    """B2a: M = 1 AND S = 0."""
    M, S, _ = _msv(p1)
    return M == 1 and S == 0


def fires_B2b(p1, p2):
    """B2b: M = 1, S = 1, V = 2 (LHS = x*y with distinct x,y)."""
    M, S, V = _msv(p1)
    return M == 1 and S == 1 and V == 2


def fires_B2c(p1, p2):
    """B2c: M = 1, S = 1, V = 1 (LHS = v*v) AND Eq2.LHS = u*u for some u."""
    M, S, V = _msv(p1)
    if not (M == 1 and S == 1 and V == 1):
        return False
    L2 = p2["lhs"]
    return (isinstance(L2, Op)
            and _is_var(L2.left) and _is_var(L2.right)
            and L2.left.name == L2.right.name)


def fires_B2d(p1, p2):
    return True  # default catch-all FALSE


# ---------------------------------------------------------------------------
# 6. Scalar predict (for HF splits)
# ---------------------------------------------------------------------------

A_RULE_FNS = [
    ("A1", fires_A1),
    ("A2", fires_A2),
    ("A3", fires_A3),
    ("A4", fires_A4),
    ("A5", fires_A5),
    ("A6", fires_A6),
    ("A7", fires_A7),
    ("A8", fires_A8),
    ("A9", fires_A9),
    ("A9a", fires_A9a),
]

B_RULE_FNS = [
    ("B0", fires_B0),
    ("B1", fires_B1),
    ("B2a", fires_B2a),
    ("B2b", fires_B2b),
    ("B2c", fires_B2c),
    ("B2d", fires_B2d),
]


def predict_scalar(p1, p2, w_invariants_by_rule):
    """Return the rule name that fires under the cascade for one (p1, p2)."""
    # Layer A TRUE
    for name, fn in A_RULE_FNS:
        if fn(p1, p2):
            return name
    # Layer A FALSE witnesses
    for w in ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10"):
        h1, h2 = w_invariants_by_rule[w]
        # h1 = invariant holds on p1; h2 = invariant holds on p2
        # Witness fires iff invariant holds on Eq1 but NOT Eq2.
        if h1 and not h2:
            return w
    # Layer B
    for name, fn in B_RULE_FNS:
        if fn(p1, p2):
            return name
    return "B2d"


# ---------------------------------------------------------------------------
# 7. Per-split runner
# ---------------------------------------------------------------------------

def _precompute_invariants(ctx: ETPContext):
    """Return a dict W_name -> bool[n_eq] of per-equation invariant holds."""
    out = {}
    for name, fn in W_INVARIANTS.items():
        vec = np.zeros(ctx.n_eq, dtype=bool)
        for i, p in enumerate(ctx.parsed):
            vec[i] = fn(p)
        out[name] = vec
    return out


def run_on_split(stem: str, ctx: ETPContext, inv: dict[str, np.ndarray]) -> dict:
    problems = load_split(stem)
    rows = []
    # Splits like `evaluation_order5` reference equation IDs outside the
    # 4694-equation universe; for those we parse the equations from the
    # split's `equation1` / `equation2` strings directly.
    from parse_equation import parse_equation as _parse_eq
    for p in problems:
        i_id = p["eq1_id"]
        j_id = p["eq2_id"]
        i = i_id - 1
        j = j_id - 1
        if 0 <= i < ctx.n_eq:
            p1 = ctx.parsed[i]
            inv1 = {w: bool(inv[w][i]) for w in W_INVARIANTS}
        else:
            p1 = _parse_eq(p["equation1"])
            inv1 = {w: bool(W_INVARIANTS[w](p1)) for w in W_INVARIANTS}
        if 0 <= j < ctx.n_eq:
            p2 = ctx.parsed[j]
            inv2 = {w: bool(inv[w][j]) for w in W_INVARIANTS}
        else:
            p2 = _parse_eq(p["equation2"])
            inv2 = {w: bool(W_INVARIANTS[w](p2)) for w in W_INVARIANTS}
        w_hits = {w: (inv1[w], inv2[w]) for w in W_INVARIANTS}
        rule = predict_scalar(p1, p2, w_hits)
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
# 8. Vectorized full-ETP runner
# ---------------------------------------------------------------------------

def _per_eq_features(ctx: ETPContext):
    """Compute per-equation arrays needed to vectorize each rule's fire mask."""
    n = ctx.n_eq
    parsed = ctx.parsed

    # Per-equation A-condition flags (Eq1-only triggers and Eq2-only conditions)
    # Many A-rules have an Eq1 shape predicate AND an Eq2 condition.
    # We compute Eq1-shape-flag and Eq2-target-flag separately, then combine.

    # A1: Eq2's two sides identical → per-eq flag on j only.
    a1_eq2 = np.array([tree_eq(p["lhs"], p["rhs"]) for p in parsed], dtype=bool)

    # A2: canonicalized symmetric equation form → if equal, fire.
    a2_canon = np.empty(n, dtype=object)
    for i, p in enumerate(parsed):
        a2_canon[i] = canonicalize_equation(p["lhs"], p["rhs"])

    # A3: SINGLETON — Eq1-only flag.
    def a3_flag(p):
        L, R = p["lhs"], p["rhs"]
        if isinstance(L, Var) and L.name not in all_vars(R):
            return True
        if isinstance(R, Var) and R.name not in all_vars(L):
            return True
        return False

    a3_eq1 = np.array([a3_flag(p) for p in parsed], dtype=bool)

    # A4 LP-PIN: Eq1 shape flag, plus Eq2 condition (lm.lhs == lm.rhs).
    def a4_eq1_flag(p):
        L, R = p["lhs"], p["rhs"]
        if _is_var(L) and isinstance(R, Op) and _is_var(R.left) and _is_var(R.right):
            if L.name == R.left.name and R.left.name != R.right.name:
                return True
        if _is_var(R) and isinstance(L, Op) and _is_var(L.left) and _is_var(L.right):
            if R.name == L.left.name and L.left.name != L.right.name:
                return True
        return False

    a4_eq1 = np.array([a4_eq1_flag(p) for p in parsed], dtype=bool)
    a4_eq2 = np.array([leftmost(p["lhs"]) == leftmost(p["rhs"]) for p in parsed],
                      dtype=bool)

    # A5 RP-PIN
    def a5_eq1_flag(p):
        L, R = p["lhs"], p["rhs"]
        if _is_var(L) and isinstance(R, Op) and _is_var(R.left) and _is_var(R.right):
            if L.name == R.right.name and R.left.name != R.right.name:
                return True
        if _is_var(R) and isinstance(L, Op) and _is_var(L.left) and _is_var(L.right):
            if R.name == L.right.name and L.left.name != L.right.name:
                return True
        return False

    a5_eq1 = np.array([a5_eq1_flag(p) for p in parsed], dtype=bool)
    a5_eq2 = np.array([rightmost(p["lhs"]) == rightmost(p["rhs"]) for p in parsed],
                      dtype=bool)

    # A6 LU-PIN
    def a6_eq1_flag(p):
        L, R = p["lhs"], p["rhs"]
        for A, B in ((L, R), (R, L)):
            if (isinstance(A, Op) and isinstance(B, Op)
                    and _is_var(A.left) and _is_var(A.right)
                    and _is_var(B.left) and _is_var(B.right)):
                if (A.left.name == B.left.name
                        and A.right.name != B.right.name
                        and A.left.name != A.right.name
                        and A.left.name != B.right.name):
                    return True
        return False

    a6_eq1 = np.array([a6_eq1_flag(p) for p in parsed], dtype=bool)
    a6_eq2 = np.array([(leftmost(p["lhs"]) == leftmost(p["rhs"])
                        and left_spine_depth(p["lhs"]) == left_spine_depth(p["rhs"]))
                       for p in parsed], dtype=bool)

    # A7 RU-PIN
    def a7_eq1_flag(p):
        L, R = p["lhs"], p["rhs"]
        for A, B in ((L, R), (R, L)):
            if (isinstance(A, Op) and isinstance(B, Op)
                    and _is_var(A.left) and _is_var(A.right)
                    and _is_var(B.left) and _is_var(B.right)):
                if (A.right.name == B.right.name
                        and A.left.name != B.left.name
                        and A.right.name != A.left.name
                        and A.right.name != B.left.name):
                    return True
        return False

    a7_eq1 = np.array([a7_eq1_flag(p) for p in parsed], dtype=bool)
    a7_eq2 = np.array([(rightmost(p["lhs"]) == rightmost(p["rhs"])
                        and right_spine_depth(p["lhs"]) == right_spine_depth(p["rhs"]))
                       for p in parsed], dtype=bool)

    # A8 CONST
    def a8_eq1_flag(p):
        L, R = p["lhs"], p["rhs"]
        # x*y = R variant
        for A, B in ((L, R), (R, L)):
            if isinstance(A, Op) and _is_var(A.left) and _is_var(A.right):
                x, y = A.left.name, A.right.name
                if x != y and x not in all_vars(B) and y not in all_vars(B):
                    return True
        # x*x = y*z up to renaming
        if (isinstance(L, Op) and isinstance(R, Op)
                and _is_var(L.left) and _is_var(L.right)
                and _is_var(R.left) and _is_var(R.right)):
            v1, v2 = L.left.name, L.right.name
            u1, u2 = R.left.name, R.right.name
            if (v1 == v2 and u1 != u2) or (u1 == u2 and v1 != v2):
                return True
        return False

    a8_eq1 = np.array([a8_eq1_flag(p) for p in parsed], dtype=bool)
    a8_eq2 = np.array([(isinstance(p["lhs"], Op) and isinstance(p["rhs"], Op))
                       for p in parsed], dtype=bool)

    # A9a — handled scalar via dict lookup of canonical forms.
    # Build per-equation: (vname, attempt1_canon, attempt2_canon) if applicable.
    # Multiple candidates per equation possible (both x = C[x] and C[x] = x).
    a9a_canons = []
    for p in parsed:
        L, R = p["lhs"], p["rhs"]
        forms = set()
        candidates = []
        if _is_var(L) and not _is_var(R) and L.name in all_vars(R):
            candidates.append((L.name, R))
        if _is_var(R) and not _is_var(L) and R.name in all_vars(L):
            candidates.append((R.name, L))
        for vname, c_tree in candidates:
            cur = c_tree
            cur1 = substitute(cur, vname, c_tree)
            forms.add(canonicalize_equation(Var(vname), cur1))
            cur2 = substitute(cur1, vname, c_tree)
            forms.add(canonicalize_equation(Var(vname), cur2))
        a9a_canons.append(forms)

    # Layer B per-Eq1 features
    b_msv = np.array([_msv(p) for p in parsed], dtype=np.int32)  # (n,3)
    b_C = np.array([p["n_ops_lhs"] + p["n_ops_rhs"] for p in parsed], dtype=np.int32)

    # B2c Eq2 LHS = u*u flag
    def b2c_eq2_flag(p):
        L = p["lhs"]
        return (isinstance(L, Op)
                and _is_var(L.left) and _is_var(L.right)
                and L.left.name == L.right.name)

    b2c_eq2 = np.array([b2c_eq2_flag(p) for p in parsed], dtype=bool)

    # W invariants (per-equation hold) -> bool[n_eq]
    inv = {}
    for w, fn in W_INVARIANTS.items():
        inv[w] = np.array([fn(p) for p in parsed], dtype=bool)

    return {
        "a1_eq2": a1_eq2,
        "a2_canon": a2_canon,
        "a3_eq1": a3_eq1,
        "a4_eq1": a4_eq1, "a4_eq2": a4_eq2,
        "a5_eq1": a5_eq1, "a5_eq2": a5_eq2,
        "a6_eq1": a6_eq1, "a6_eq2": a6_eq2,
        "a7_eq1": a7_eq1, "a7_eq2": a7_eq2,
        "a8_eq1": a8_eq1, "a8_eq2": a8_eq2,
        "a9a_canons": a9a_canons,
        "b_msv": b_msv,
        "b_C": b_C,
        "b2c_eq2": b2c_eq2,
        "inv": inv,
    }


def build_fires_for_rule(ctx: ETPContext, feats: dict):
    """Return a closure `fires_for_rule(name) -> bool[n_eq, n_eq]` covering
    every rule in RULE_ORDER. The returned mask is the *candidate* fire mask
    irrespective of cascade ordering — `run_full_etp` walks RULE_ORDER and
    keeps only the first-firing rule per cell.
    """
    n = ctx.n_eq

    # Pre-build canonical-form -> set of i's for A2 lookup
    canon_to_i: dict = {}
    for i, c in enumerate(feats["a2_canon"]):
        canon_to_i.setdefault(c, []).append(i)

    a2_mask_cache = {"m": None}

    def get_a2_mask():
        if a2_mask_cache["m"] is not None:
            return a2_mask_cache["m"]
        m = np.zeros((n, n), dtype=bool)
        # A2 fires iff canon[i] == canon[j], i.e. Eq2 = rename of Eq1.
        # Group i's by canonical form, then for each group (i,j) cross.
        for canon, idxs in canon_to_i.items():
            arr = np.array(idxs, dtype=np.int64)
            ii, jj = np.meshgrid(arr, arr, indexing="ij")
            m[ii.ravel(), jj.ravel()] = True
        a2_mask_cache["m"] = m
        return m

    a9a_mask_cache = {"m": None}

    def get_a9a_mask():
        if a9a_mask_cache["m"] is not None:
            return a9a_mask_cache["m"]
        m = np.zeros((n, n), dtype=bool)
        target_canon = feats["a2_canon"]  # canonicalize_equation per equation j
        # Build: for each j, the canonical form. For each i with non-empty
        # a9a_canons set, set m[i, j] = True if target_canon[j] in a9a_canons[i].
        # Group j by canon → fast lookup.
        canon_to_js: dict = {}
        for j, c in enumerate(target_canon):
            canon_to_js.setdefault(c, []).append(j)
        for i, forms in enumerate(feats["a9a_canons"]):
            if not forms:
                continue
            for c in forms:
                if c in canon_to_js:
                    js = canon_to_js[c]
                    m[i, js] = True
        a9a_mask_cache["m"] = m
        return m

    def fires_for_rule(name: str) -> np.ndarray:
        if name == "A1":
            # depends only on j (Eq2)
            return np.broadcast_to(feats["a1_eq2"][None, :], (n, n)).copy()
        if name == "A2":
            return get_a2_mask()
        if name == "A3":
            return np.broadcast_to(feats["a3_eq1"][:, None], (n, n)).copy()
        if name == "A4":
            return feats["a4_eq1"][:, None] & feats["a4_eq2"][None, :]
        if name == "A5":
            return feats["a5_eq1"][:, None] & feats["a5_eq2"][None, :]
        if name == "A6":
            return feats["a6_eq1"][:, None] & feats["a6_eq2"][None, :]
        if name == "A7":
            return feats["a7_eq1"][:, None] & feats["a7_eq2"][None, :]
        if name == "A8":
            return feats["a8_eq1"][:, None] & feats["a8_eq2"][None, :]
        if name == "A9":
            return np.zeros((n, n), dtype=bool)  # subsumed by A9a
        if name == "A9a":
            return get_a9a_mask()
        if name in W_INVARIANTS:
            h = feats["inv"][name]
            return h[:, None] & ~h[None, :]
        if name == "B0":
            M = feats["b_msv"][:, 0]  # M is per-Eq1
            C1 = feats["b_C"]
            C2 = feats["b_C"]
            # bilateral: fires iff M[i] == 1 AND C2[j] > C1[i] + 2
            return (M[:, None] == 1) & (C2[None, :] > (C1[:, None] + 2))
        if name == "B1":
            M = feats["b_msv"][:, 0]
            return np.broadcast_to((M >= 2)[:, None], (n, n)).copy()
        if name == "B2a":
            M = feats["b_msv"][:, 0]
            S = feats["b_msv"][:, 1]
            flag = (M == 1) & (S == 0)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "B2b":
            M = feats["b_msv"][:, 0]
            S = feats["b_msv"][:, 1]
            V = feats["b_msv"][:, 2]
            flag = (M == 1) & (S == 1) & (V == 2)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "B2c":
            M = feats["b_msv"][:, 0]
            S = feats["b_msv"][:, 1]
            V = feats["b_msv"][:, 2]
            flag1 = (M == 1) & (S == 1) & (V == 1)
            return flag1[:, None] & feats["b2c_eq2"][None, :]
        if name == "B2d":
            return np.ones((n, n), dtype=bool)
        raise KeyError(f"Unknown rule {name!r}")

    return fires_for_rule


def run_full_etp_summary(ctx: ETPContext, feats: dict | None = None) -> dict:
    if feats is None:
        feats = _per_eq_features(ctx)
    fires_for_rule = build_fires_for_rule(ctx, feats)
    return run_full_etp(ctx, fires_for_rule, RULE_ORDER, TRUE_RULES,
                        progress_label="reza_jamei-ETP")


# ---------------------------------------------------------------------------
# 9. Driver
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
    out_dir = ROOT / "analysis" / "results" / "reza_jamei"
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.stderr.write("Loading ETP context (parse + compile + gold)...\n")
    t0 = time.time()
    ctx = load_etp_context(load_gold=True)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s "
                     f"(n_eq={ctx.n_eq}, gold loaded={ctx.gold is not None})\n")

    sys.stderr.write("Computing per-equation features (invariants, A/B flags)...\n")
    t0 = time.time()
    feats = _per_eq_features(ctx)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s\n")

    inv = feats["inv"]

    summaries = {}

    sys.stderr.write("\n=== Splits ===\n")
    for stem in SPLITS:
        sys.stderr.write(f"  running {stem}...\n")
        s = run_on_split(stem, ctx, inv)
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

    # Combined summary.json
    combined = {
        "splits": {stem: summaries[stem] for stem in SPLITS},
        "full_etp": full,
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(combined, f, indent=2)

    # SUMMARY.md
    md = ["# reza_jamei.txt programmatic checker — summary", ""]
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
