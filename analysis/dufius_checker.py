"""Programmatic ("ceiling") checker for the dufius.txt cheatsheet.

Implements the deterministic cascade exactly as written in
`cheatsheets/dufius.txt`:

  STEP 2  — IDENTITY/COLLAPSE TRUE rules : X1, X2, X3
  STEP 3  — FORCED BEHAVIOR              : F1, F2, F3, F4 (each can fire TRUE
            or FALSE; we expand into F{n}_TRUE / F{n}_FALSE for the per-rule
            breakdown)
  STEP 4  — SOURCE CONTRADICTION MOTIFS  : C1..C14 (TRUE)
  STEP 5  — SEPARATORS                   : S1..S5 (FALSE)
  STEP 6  — AFFINE PROBES                : A1..A10 (FALSE)
  STEP 7  — HEURISTIC REJECTS            : H1..H6 (FALSE)
  STEP 8  — LAYER B FALLBACK             : B1 (FALSE), B2a (TRUE),
            B2b (TRUE), B2c (FALSE)

Two entry points:
    run_on_split(stem, ctx)       -> per-split scalar evaluation
    run_full_etp_summary(ctx)     -> vectorized 4694x4694 evaluation

The driver runs all 9 SAIR splits + the full ETP and writes results to
`analysis/results/dufius/`.
"""

from __future__ import annotations

import json
import sys
import time
from itertools import product
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
# 1. Cascade name list & TRUE-set
# ---------------------------------------------------------------------------

RULE_ORDER = [
    # STEP 2
    "X1", "X2", "X3",
    # STEP 3 — F-rules expanded into their two outcomes
    "F1_TRUE", "F1_FALSE",
    "F2_TRUE", "F2_FALSE",
    "F3_TRUE", "F3_FALSE",
    "F4_TRUE", "F4_FALSE",
    # STEP 4
    "C1", "C2", "C3", "C4", "C5", "C6", "C7",
    "C8", "C9", "C10", "C11", "C12", "C13", "C14",
    # STEP 5
    "S1", "S2", "S3", "S4", "S5",
    # STEP 6
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
    # STEP 7
    "H1", "H2", "H3", "H4", "H5", "H6",
    # STEP 8
    "B1", "B2a", "B2b", "B2c",
]

TRUE_RULES = {
    "X1", "X2", "X3",
    "F1_TRUE", "F2_TRUE", "F3_TRUE", "F4_TRUE",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7",
    "C8", "C9", "C10", "C11", "C12", "C13", "C14",
    "B2a", "B2b",
}


# ---------------------------------------------------------------------------
# 2. Tree helpers
# ---------------------------------------------------------------------------

def _is_var(n):
    return isinstance(n, Var)


def leaves(node):
    if isinstance(node, Var):
        return [node.name]
    return leaves(node.left) + leaves(node.right)


def all_vars(node):
    if isinstance(node, Var):
        return {node.name}
    return all_vars(node.left) | all_vars(node.right)


def count_var(node, name):
    if isinstance(node, Var):
        return 1 if node.name == name else 0
    return count_var(node.left, name) + count_var(node.right, name)


def _occ_dict(node):
    d = {}
    for v in leaves(node):
        d[v] = d.get(v, 0) + 1
    return d


def leftmost(node):
    while isinstance(node, Op):
        node = node.left
    return node.name


def rightmost(node):
    while isinstance(node, Op):
        node = node.right
    return node.name


def left_depth(node):
    """Number of left-branches on path to leftmost leaf."""
    d = 0
    while isinstance(node, Op):
        d += 1
        node = node.left
    return d


def right_depth(node):
    """Number of right-branches on path to rightmost leaf."""
    d = 0
    while isinstance(node, Op):
        d += 1
        node = node.right
    return d


def has_square_subterm(node):
    """True iff some subterm has form u*u (same variable on both sides)."""
    if isinstance(node, Var):
        return False
    if (_is_var(node.left) and _is_var(node.right)
            and node.left.name == node.right.name):
        return True
    return has_square_subterm(node.left) or has_square_subterm(node.right)


# ---------------------------------------------------------------------------
# 3. Per-equation features
# ---------------------------------------------------------------------------

def equation_features(p):
    """Compute the per-equation features used by all rules."""
    L, R = p["lhs"], p["rhs"]
    occL = _occ_dict(L)
    occR = _occ_dict(R)
    v_all = set(occL) | set(occR)

    # LP / RP / SET / XOR / AB
    LP_eq = (leftmost(L) == leftmost(R))
    RP_eq = (rightmost(L) == rightmost(R))
    SET_eq = (set(occL) == set(occR))
    XOR_eq = all((occL.get(k, 0) % 2) == (occR.get(k, 0) % 2) for k in v_all)
    AB_eq = all((occL.get(k, 0)) == (occR.get(k, 0)) for k in v_all)

    # bare(E): exactly one side bare
    L_is_var = isinstance(L, Var)
    R_is_var = isinstance(R, Var)
    bare = (L_is_var and not R_is_var) or (R_is_var and not L_is_var)

    feats = {
        "LP": LP_eq,
        "RP": RP_eq,
        "SET": SET_eq,
        "XOR": XOR_eq,
        "AB": AB_eq,
        "bare": bare,
        "L_is_var": L_is_var,
        "R_is_var": R_is_var,
    }

    # If bare, compute kind/shortest_len/occ on the product side relative to
    # the bare variable x.
    if bare:
        if L_is_var:
            x = L.name
            prod = R
        else:
            x = R.name
            prod = L

        # Walk the product tree collecting all paths to each x leaf.
        paths = []  # list of strings (sequence of 'L'/'R')
        def walk(t, path):
            if isinstance(t, Var):
                if t.name == x:
                    paths.append(path)
                return
            walk(t.left, path + "L")
            walk(t.right, path + "R")
        walk(prod, "")

        if not paths:
            kind = "X"
            shortest_len = -1
            occ = 0
        else:
            occ = len(paths)
            shortest_len = min(len(p_) for p_ in paths)
            all_L = all(set(p_) <= {"L"} for p_ in paths)
            all_R = all(set(p_) <= {"R"} for p_ in paths)
            any_mix = any(("L" in p_ and "R" in p_) for p_ in paths)
            if any_mix:
                kind = "M"
            elif all_L and not all_R:
                kind = "L"
            elif all_R and not all_L:
                kind = "R"
            else:
                # Could be empty path (x at root, but that's not bare-product)
                # or all paths empty — treat as L by default.
                kind = "L"

        feats["x"] = x
        feats["kind"] = kind
        feats["shortest_len"] = shortest_len
        feats["occ_x"] = occ
        feats["prod_side"] = prod

        # Step 4 (C-rule) features for product side of A
        prod_occ = _occ_dict(prod)
        prod_vars = set(prod_occ)
        rhsVars = len(prod_vars)
        rhsCounts = "".join(str(c) for c in sorted(prod_occ.values()))
        Lx = (leftmost(prod) == x)
        Rx = (rightmost(prod) == x)
        # topShape
        if isinstance(prod, Op):
            U, V = prod.left, prod.right
            U_var = isinstance(U, Var)
            V_var = isinstance(V, Var)
            if U_var and not V_var:
                topShape = "v-m"
            elif V_var and not U_var:
                topShape = "m-v"
            elif U_var and V_var:
                # Both bare — treat as v-m (U var, V var; cheatsheet doesn't
                # specifically distinguish, but C-rules require one side product
                # so this case won't matter).
                topShape = "v-v"
            else:
                topShape = "m-m"
            U_has_x = (x in all_vars(U))
            V_has_x = (x in all_vars(V))
            if U_has_x and V_has_x:
                xTop = "both"
            elif U_has_x and not V_has_x:
                xTop = "left"
            elif V_has_x and not U_has_x:
                xTop = "right"
            else:
                xTop = "none"
        else:
            # bare product — won't reach C-rules anyway
            topShape = ""
            xTop = "none"

        xCount = count_var(prod, x)
        square = has_square_subterm(prod)

        feats["rhsVars"] = rhsVars
        feats["rhsCounts"] = rhsCounts
        feats["Lx"] = Lx
        feats["Rx"] = Rx
        feats["topShape"] = topShape
        feats["xTop"] = xTop
        feats["xCount"] = xCount
        feats["square"] = square
    else:
        feats["x"] = None
        feats["kind"] = "N"
        feats["shortest_len"] = -1
        feats["occ_x"] = 0
        feats["rhsVars"] = 0
        feats["rhsCounts"] = ""
        feats["Lx"] = False
        feats["Rx"] = False
        feats["topShape"] = ""
        feats["xTop"] = "none"
        feats["xCount"] = 0
        feats["square"] = False
        feats["prod_side"] = None

    # M / S / V for layer B
    all_v = set(occL) | set(occR)
    if not all_v:
        M = 0
    else:
        M = min(occL.get(v, 0) + occR.get(v, 0) for v in all_v)
    S = p["n_ops_lhs"]
    if isinstance(L, Var):
        V_count = 1
    else:
        V_count = len(set(occL))
    feats["M"] = M
    feats["S"] = S
    feats["V"] = V_count

    return feats


# ---------------------------------------------------------------------------
# 4. STEP 2 - X rules
# ---------------------------------------------------------------------------

def fires_X1(p1, p2, f1, f2):
    """B.L = B.R syntactically."""
    return _tree_eq(p2["lhs"], p2["rhs"])


def _tree_eq(a, b):
    if isinstance(a, Var) and isinstance(b, Var):
        return a.name == b.name
    if isinstance(a, Op) and isinstance(b, Op):
        return _tree_eq(a.left, b.left) and _tree_eq(a.right, b.right)
    return False


def fires_X2(p1, p2, f1, f2):
    """A and B same up to consistent renaming + optional side-swap of A.
    The 'canonical' form already canonicalises the equation symmetrically."""
    return p1["canonical"] == p2["canonical"]


def fires_X3(p1, p2, f1, f2):
    """A is `x = y` (x != y), OR A has a lone-variable side absent from
    the other side."""
    L, R = p1["lhs"], p1["rhs"]
    if isinstance(L, Var) and isinstance(R, Var):
        if L.name != R.name:
            return True
    if isinstance(L, Var) and L.name not in all_vars(R):
        return True
    if isinstance(R, Var) and R.name not in all_vars(L):
        return True
    return False


# ---------------------------------------------------------------------------
# 5. STEP 3 - F rules
#
# Each F-rule has two outcomes: TRUE or FALSE. The ORDER in the cascade is:
# F1 fires (TRUE or FALSE) before F2 fires, etc.
# We expand F1 into F1_TRUE / F1_FALSE: one of these fires depending on B's
# feature.
# ---------------------------------------------------------------------------

def _is_two_var_product(node):
    """True if node is x*y with x,y vars (possibly same)."""
    return (isinstance(node, Op) and _is_var(node.left) and _is_var(node.right))


def f1_triggers(p):
    """A is `x = x*y` or `x*y = x` (up to side-swap), x != y. Return True if it
    triggers (then verdict is TRUE iff LP(B), else FALSE)."""
    L, R = p["lhs"], p["rhs"]
    for B, P in ((L, R), (R, L)):
        if _is_var(B) and _is_two_var_product(P):
            x = B.name
            if P.left.name == x and P.right.name != x:
                return True
    return False


def f2_triggers(p):
    """A is `x = y*x` or `y*x = x`, x != y."""
    L, R = p["lhs"], p["rhs"]
    for B, P in ((L, R), (R, L)):
        if _is_var(B) and _is_two_var_product(P):
            x = B.name
            if P.right.name == x and P.left.name != x:
                return True
    return False


def f3_triggers(p):
    """Both sides products of two vars; same left child, different right."""
    L, R = p["lhs"], p["rhs"]
    if _is_two_var_product(L) and _is_two_var_product(R):
        if L.left.name == R.left.name and L.right.name != R.right.name:
            return True
    return False


def f4_triggers(p):
    """Both sides products of two vars; same right child, different left."""
    L, R = p["lhs"], p["rhs"]
    if _is_two_var_product(L) and _is_two_var_product(R):
        if L.right.name == R.right.name and L.left.name != R.left.name:
            return True
    return False


def f3_b_holds(p):
    """(leftmost,left-depth) pairs of B.L and B.R match."""
    return (leftmost(p["lhs"]) == leftmost(p["rhs"])
            and left_depth(p["lhs"]) == left_depth(p["rhs"]))


def f4_b_holds(p):
    """(rightmost,right-depth) pairs of B.L and B.R match."""
    return (rightmost(p["lhs"]) == rightmost(p["rhs"])
            and right_depth(p["lhs"]) == right_depth(p["rhs"]))


# ---------------------------------------------------------------------------
# 6. STEP 4 - C rules (operate on bare(A) only; use product side of A)
# ---------------------------------------------------------------------------

def fires_C1(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return f1["rhsVars"] == 4 and not f1["Lx"] and not f1["Rx"]


def fires_C2(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return f1["rhsCounts"] == "113" and not f1["Lx"] and not f1["Rx"]


def fires_C3(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (not f1["Lx"] and f1["xTop"] == "left" and f1["square"]
            and f1["topShape"] == "m-v")


def fires_C4(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "112" and not f1["Lx"] and not f1["Rx"]
            and f1["xTop"] == "right" and f1["topShape"] == "v-m")


def fires_C5(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "1112" and not f1["Lx"] and not f1["Rx"]
            and f1["xTop"] == "right" and f1["topShape"] == "v-m")


def fires_C6(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsVars"] == 3 and f1["xTop"] == "right"
            and f1["topShape"] == "v-m" and f1["xCount"] == 2)


def fires_C7(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsVars"] == 3 and not f1["Lx"] and not f1["Rx"]
            and f1["xTop"] == "left" and f1["topShape"] == "m-v"
            and f1["xCount"] == 2)


def fires_C8(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsVars"] == 3 and f1["Lx"]
            and f1["xTop"] == "left" and f1["topShape"] == "m-v")


def fires_C9(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "122" and f1["Lx"] and not f1["Rx"]
            and f1["xTop"] == "both" and f1["topShape"] == "v-m")


def fires_C10(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "122" and not f1["Lx"] and f1["Rx"]
            and f1["xCount"] == 2)


def fires_C11(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "113" and not f1["Lx"] and not f1["Rx"]
            and f1["xTop"] == "right" and f1["topShape"] == "v-m")


def fires_C12(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "113" and not f1["Lx"] and not f1["Rx"]
            and f1["xTop"] == "left" and f1["topShape"] == "m-v")


def fires_C13(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f1["rhsCounts"] == "1112" and not f1["Lx"] and f1["Rx"])


def fires_C14(p1, p2, f1, f2):
    if not f1["bare"]: return False
    return (f2["bare"] and f1["rhsCounts"] == "113" and f1["Rx"]
            and not f1["square"])


# ---------------------------------------------------------------------------
# 7. STEP 5 - S rules (separators)
# ---------------------------------------------------------------------------

def fires_S1(p1, p2, f1, f2): return f1["LP"] and not f2["LP"]
def fires_S2(p1, p2, f1, f2): return f1["RP"] and not f2["RP"]
def fires_S3(p1, p2, f1, f2): return f1["SET"] and not f2["SET"]
def fires_S4(p1, p2, f1, f2): return f1["XOR"] and not f2["XOR"]
def fires_S5(p1, p2, f1, f2): return f1["AB"] and not f2["AB"]


# ---------------------------------------------------------------------------
# 8. STEP 6 - Affine probes
#
# For each probe u*v = p*u + q*v + c (mod m), we recursively compute a
# (coeff_dict, const) form for any expression. An equation "holds in the probe"
# iff LHS form == RHS form.
# ---------------------------------------------------------------------------

def affine_eval(node, p_coef, q_coef, const, m):
    """Return (coef_dict, c) for `node` under u*v = p*u + q*v + const mod m.
    coef_dict is var-name -> int mod m; c is int mod m."""
    if isinstance(node, Var):
        return ({node.name: 1 % m}, 0)
    L_coef, L_c = affine_eval(node.left, p_coef, q_coef, const, m)
    R_coef, R_c = affine_eval(node.right, p_coef, q_coef, const, m)
    out = {}
    for k, v in L_coef.items():
        out[k] = (out.get(k, 0) + p_coef * v) % m
    for k, v in R_coef.items():
        out[k] = (out.get(k, 0) + q_coef * v) % m
    # Drop zero entries for cleanliness
    out = {k: v for k, v in out.items() if v % m != 0}
    c = (p_coef * L_c + q_coef * R_c + const) % m
    return (out, c)


def affine_eq_holds(p, p_coef, q_coef, const, m):
    """Equation holds iff LHS form == RHS form."""
    a = affine_eval(p["lhs"], p_coef, q_coef, const, m)
    b = affine_eval(p["rhs"], p_coef, q_coef, const, m)
    return a[0] == b[0] and a[1] == b[1]


AFFINE_PROBES = [
    ("A1",  0, 1, 1, 3),   # v + 1 mod 3
    ("A2",  1, 0, 1, 3),
    ("A3",  1, 1, 0, 3),
    ("A4",  1, 2, 0, 3),
    ("A5",  2, 2, 0, 3),
    ("A6",  2, 3, 0, 4),
    ("A7",  3, 2, 0, 4),
    ("A8",  1, 2, 0, 4),
    ("A9",  2, 1, 1, 4),
    ("A10", 3, 3, 0, 5),
]


# ---------------------------------------------------------------------------
# 9. STEP 7 - Heuristic rejects (FALSE)
# ---------------------------------------------------------------------------

def fires_H1(p1, p2, f1, f2):
    return (f1["kind"] == "M" and len(p1["lhs_vars"] | p1["rhs_vars"]) >= 4
            and f2["kind"] == "X")


def fires_H2(p1, p2, f1, f2):
    """kind(A)=L AND shortest_len(A)=1 AND dup(A)>=3 AND bare(B)=F
       AND dup(B)>=3 AND vars(B)<=3."""
    if f1["kind"] != "L" or f1["shortest_len"] != 1:
        return False
    occA = _occ_dict(p1["lhs"])
    for k, v in _occ_dict(p1["rhs"]).items():
        occA[k] = occA.get(k, 0) + v
    sizeA = sum(occA.values())
    varsA = len(occA)
    dupA = sizeA - varsA
    if dupA < 3:
        return False
    if f2["bare"]:
        return False
    occB = _occ_dict(p2["lhs"])
    for k, v in _occ_dict(p2["rhs"]).items():
        occB[k] = occB.get(k, 0) + v
    sizeB = sum(occB.values())
    varsB = len(occB)
    dupB = sizeB - varsB
    return dupB >= 3 and varsB <= 3


def fires_H3(p1, p2, f1, f2):
    return (f1["kind"] == "M" and f1["occ_x"] == 2 and not f1["RP"]
            and not f1["Lx"])


def fires_H4(p1, p2, f1, f2):
    return f1["shortest_len"] == 1 and f1["occ_x"] == 3


def fires_H5(p1, p2, f1, f2):
    return (f1["kind"] == "M" and f1["shortest_len"] == 3
            and f1["occ_x"] == 2)


def fires_H6(p1, p2, f1, f2):
    """kind(A)=L AND occ(B)=2 AND vars(B)=4."""
    if f1["kind"] != "L":
        return False
    # occ(B) refers to occ() of B (bare-side feature).
    # vars(B) = number of distinct variables in B (whole equation).
    varsB = len(p2["lhs_vars"] | p2["rhs_vars"])
    return f2["occ_x"] == 2 and varsB == 4


# ---------------------------------------------------------------------------
# 10. STEP 8 - Layer B
# ---------------------------------------------------------------------------

def fires_B1(p1, p2, f1, f2): return f1["M"] >= 2
def fires_B2a(p1, p2, f1, f2): return f1["M"] == 1 and f1["S"] == 0
def fires_B2b(p1, p2, f1, f2):
    return f1["M"] == 1 and f1["S"] == 1 and f1["V"] == 2
def fires_B2c(p1, p2, f1, f2): return True  # default catch-all FALSE


# ---------------------------------------------------------------------------
# 11. Scalar predict
# ---------------------------------------------------------------------------

# Order-independent scalar registry: each entry is (name, predicate, verdict).
# We walk RULE_ORDER and consult the appropriate predicate.

C_FNS = [
    ("C1", fires_C1), ("C2", fires_C2), ("C3", fires_C3), ("C4", fires_C4),
    ("C5", fires_C5), ("C6", fires_C6), ("C7", fires_C7), ("C8", fires_C8),
    ("C9", fires_C9), ("C10", fires_C10), ("C11", fires_C11), ("C12", fires_C12),
    ("C13", fires_C13), ("C14", fires_C14),
]
S_FNS = [
    ("S1", fires_S1), ("S2", fires_S2), ("S3", fires_S3), ("S4", fires_S4),
    ("S5", fires_S5),
]
H_FNS = [
    ("H1", fires_H1), ("H2", fires_H2), ("H3", fires_H3),
    ("H4", fires_H4), ("H5", fires_H5), ("H6", fires_H6),
]


def predict_scalar(p1, p2, f1, f2, holdsA_by_probe, holdsB_by_probe):
    """Return the rule name that fires for the (p1, p2) pair under the
    cascade.

    holdsA_by_probe[probe_name] -> bool  (probe holds on Eq1)
    holdsB_by_probe[probe_name] -> bool  (probe holds on Eq2)
    """
    # X1, X2, X3
    if fires_X1(p1, p2, f1, f2): return "X1"
    if fires_X2(p1, p2, f1, f2): return "X2"
    if fires_X3(p1, p2, f1, f2): return "X3"

    # F1
    if f1_triggers(p1):
        return "F1_TRUE" if f2["LP"] else "F1_FALSE"
    # F2
    if f2_triggers(p1):
        return "F2_TRUE" if f2["RP"] else "F2_FALSE"
    # F3
    if f3_triggers(p1):
        return "F3_TRUE" if f3_b_holds(p2) else "F3_FALSE"
    # F4
    if f4_triggers(p1):
        return "F4_TRUE" if f4_b_holds(p2) else "F4_FALSE"

    # C-rules
    for name, fn in C_FNS:
        if fn(p1, p2, f1, f2):
            return name

    # S-rules
    for name, fn in S_FNS:
        if fn(p1, p2, f1, f2):
            return name

    # Affine probes: probe fires FALSE iff holdsA AND NOT holdsB
    for name, *_ in AFFINE_PROBES:
        if holdsA_by_probe[name] and not holdsB_by_probe[name]:
            return name

    # H-rules
    for name, fn in H_FNS:
        if fn(p1, p2, f1, f2):
            return name

    # Layer B
    if fires_B1(p1, p2, f1, f2): return "B1"
    if fires_B2a(p1, p2, f1, f2): return "B2a"
    if fires_B2b(p1, p2, f1, f2): return "B2b"
    return "B2c"


# ---------------------------------------------------------------------------
# 12. Per-split runner
# ---------------------------------------------------------------------------

def _precompute_split_features(ctx: ETPContext):
    """Per-equation features + per-equation affine probe holds bools."""
    feats = [equation_features(p) for p in ctx.parsed]
    holds = {}
    for name, p_, q_, c_, m_ in AFFINE_PROBES:
        v = np.zeros(ctx.n_eq, dtype=bool)
        for i, p in enumerate(ctx.parsed):
            v[i] = affine_eq_holds(p, p_, q_, c_, m_)
        holds[name] = v
    return feats, holds


def run_on_split(stem: str, ctx: ETPContext, feats: list, holds: dict) -> dict:
    problems = load_split(stem)
    rows = []
    for p in problems:
        i_id = p["eq1_id"]
        j_id = p["eq2_id"]
        i = i_id - 1
        j = j_id - 1
        if 0 <= i < ctx.n_eq:
            p1 = ctx.parsed[i]
            f1 = feats[i]
            holdsA = {n: bool(holds[n][i]) for n, *_ in AFFINE_PROBES}
        else:
            p1 = _parse_eq(p["equation1"])
            f1 = equation_features(p1)
            holdsA = {n: affine_eq_holds(p1, pp, qq, cc, mm)
                      for n, pp, qq, cc, mm in AFFINE_PROBES}
        if 0 <= j < ctx.n_eq:
            p2 = ctx.parsed[j]
            f2 = feats[j]
            holdsB = {n: bool(holds[n][j]) for n, *_ in AFFINE_PROBES}
        else:
            p2 = _parse_eq(p["equation2"])
            f2 = equation_features(p2)
            holdsB = {n: affine_eq_holds(p2, pp, qq, cc, mm)
                      for n, pp, qq, cc, mm in AFFINE_PROBES}
        rule = predict_scalar(p1, p2, f1, f2, holdsA, holdsB)
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
# 13. Vectorized full-ETP runner
# ---------------------------------------------------------------------------

def _per_eq_features(ctx: ETPContext):
    """Compute per-equation arrays needed to vectorize each rule's fire mask."""
    n = ctx.n_eq
    parsed = ctx.parsed
    feats = [equation_features(p) for p in parsed]

    # Per-equation booleans for vectorization
    LP = np.array([f["LP"] for f in feats], dtype=bool)
    RP = np.array([f["RP"] for f in feats], dtype=bool)
    SET = np.array([f["SET"] for f in feats], dtype=bool)
    XOR = np.array([f["XOR"] for f in feats], dtype=bool)
    AB = np.array([f["AB"] for f in feats], dtype=bool)
    bare_ = np.array([f["bare"] for f in feats], dtype=bool)

    # X1: depends only on j (Eq2); B.L = B.R syntactically.
    x1_eq2 = np.array([_tree_eq(p["lhs"], p["rhs"]) for p in parsed], dtype=bool)
    # X2: same canonical form.
    canon = np.array([p["canonical"] for p in parsed], dtype=object)
    # X3: depends only on i.
    def x3_flag(p):
        L, R = p["lhs"], p["rhs"]
        if isinstance(L, Var) and isinstance(R, Var) and L.name != R.name:
            return True
        if isinstance(L, Var) and L.name not in all_vars(R):
            return True
        if isinstance(R, Var) and R.name not in all_vars(L):
            return True
        return False
    x3_eq1 = np.array([x3_flag(p) for p in parsed], dtype=bool)

    # F-rule triggers (Eq1-only)
    f1_trig = np.array([f1_triggers(p) for p in parsed], dtype=bool)
    f2_trig = np.array([f2_triggers(p) for p in parsed], dtype=bool)
    f3_trig = np.array([f3_triggers(p) for p in parsed], dtype=bool)
    f4_trig = np.array([f4_triggers(p) for p in parsed], dtype=bool)
    # F-rule outcome features (Eq2-only)
    # F1 outcome: LP(B) → LP[j]; F2: RP[j]; F3: f3_b_holds; F4: f4_b_holds
    f3b = np.array([f3_b_holds(p) for p in parsed], dtype=bool)
    f4b = np.array([f4_b_holds(p) for p in parsed], dtype=bool)

    # C-rules: each is an Eq1-only flag (depends on bare-A's product side)
    # Build a (n_rules, n) boolean matrix.
    c_flags = {}
    for name, fn in C_FNS:
        if name == "C14":
            continue  # bilateral; handled separately below.
        c_flags[name] = np.array(
            [fn(p, None, feats[i], None) for i, p in enumerate(parsed)],
            dtype=bool)
    # C14 requires bare(B); split into Eq1-only flag + bare(B) flag.
    def c14_eq1(f1):
        return (f1["bare"] and f1["rhsCounts"] == "113" and f1["Rx"]
                and not f1["square"])
    c14_eq1_arr = np.array([c14_eq1(feats[i]) for i in range(n)], dtype=bool)
    c14_eq2_arr = bare_  # bare(B)

    # S-rules: depend on Eq1 invariant + Eq2 invariant via outer prod.
    # S1: LP(A) AND NOT LP(B). General form: Inv(A) AND NOT Inv(B).

    # Affine probes — compute per-eq holds bools.
    holds = {}
    for name, pa, qa, ca, ma in AFFINE_PROBES:
        v = np.zeros(n, dtype=bool)
        for i, p in enumerate(parsed):
            v[i] = affine_eq_holds(p, pa, qa, ca, ma)
        holds[name] = v

    # H-rules: H1 depends on Eq1 & Eq2 features; H2 has Eq1 & Eq2; H3..H5 are
    # Eq1-only; H6 depends on Eq1 & Eq2.
    kindA = np.array([f["kind"] for f in feats], dtype=object)
    occ_xA = np.array([f["occ_x"] for f in feats], dtype=np.int32)
    short_lenA = np.array([f["shortest_len"] for f in feats], dtype=np.int32)
    nvars_eq = np.array([len(p["lhs_vars"] | p["rhs_vars"]) for p in parsed],
                        dtype=np.int32)

    # dup feature for whole equation A and B
    def dup_eq(p):
        occA = _occ_dict(p["lhs"])
        for k, v in _occ_dict(p["rhs"]).items():
            occA[k] = occA.get(k, 0) + v
        size = sum(occA.values())
        nv = len(occA)
        return size - nv

    dup_arr = np.array([dup_eq(p) for p in parsed], dtype=np.int32)

    # H1: M-source AND >=4 vars AND target is X-source
    h1_eq1 = (kindA == "M") & (nvars_eq >= 4)
    h1_eq2 = (kindA == "X")
    # H2: kind(A)=L AND shortest_len(A)=1 AND dup(A)>=3 AND bare(B)=F
    #     AND dup(B)>=3 AND vars(B)<=3
    h2_eq1 = (kindA == "L") & (short_lenA == 1) & (dup_arr >= 3)
    h2_eq2 = (~bare_) & (dup_arr >= 3) & (nvars_eq <= 3)
    # H3: M, occ=2, NOT RP(A), Lx(A)=F  [Eq1-only]
    LxA = np.array([f["Lx"] for f in feats], dtype=bool)
    h3_eq1 = (kindA == "M") & (occ_xA == 2) & (~RP) & (~LxA)
    # H4: shortest_len=1 AND occ=3 (Eq1-only, regardless)
    h4_eq1 = (short_lenA == 1) & (occ_xA == 3)
    # H5: M, shortest_len=3, occ=2 (Eq1-only)
    h5_eq1 = (kindA == "M") & (short_lenA == 3) & (occ_xA == 2)
    # H6: kind(A)=L AND occ(B)=2 AND vars(B)=4
    h6_eq1 = (kindA == "L")
    h6_eq2 = (occ_xA == 2) & (nvars_eq == 4)

    # Layer B per-Eq1
    M_arr = np.array([f["M"] for f in feats], dtype=np.int32)
    S_arr = np.array([f["S"] for f in feats], dtype=np.int32)
    V_arr = np.array([f["V"] for f in feats], dtype=np.int32)

    return {
        "feats": feats,
        "LP": LP, "RP": RP, "SET": SET, "XOR": XOR, "AB": AB, "bare": bare_,
        "x1_eq2": x1_eq2, "canon": canon, "x3_eq1": x3_eq1,
        "f1_trig": f1_trig, "f2_trig": f2_trig,
        "f3_trig": f3_trig, "f4_trig": f4_trig,
        "f3b": f3b, "f4b": f4b,
        "c_flags": c_flags,
        "c14_eq1": c14_eq1_arr, "c14_eq2": c14_eq2_arr,
        "holds": holds,
        "h1_eq1": h1_eq1, "h1_eq2": h1_eq2,
        "h2_eq1": h2_eq1, "h2_eq2": h2_eq2,
        "h3_eq1": h3_eq1, "h4_eq1": h4_eq1, "h5_eq1": h5_eq1,
        "h6_eq1": h6_eq1, "h6_eq2": h6_eq2,
        "M": M_arr, "S": S_arr, "V": V_arr,
    }


def build_fires_for_rule(ctx: ETPContext, feats: dict):
    """Return a closure `fires_for_rule(name) -> bool[n_eq, n_eq]`."""
    n = ctx.n_eq

    # Pre-build canonical → list of i for X2.
    canon_to_i: dict = {}
    for i, c in enumerate(feats["canon"]):
        canon_to_i.setdefault(c, []).append(i)

    x2_mask_cache = {"m": None}

    def get_x2_mask():
        if x2_mask_cache["m"] is not None:
            return x2_mask_cache["m"]
        m = np.zeros((n, n), dtype=bool)
        for c, idxs in canon_to_i.items():
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
        # F-rules
        if name == "F1_TRUE":
            return feats["f1_trig"][:, None] & feats["LP"][None, :]
        if name == "F1_FALSE":
            return feats["f1_trig"][:, None] & ~feats["LP"][None, :]
        if name == "F2_TRUE":
            return feats["f2_trig"][:, None] & feats["RP"][None, :]
        if name == "F2_FALSE":
            return feats["f2_trig"][:, None] & ~feats["RP"][None, :]
        if name == "F3_TRUE":
            return feats["f3_trig"][:, None] & feats["f3b"][None, :]
        if name == "F3_FALSE":
            return feats["f3_trig"][:, None] & ~feats["f3b"][None, :]
        if name == "F4_TRUE":
            return feats["f4_trig"][:, None] & feats["f4b"][None, :]
        if name == "F4_FALSE":
            return feats["f4_trig"][:, None] & ~feats["f4b"][None, :]
        # C-rules
        if name in ("C1", "C2", "C3", "C4", "C5", "C6", "C7",
                    "C8", "C9", "C10", "C11", "C12", "C13"):
            return np.broadcast_to(feats["c_flags"][name][:, None],
                                    (n, n)).copy()
        if name == "C14":
            return feats["c14_eq1"][:, None] & feats["c14_eq2"][None, :]
        # S-rules
        if name == "S1":
            return feats["LP"][:, None] & ~feats["LP"][None, :]
        if name == "S2":
            return feats["RP"][:, None] & ~feats["RP"][None, :]
        if name == "S3":
            return feats["SET"][:, None] & ~feats["SET"][None, :]
        if name == "S4":
            return feats["XOR"][:, None] & ~feats["XOR"][None, :]
        if name == "S5":
            return feats["AB"][:, None] & ~feats["AB"][None, :]
        # Affine probes
        if name in feats["holds"]:
            h = feats["holds"][name]
            return h[:, None] & ~h[None, :]
        # H-rules
        if name == "H1":
            return feats["h1_eq1"][:, None] & feats["h1_eq2"][None, :]
        if name == "H2":
            return feats["h2_eq1"][:, None] & feats["h2_eq2"][None, :]
        if name == "H3":
            return np.broadcast_to(feats["h3_eq1"][:, None], (n, n)).copy()
        if name == "H4":
            return np.broadcast_to(feats["h4_eq1"][:, None], (n, n)).copy()
        if name == "H5":
            return np.broadcast_to(feats["h5_eq1"][:, None], (n, n)).copy()
        if name == "H6":
            return feats["h6_eq1"][:, None] & feats["h6_eq2"][None, :]
        # Layer B
        if name == "B1":
            flag = feats["M"] >= 2
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "B2a":
            flag = (feats["M"] == 1) & (feats["S"] == 0)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "B2b":
            flag = (feats["M"] == 1) & (feats["S"] == 1) & (feats["V"] == 2)
            return np.broadcast_to(flag[:, None], (n, n)).copy()
        if name == "B2c":
            return np.ones((n, n), dtype=bool)
        raise KeyError(f"Unknown rule {name!r}")

    return fires_for_rule


def run_full_etp_summary(ctx: ETPContext, feats: dict | None = None) -> dict:
    if feats is None:
        feats = _per_eq_features(ctx)
    fires_for_rule = build_fires_for_rule(ctx, feats)
    return run_full_etp(ctx, fires_for_rule, RULE_ORDER, TRUE_RULES,
                        progress_label="dufius-ETP")


# ---------------------------------------------------------------------------
# 14. Output
# ---------------------------------------------------------------------------

def _md_table_for_split(s: dict) -> str:
    n, nc = s["n"], s["n_correct"]
    cf = s["confusion"]
    out = [f"### `{s['dataset']}`  —  accuracy {nc}/{n} = {nc/n*100:.2f}%", ""]
    out.append(f"Confusion: TP={cf['tp']}, FP={cf['fp']}, "
               f"TN={cf['tn']}, FN={cf['fn']}")
    out.append("")
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
        out.append(f"| {rule} | {verdict} | {bs['n']} | {correct} | "
                   f"{wrong} | {prec:.1f}% |")
    out.append("")
    return "\n".join(out)


def main():
    out_dir = ROOT / "analysis" / "results" / "dufius"
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.stderr.write("Loading ETP context (parse + compile + gold)...\n")
    t0 = time.time()
    ctx = load_etp_context(load_gold=True)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s "
                     f"(n_eq={ctx.n_eq}, gold loaded={ctx.gold is not None})\n")

    sys.stderr.write("Computing per-equation features (invariants, A/B/C/F/H "
                     "flags + affine holds)...\n")
    t0 = time.time()
    full_feats = _per_eq_features(ctx)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s\n")

    # For per-split scalar runs we need feats list and holds dict
    feats_list = full_feats["feats"]
    holds = full_feats["holds"]

    summaries = {}

    sys.stderr.write("\n=== Splits ===\n")
    for stem in SPLITS:
        sys.stderr.write(f"  running {stem}...\n")
        s = run_on_split(stem, ctx, feats_list, holds)
        save_summary(s, out_dir / f"{stem}.json", drop_rows=False)
        summaries[stem] = {k: v for k, v in s.items() if k != "rows"}
        print_summary(s)

    sys.stderr.write("\n=== Full ETP (4694x4694 = 22M pairs) ===\n")
    t0 = time.time()
    full = run_full_etp_summary(ctx, full_feats)
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

    md = ["# dufius.txt programmatic checker — summary", ""]
    md.append("## Overall accuracy")
    md.append("")
    md.append("| dataset | n | accuracy |")
    md.append("|---------|--:|---------:|")
    for stem in SPLITS:
        s = summaries[stem]
        md.append(f"| {stem} | {s['n']} | {s['n_correct']}/{s['n']} = "
                  f"{s['n_correct']/s['n']*100:.2f}% |")
    md.append(f"| full_etp | {full['n']} | {full['n_correct']}/{full['n']} = "
              f"{full['n_correct']/full['n']*100:.4f}% |")
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
