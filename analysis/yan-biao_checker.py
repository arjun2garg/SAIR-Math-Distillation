"""Programmatic ("ceiling") checker for the yan-biao.txt cheatsheet.

Implements the deterministic cascade in cheatsheet order:

  STEP 0   — S0a, S0b   (singleton checks; TRUE)
  STEP 1   — T1 (TRUE), F0 (FALSE)
  STEP 1.5 — FP1, FP2, FP3 (forced-projection iff theorems; commit TRUE/FALSE)
  STEP 2   — L, R, K, X (model counterexamples; commit FALSE)
  STEP 2.5 — D_SPINE_L, D_SPINE_R (depth-divisibility; commit FALSE)
  STEP 3   — CASE_A_3VARS_TRUE / CASE_A_LE2VARS_FALSE (no model fired)
             B0, B1, B2, B_SUB, B3_SAME, B3_CROSS, B3_LOOSE, B_RPROJ_NARROW
             DEFAULT_FALSE (catch-all)

Two entry points:
    run_on_split(stem, ctx)        -> per-split scalar evaluation
    run_full_etp_summary(ctx)      -> vectorized 4694x4694 evaluation

Driver writes to `analysis/results/yan-biao/`.
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
# Cascade rule names + verdicts
# ---------------------------------------------------------------------------

RULE_ORDER = [
    # Step 0
    "S0a", "S0b",
    # Step 1
    "T1", "F0",
    # Step 1.5 — split into TRUE/FALSE branches per FP
    "FP1_TRUE", "FP1_FALSE",
    "FP2_TRUE", "FP2_FALSE",
    "FP3_TRUE", "FP3_FALSE",
    # Step 2 — counterexample models (FALSE)
    "L", "R", "K", "X",
    # Step 2.5 — D-spine
    "D_SPINE_L", "D_SPINE_R",
    # Step 3 — Case A
    "CASE_A_3VARS_TRUE", "CASE_A_LE2VARS_FALSE",
    # Step 3 — Case B
    "B0", "B1", "B2", "B_SUB", "B3_SAME", "B3_CROSS", "B3_LOOSE",
    "B_RPROJ_NARROW",
    "DEFAULT_FALSE",
]

TRUE_RULES = {
    "S0a", "S0b", "T1",
    "FP1_TRUE", "FP2_TRUE", "FP3_TRUE",
    "CASE_A_3VARS_TRUE",
    "B0", "B1", "B2", "B_SUB", "B3_SAME", "B3_CROSS", "B3_LOOSE",
    "B_RPROJ_NARROW",
}


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------

def _is_var(n):
    return isinstance(n, Var)


def all_vars(node):
    if _is_var(node):
        return {node.name}
    return all_vars(node.left) | all_vars(node.right)


def leaves(node):
    if _is_var(node):
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


def n_ops(node):
    if _is_var(node):
        return 0
    return 1 + n_ops(node.left) + n_ops(node.right)


def count_var(node, name):
    if _is_var(node):
        return 1 if node.name == name else 0
    return count_var(node.left, name) + count_var(node.right, name)


def tree_eq(a, b):
    if _is_var(a) and _is_var(b):
        return a.name == b.name
    if isinstance(a, Op) and isinstance(b, Op):
        return tree_eq(a.left, b.left) and tree_eq(a.right, b.right)
    return False


def tree_to_tuple(node):
    if _is_var(node):
        return node.name
    return (tree_to_tuple(node.left), tree_to_tuple(node.right))


def canonicalize_equation(lhs, rhs):
    """Canonical form jointly canonicalizing variable names; returns the
    smaller of (lhs,rhs) and (rhs,lhs)."""
    var_pool = "xyzwuv" + "abcdefghijklmnopqrst"

    def go(a, b):
        mapping = {}

        def assign(n):
            if _is_var(n):
                if n.name not in mapping:
                    mapping[n.name] = var_pool[len(mapping)]
            else:
                assign(n.left)
                assign(n.right)

        def rebuild(n):
            if _is_var(n):
                return mapping[n.name]
            return (rebuild(n.left), rebuild(n.right))

        assign(a)
        assign(b)
        return (rebuild(a), rebuild(b))

    f = go(lhs, rhs)
    g = go(rhs, lhs)
    return f if repr(f) <= repr(g) else g


def substitute(node, var_name, replacement):
    if _is_var(node):
        if node.name == var_name:
            return replacement
        return node
    return Op(substitute(node.left, var_name, replacement),
              substitute(node.right, var_name, replacement))


# ---------------------------------------------------------------------------
# Step 2: model simplification
# ---------------------------------------------------------------------------

def simplify_L(node):
    """Left-projection model: a*b = a => keep only leftmost variable."""
    while isinstance(node, Op):
        node = node.left
    return node.name  # variable name


def simplify_R(node):
    """Right-projection model: a*b = b => keep only rightmost variable."""
    while isinstance(node, Op):
        node = node.right
    return node.name


def simplify_X(node):
    """XOR/parity model: count variable occurrences, keep odd ones (as a set)."""
    counts = {}
    for v in leaves(node):
        counts[v] = counts.get(v, 0) + 1
    return frozenset(v for v, c in counts.items() if c % 2 == 1)


def model_status_L(p):
    """Returns 'tautology' (sides match), 'constraint' (sides differ)."""
    if simplify_L(p["lhs"]) == simplify_L(p["rhs"]):
        return "tautology"
    return "constraint"


def model_status_R(p):
    if simplify_R(p["lhs"]) == simplify_R(p["rhs"]):
        return "tautology"
    return "constraint"


def model_status_K(p):
    """Constant model: any expression with * collapses to c. Bare var stays.
    Tautology iff both sides are products (c=c) OR same bare variable both sides.
    Constraint iff sides become bare variable vs c, or different bare variables.
    """
    L_op = isinstance(p["lhs"], Op)
    R_op = isinstance(p["rhs"], Op)
    if L_op and R_op:
        return "tautology"
    if not L_op and not R_op:
        # both bare variables
        if p["lhs"].name == p["rhs"].name:
            return "tautology"
        return "constraint"
    # one is product, one is variable -> variable = c -> constraint
    return "constraint"


def model_status_X(p):
    if simplify_X(p["lhs"]) == simplify_X(p["rhs"]):
        return "tautology"
    return "constraint"


# ---------------------------------------------------------------------------
# Step 1.5: pattern matchers for FP1/FP2/FP3
# ---------------------------------------------------------------------------

def _all_vars_unique(node):
    """Every variable appears at most once in `node`."""
    leaf_list = leaves(node)
    return len(leaf_list) == len(set(leaf_list))


def _t_strict(t, x):
    """T qualifies as a 'strict' slot for FP1/FP2: no x, no repeated vars."""
    if x in all_vars(t):
        return False
    return _all_vars_unique(t)


def is_FP1_class(p):
    """Eq1: x = x*T with T strict (no x, no repeats)."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    if not _is_var(R.left) or R.left.name != x:
        return False
    return _t_strict(R.right, x)


def is_FP2_class(p):
    """Eq1: x = T*x with T strict."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    if not _is_var(R.right) or R.right.name != x:
        return False
    return _t_strict(R.left, x)


def is_FP3_class(p):
    """Eq1: x*y=z*w (4 distinct single vars) OR a*a=y*z (y!=z singles, a not in RHS).
    NO nesting on either side."""
    L, R = p["lhs"], p["rhs"]
    if not isinstance(L, Op) or not isinstance(R, Op):
        return False
    if not (_is_var(L.left) and _is_var(L.right)
            and _is_var(R.left) and _is_var(R.right)):
        return False
    a, b = L.left.name, L.right.name
    c, d = R.left.name, R.right.name
    # variant 1: 4 distinct singles
    if len({a, b, c, d}) == 4:
        return True
    # variant 2: a*a=y*z, y!=z, a not in RHS
    if a == b and c != d and a != c and a != d:
        return True
    # mirror: y*z = a*a
    if c == d and a != b and c != a and c != b:
        return True
    return False


def fp1_eq2_true(p2):
    """FP1 forces a*b=a; Eq2 holds iff lm(LHS)=lm(RHS)."""
    return leftmost(p2["lhs"]) == leftmost(p2["rhs"])


def fp2_eq2_true(p2):
    return rightmost(p2["lhs"]) == rightmost(p2["rhs"])


def fp3_eq2_true(p2):
    """FP3 forces constant; TRUE iff (both sides have *) or (both bare same letter)."""
    L, R = p2["lhs"], p2["rhs"]
    if isinstance(L, Op) and isinstance(R, Op):
        return True
    if _is_var(L) and _is_var(R) and L.name == R.name:
        return True
    return False


# ---------------------------------------------------------------------------
# Step 2.5: D-SPINE
# ---------------------------------------------------------------------------

def is_pure_left_spine(node, x):
    """Pure left-spine of depth n>=1 with variable x ONLY at deepest left leaf.
    Returns the depth, or 0 if not a pure left spine.

    Shape: ((((x*T1)*T2)*...)*Tn) -- x at deepest left leaf, Tk on the right side.
    Each Tk should not contain x.
    """
    if _is_var(node):
        return 0
    depth = 0
    cur = node
    Ts = []
    while isinstance(cur, Op):
        Ts.append(cur.right)
        cur = cur.left
        depth += 1
    # cur is the deepest left leaf
    if not _is_var(cur) or cur.name != x:
        return 0
    # Check each T does not contain x
    for T in Ts:
        if x in all_vars(T):
            return 0
    return depth


def is_pure_right_spine(node, x):
    """Mirror: x at deepest right leaf."""
    if _is_var(node):
        return 0
    depth = 0
    cur = node
    Ts = []
    while isinstance(cur, Op):
        Ts.append(cur.left)
        cur = cur.right
        depth += 1
    if not _is_var(cur) or cur.name != x:
        return 0
    for T in Ts:
        if x in all_vars(T):
            return 0
    return depth


def d_spine_L_depths(p):
    """Returns (n,) where n is left-spine depth of Eq.RHS (with x = LHS)
    if Eq.LHS is a bare var, else None."""
    L = p["lhs"]
    if not _is_var(L):
        return None
    n = is_pure_left_spine(p["rhs"], L.name)
    if n == 0:
        return None
    return n


def d_spine_R_depths(p):
    L = p["lhs"]
    if not _is_var(L):
        return None
    n = is_pure_right_spine(p["rhs"], L.name)
    if n == 0:
        return None
    return n


# ---------------------------------------------------------------------------
# Step 3: B-class STRICT pattern matchers
# ---------------------------------------------------------------------------
# For variable-LHS classes: x = LHS var. Slots y,z,w = subexpressions
# satisfying: (1) Slot does not contain x. (2) Each slot: every var appears
# AT MOST ONCE.

def _strict_slot_ok(slot, x):
    """Slot does not contain x AND every var in slot appears at most once."""
    if x in all_vars(slot):
        return False
    return _all_vars_unique(slot)


def matches_71a(p):
    """x = x*T, T strict."""
    return is_FP1_class(p)


def matches_71b(p):
    """x = T*x, T strict."""
    return is_FP2_class(p)


def matches_112a(p):
    """x = (x*T1)*T2, both T1 and T2 strict (no x, no repeats)."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    # R = (x*T1) * T2
    inner = R.left
    T2 = R.right
    if not isinstance(inner, Op):
        return False
    if not _is_var(inner.left) or inner.left.name != x:
        return False
    T1 = inner.right
    return _strict_slot_ok(T1, x) and _strict_slot_ok(T2, x)


def matches_112b(p):
    """x = T1*(T2*x), both strict."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    T1 = R.left
    inner = R.right
    if not isinstance(inner, Op):
        return False
    if not _is_var(inner.right) or inner.right.name != x:
        return False
    T2 = inner.left
    return _strict_slot_ok(T1, x) and _strict_slot_ok(T2, x)


def matches_76a(p):
    """x = ((x*T1)*T2)*T3, all strict."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    T3 = R.right
    inner2 = R.left
    if not isinstance(inner2, Op):
        return False
    T2 = inner2.right
    inner1 = inner2.left
    if not isinstance(inner1, Op):
        return False
    if not _is_var(inner1.left) or inner1.left.name != x:
        return False
    T1 = inner1.right
    return (_strict_slot_ok(T1, x) and _strict_slot_ok(T2, x)
            and _strict_slot_ok(T3, x))


def matches_76b(p):
    """x = T1*(T2*(T3*x)), all strict."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    T1 = R.left
    inner1 = R.right
    if not isinstance(inner1, Op):
        return False
    T2 = inner1.left
    inner2 = inner1.right
    if not isinstance(inner2, Op):
        return False
    T3 = inner2.left
    if not _is_var(inner2.right) or inner2.right.name != x:
        return False
    return (_strict_slot_ok(T1, x) and _strict_slot_ok(T2, x)
            and _strict_slot_ok(T3, x))


def matches_K419(p):
    """Eq1 = x*y=z*w (4 distinct single vars) OR a*a=y*z (a not in RHS, y!=z singles)."""
    return is_FP3_class(p)


CLASS_FNS = {
    "71a": matches_71a,
    "71b": matches_71b,
    "112a": matches_112a,
    "112b": matches_112b,
    "76a": matches_76a,
    "76b": matches_76b,
    "K419": matches_K419,
}


def b3_class_of(p):
    """Return list of class names that p strictly matches. Multiple matches
    possible (e.g. x=x*y matches 71a only)."""
    return [c for c, fn in CLASS_FNS.items() if fn(p)]


B3_CROSS_EDGES = {
    "71a": {"112a", "76a"},
    "71b": {"112b", "76b"},
    "112a": {"76a"},
    "112b": {"76b"},
    "76a": set(),
    "76b": set(),
    "K419": set(),
}


# ---------------------------------------------------------------------------
# B3-LOOSE: 4-gate matcher for 112a/112b/76a/76b
# ---------------------------------------------------------------------------

def loose_match(p, cls):
    """Loose-match Eq for class cls in {112a,112b,76a,76b}.
    Returns True if shape matches and exactly one slot is "dirty" (contains x or
    has repeats). Also returns True if all slots are clean (strict match).
    Returns False otherwise.

    For our purposes, B3-LOOSE only fires when at least one match is loose (or
    strict on Eq2). The cheatsheet says "EXACTLY ONE slot is dirty" for the
    Eq1 side that's loose. We return (matches, n_dirty)."""
    L, R = p["lhs"], p["rhs"]
    if not _is_var(L):
        return False, None
    x = L.name
    if not isinstance(R, Op):
        return False, None

    slots = []
    if cls == "112a":
        # R = (x*T1)*T2
        inner = R.left
        T2 = R.right
        if not isinstance(inner, Op) or not _is_var(inner.left) or inner.left.name != x:
            return False, None
        slots = [inner.right, T2]
    elif cls == "112b":
        T1 = R.left
        inner = R.right
        if not isinstance(inner, Op) or not _is_var(inner.right) or inner.right.name != x:
            return False, None
        slots = [T1, inner.left]
    elif cls == "76a":
        T3 = R.right
        inner2 = R.left
        if not isinstance(inner2, Op):
            return False, None
        T2 = inner2.right
        inner1 = inner2.left
        if not isinstance(inner1, Op) or not _is_var(inner1.left) or inner1.left.name != x:
            return False, None
        T1 = inner1.right
        slots = [T1, T2, T3]
    elif cls == "76b":
        T1 = R.left
        inner1 = R.right
        if not isinstance(inner1, Op):
            return False, None
        T2 = inner1.left
        inner2 = inner1.right
        if not isinstance(inner2, Op) or not _is_var(inner2.right) or inner2.right.name != x:
            return False, None
        T3 = inner2.left
        slots = [T1, T2, T3]
    else:
        return False, None

    n_dirty = 0
    for s in slots:
        if x in all_vars(s):
            n_dirty += 1
        elif not _all_vars_unique(s):
            n_dirty += 1
    # loose allows AT MOST ONE dirty slot
    if n_dirty <= 1:
        return True, n_dirty
    return False, n_dirty


# ---------------------------------------------------------------------------
# B-SUB: substitution instance (greedy unification)
# ---------------------------------------------------------------------------

def try_b_sub(p1, p2):
    """Find substitution σ with σ(LHS1)=LHS2 AND σ(RHS1)=RHS2. Returns True iff
    greedy left-to-right unification succeeds.

    Implementation: walk both sides simultaneously; whenever Eq1 has a Var v,
    bind v -> corresponding subtree (consistent across uses). Whenever Eq1 has
    Op, Eq2 must also have Op; recurse on left and right.

    To avoid any ambiguity (Eq1 var can match anything), this is well-defined:
    structural recursion on the Eq1 tree.
    """
    sigma = {}

    def unify(t1, t2):
        if _is_var(t1):
            v = t1.name
            if v in sigma:
                return tree_eq(sigma[v], t2)
            sigma[v] = t2
            return True
        # t1 is Op
        if not isinstance(t2, Op):
            return False
        return unify(t1.left, t2.left) and unify(t1.right, t2.right)

    if not unify(p1["lhs"], p2["lhs"]):
        return False
    if not unify(p1["rhs"], p2["rhs"]):
        return False
    return True


# ---------------------------------------------------------------------------
# Step 0/1 quick rules
# ---------------------------------------------------------------------------

def fires_S0a(p1):
    """Eq1.LHS bare var absent from RHS."""
    L, R = p1["lhs"], p1["rhs"]
    return _is_var(L) and L.name not in all_vars(R)


def fires_S0b(p1):
    L, R = p1["lhs"], p1["rhs"]
    return _is_var(R) and R.name not in all_vars(L)


def fires_T1(p1, p2):
    """Eq2 tautology (both sides identical) OR Eq1 = Eq2 under renaming."""
    if tree_eq(p2["lhs"], p2["rhs"]):
        return True
    return canonicalize_equation(p1["lhs"], p1["rhs"]) == canonicalize_equation(p2["lhs"], p2["rhs"])


def fires_F0(p1, p2):
    """Eq1.LHS contains * but Eq2.LHS is a single variable. FALSE."""
    return isinstance(p1["lhs"], Op) and _is_var(p2["lhs"])


# ---------------------------------------------------------------------------
# Step 3 / Case A and Case B helpers
# ---------------------------------------------------------------------------

def case_a_3vars_check(p1):
    """Returns True if Eq1 has >= 3 distinct vars AND not the 'x in BOTH A and B' exception."""
    vars1 = all_vars(p1["lhs"]) | all_vars(p1["rhs"])
    if len(vars1) < 3:
        return False
    # Exception: LHS is variable x, RHS top-level A*B, x in BOTH A and B → go to Case B
    L, R = p1["lhs"], p1["rhs"]
    if _is_var(L) and isinstance(R, Op):
        x = L.name
        A, B = R.left, R.right
        if x in all_vars(A) and x in all_vars(B):
            return False  # exception triggered
    return True


def case_a_le2vars(p1):
    vars1 = all_vars(p1["lhs"]) | all_vars(p1["rhs"])
    return len(vars1) <= 2


def fires_B0(p1, p2):
    """Variable LHS + 6+ distinct vars (overall in Eq1) → TRUE."""
    if not _is_var(p1["lhs"]):
        return False
    vars1 = all_vars(p1["lhs"]) | all_vars(p1["rhs"])
    return len(vars1) >= 6


def fires_B1(p1, p2):
    """Eq1 LHS = A*B where A and B are BOTH single variable letters (A != B, NOT A*A).
    Eq1.RHS has variable NOT in {A,B}. Eq1.RHS does NOT contain BOTH A and B."""
    L = p1["lhs"]
    if not isinstance(L, Op):
        return False
    if not (_is_var(L.left) and _is_var(L.right)):
        return False
    A, B = L.left.name, L.right.name
    if A == B:
        return False
    rhs_vars = all_vars(p1["rhs"])
    # Eq1.RHS has variable NOT in {A,B}
    if not (rhs_vars - {A, B}):
        return False
    # Eq1.RHS does NOT contain BOTH A and B
    if A in rhs_vars and B in rhs_vars:
        return False
    return True


def fires_B2(p1, p2):
    """Eq1 MUST have variable LHS. Compound LHS → does not apply.
    Eq1 RHS top = x*T or T*x, T does NOT contain x.
    Fires if ANY: (a) T single var, (b) outer child of T is single var NOT in
    the other child, (c) T has 3+ distinct vars."""
    L, R = p1["lhs"], p1["rhs"]
    if not _is_var(L):
        return False
    x = L.name
    if not isinstance(R, Op):
        return False
    # x*T form
    T = None
    is_xT = False
    is_Tx = False
    if _is_var(R.left) and R.left.name == x:
        T = R.right
        is_xT = True
    elif _is_var(R.right) and R.right.name == x:
        T = R.left
        is_Tx = True
    else:
        return False
    if x in all_vars(T):
        return False
    # condition (a) T single var
    if _is_var(T):
        return True
    # condition (c) T has 3+ distinct vars
    if len(all_vars(T)) >= 3:
        return True
    # condition (b) outer child of T is single var NOT in the other child
    # For x*T, "outer child" of T = right child of T (the one furthest from x).
    # For T*x, "outer child" of T = left child of T.
    if isinstance(T, Op):
        if is_xT:
            outer = T.right
            other = T.left
        else:  # is_Tx
            outer = T.left
            other = T.right
        if _is_var(outer) and outer.name not in all_vars(other):
            return True
    return False


def fires_B_RPROJ_NARROW(p1, p2, valid_models):
    """ONLY Model R valid; Eq1.LHS=bare x; 3+ distinct vars;
    Eq1.RHS top-level A*B with B=x (BARE x at top-right, A arbitrary);
    Eq2.LHS compound → TRUE.  ⚠ If L also valid → does NOT fire."""
    if "R" not in valid_models:
        return False
    if "L" in valid_models:
        return False
    L = p1["lhs"]
    R = p1["rhs"]
    if not _is_var(L):
        return False
    vars1 = all_vars(p1["lhs"]) | all_vars(p1["rhs"])
    if len(vars1) < 3:
        return False
    if not isinstance(R, Op):
        return False
    if not (_is_var(R.right) and R.right.name == L.name):
        return False
    if not isinstance(p2["lhs"], Op):
        return False
    return True


# ---------------------------------------------------------------------------
# B3-LOOSE 4-gate
# ---------------------------------------------------------------------------

def fires_B3_LOOSE(p1, p2, valid_models):
    """Gates:
      (i) Eq1 loose-matches class C in {112a,112b,76a,76b} (top-level shape +
          exactly one dirty slot OR strict match).
      (ii) |Eq1 vars| >= 3
      (iii) Eq2 strict OR loose-matches the SAME class C
      (iv) Both Eq1 and Eq2 are tautologies under Model L (for 112a/76a) OR
           Model R (for 112b/76b).

    For "EXACTLY ONE" dirty slot: the cheatsheet says "at most one relaxation per
    side". We require Eq1 has at least one dirty slot (otherwise it'd be strict
    and B3_SAME/CROSS would have already fired). Actually, re-reading: B3-LOOSE
    fires only after STRICT both failed — so it must be a TRUE non-strict match
    on at least one side."""
    vars1 = all_vars(p1["lhs"]) | all_vars(p1["rhs"])
    if len(vars1) < 3:
        return False
    for cls in ("112a", "112b", "76a", "76b"):
        ok1, n_dirty1 = loose_match(p1, cls)
        if not ok1:
            continue
        ok2, n_dirty2 = loose_match(p2, cls)
        if not ok2:
            continue
        # gate (iv): tautology in matching model
        model = "L" if cls in ("112a", "76a") else "R"
        if model not in valid_models:
            continue
        # need to ensure Eq2 is also tautology in that model
        # (valid_models already encodes Eq1 tautology + Eq2 tautology)
        return True
    return False


# ---------------------------------------------------------------------------
# Scalar predict (for HF splits)
# ---------------------------------------------------------------------------

def predict_scalar(p1, p2):
    """Walk the cascade in RULE_ORDER, return rule name."""
    # Step 0
    if fires_S0a(p1):
        return "S0a"
    if fires_S0b(p1):
        return "S0b"
    # Step 1
    if fires_T1(p1, p2):
        return "T1"
    if fires_F0(p1, p2):
        return "F0"
    # Step 1.5 — FP1
    if is_FP1_class(p1):
        return "FP1_TRUE" if fp1_eq2_true(p2) else "FP1_FALSE"
    if is_FP2_class(p1):
        return "FP2_TRUE" if fp2_eq2_true(p2) else "FP2_FALSE"
    if is_FP3_class(p1):
        return "FP3_TRUE" if fp3_eq2_true(p2) else "FP3_FALSE"

    # Step 2 — find counterexamples and track validity
    valid_models = set()
    # Model L
    sl1 = model_status_L(p1)
    if sl1 == "tautology":
        sl2 = model_status_L(p2)
        if sl2 == "constraint":
            return "L"
        # tautology -> model VALID, inconclusive
        valid_models.add("L")
    # Model R
    sr1 = model_status_R(p1)
    if sr1 == "tautology":
        sr2 = model_status_R(p2)
        if sr2 == "constraint":
            return "R"
        valid_models.add("R")
    # Model K
    sk1 = model_status_K(p1)
    if sk1 == "tautology":
        sk2 = model_status_K(p2)
        if sk2 == "constraint":
            return "K"
        valid_models.add("K")
    # Model X
    sx1 = model_status_X(p1)
    if sx1 == "tautology":
        sx2 = model_status_X(p2)
        if sx2 == "constraint":
            return "X"
        valid_models.add("X")

    # Step 2.5 — D-SPINE
    n1_L = d_spine_L_depths(p1)
    if n1_L is not None and _is_var(p2["lhs"]):
        m2 = is_pure_left_spine(p2["rhs"], p2["lhs"].name)
        if m2 >= 1 and (m2 % n1_L != 0):
            return "D_SPINE_L"
    n1_R = d_spine_R_depths(p1)
    if n1_R is not None and _is_var(p2["lhs"]):
        m2 = is_pure_right_spine(p2["rhs"], p2["lhs"].name)
        if m2 >= 1 and (m2 % n1_R != 0):
            return "D_SPINE_R"

    # Step 3
    if not valid_models:
        # Case A
        if case_a_3vars_check(p1):
            return "CASE_A_3VARS_TRUE"
        if case_a_le2vars(p1):
            return "CASE_A_LE2VARS_FALSE"
        # falls through to default

    # Case B (some model valid)
    # B0
    if fires_B0(p1, p2):
        return "B0"
    # B1
    if fires_B1(p1, p2):
        return "B1"
    # B2
    if fires_B2(p1, p2):
        return "B2"
    # B-SUB
    if try_b_sub(p1, p2):
        return "B_SUB"
    # B3-SAME / B3-CROSS
    cls1 = b3_class_of(p1)
    cls2 = b3_class_of(p2)
    if cls1 and cls2:
        # B3-SAME
        if set(cls1) & set(cls2):
            return "B3_SAME"
        # B3-CROSS
        for c1 in cls1:
            edges = B3_CROSS_EDGES.get(c1, set())
            if edges & set(cls2):
                return "B3_CROSS"
    # B3-LOOSE
    if fires_B3_LOOSE(p1, p2, valid_models):
        return "B3_LOOSE"
    # B-RPROJ-narrow
    if fires_B_RPROJ_NARROW(p1, p2, valid_models):
        return "B_RPROJ_NARROW"

    return "DEFAULT_FALSE"


# ---------------------------------------------------------------------------
# Per-split runner (scalar)
# ---------------------------------------------------------------------------

def run_on_split(stem: str, ctx: ETPContext) -> dict:
    problems = load_split(stem)
    rows = []
    for p in problems:
        i_id = p["eq1_id"]
        j_id = p["eq2_id"]
        i = i_id - 1
        j = j_id - 1
        if 0 <= i < ctx.n_eq:
            p1 = ctx.parsed[i]
        else:
            p1 = _parse_eq(p["equation1"])
        if 0 <= j < ctx.n_eq:
            p2 = ctx.parsed[j]
        else:
            p2 = _parse_eq(p["equation2"])
        rule = predict_scalar(p1, p2)
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
# Vectorized full-ETP runner
# ---------------------------------------------------------------------------

def _per_eq_features(ctx: ETPContext) -> dict:
    """Compute per-equation feature arrays needed for the vectorized cascade."""
    n = ctx.n_eq
    parsed = ctx.parsed

    # --- Step 0
    s0a = np.array([fires_S0a(p) for p in parsed], dtype=bool)
    s0b = np.array([fires_S0b(p) for p in parsed], dtype=bool)

    # --- Step 1
    # T1 (Eq2 tautology) -> per-j flag
    t1_taut_j = np.array([tree_eq(p["lhs"], p["rhs"]) for p in parsed], dtype=bool)
    # T1 (Eq1=Eq2 under renaming) -> canonical equality match
    canon = [canonicalize_equation(p["lhs"], p["rhs"]) for p in parsed]

    # F0: Eq1.LHS contains * (per-i) and Eq2.LHS is single variable (per-j)
    f0_i = np.array([isinstance(p["lhs"], Op) for p in parsed], dtype=bool)
    f0_j = np.array([_is_var(p["lhs"]) for p in parsed], dtype=bool)

    # --- Step 1.5: FP1/FP2/FP3
    fp1_i = np.array([is_FP1_class(p) for p in parsed], dtype=bool)
    fp2_i = np.array([is_FP2_class(p) for p in parsed], dtype=bool)
    fp3_i = np.array([is_FP3_class(p) for p in parsed], dtype=bool)

    fp1_j = np.array([fp1_eq2_true(p) for p in parsed], dtype=bool)
    fp2_j = np.array([fp2_eq2_true(p) for p in parsed], dtype=bool)
    fp3_j = np.array([fp3_eq2_true(p) for p in parsed], dtype=bool)

    # --- Step 2: model status per-equation
    # status = "tautology" or "constraint"
    L_taut = np.array([model_status_L(p) == "tautology" for p in parsed], dtype=bool)
    R_taut = np.array([model_status_R(p) == "tautology" for p in parsed], dtype=bool)
    K_taut = np.array([model_status_K(p) == "tautology" for p in parsed], dtype=bool)
    X_taut = np.array([model_status_X(p) == "tautology" for p in parsed], dtype=bool)

    # --- Step 2.5: D-SPINE
    # depth of left-spine when Eq.LHS is bare var; 0 otherwise
    dspl = np.array([
        d_spine_L_depths(p) or 0 for p in parsed
    ], dtype=np.int32)
    dspr = np.array([
        d_spine_R_depths(p) or 0 for p in parsed
    ], dtype=np.int32)
    # Eq2.LHS bare var (per-j)
    eq_lhs_var = np.array([_is_var(p["lhs"]) for p in parsed], dtype=bool)

    # --- Step 3: distinct vars per equation
    n_vars1 = np.array([len(all_vars(p["lhs"]) | all_vars(p["rhs"])) for p in parsed],
                       dtype=np.int32)

    # Case A 3-vars TRUE (per-i): >=3 vars AND not exception
    case_a_3 = np.array([case_a_3vars_check(p) for p in parsed], dtype=bool)
    case_a_le2 = np.array([case_a_le2vars(p) for p in parsed], dtype=bool)

    # B0 (per-i): bare LHS AND >=6 vars
    b0_i = np.array([_is_var(p["lhs"]) and (len(all_vars(p["lhs"]) | all_vars(p["rhs"])) >= 6)
                     for p in parsed], dtype=bool)
    # B1 (per-i)
    def b1_flag(p):
        L = p["lhs"]
        if not isinstance(L, Op):
            return False
        if not (_is_var(L.left) and _is_var(L.right)):
            return False
        A, B = L.left.name, L.right.name
        if A == B:
            return False
        rhs_vars = all_vars(p["rhs"])
        if not (rhs_vars - {A, B}):
            return False
        if A in rhs_vars and B in rhs_vars:
            return False
        return True

    b1_i = np.array([b1_flag(p) for p in parsed], dtype=bool)

    # B2 (per-i)
    def b2_flag(p):
        L, R = p["lhs"], p["rhs"]
        if not _is_var(L):
            return False
        x = L.name
        if not isinstance(R, Op):
            return False
        T = None
        is_xT = False
        is_Tx = False
        if _is_var(R.left) and R.left.name == x:
            T = R.right
            is_xT = True
        elif _is_var(R.right) and R.right.name == x:
            T = R.left
            is_Tx = True
        else:
            return False
        if x in all_vars(T):
            return False
        if _is_var(T):
            return True
        if len(all_vars(T)) >= 3:
            return True
        if isinstance(T, Op):
            if is_xT:
                outer = T.right
                other = T.left
            else:
                outer = T.left
                other = T.right
            if _is_var(outer) and outer.name not in all_vars(other):
                return True
        return False

    b2_i = np.array([b2_flag(p) for p in parsed], dtype=bool)

    # B3 strict classes per equation
    b3_classes = [b3_class_of(p) for p in parsed]

    # B3-LOOSE: per-equation, set of classes c in {112a,112b,76a,76b} for which
    # the equation loose-matches AND the n_dirty count is in {0,1}.
    # We'll record (cls, n_dirty) sets.
    def loose_classes(p):
        out = []
        for cls in ("112a", "112b", "76a", "76b"):
            ok, n_dirty = loose_match(p, cls)
            if ok:
                out.append(cls)
        return out

    loose_cls_per_eq = [loose_classes(p) for p in parsed]

    # B-RPROJ-narrow: per-i flag captures shape conditions
    def brproj_i_flag(p):
        L = p["lhs"]
        R = p["rhs"]
        if not _is_var(L):
            return False
        vars1 = all_vars(L) | all_vars(R)
        if len(vars1) < 3:
            return False
        if not isinstance(R, Op):
            return False
        if not (_is_var(R.right) and R.right.name == L.name):
            return False
        return True

    brproj_i = np.array([brproj_i_flag(p) for p in parsed], dtype=bool)
    # B-RPROJ-narrow per-j: Eq2.LHS compound
    brproj_j = np.array([isinstance(p["lhs"], Op) for p in parsed], dtype=bool)

    return {
        "s0a": s0a, "s0b": s0b,
        "t1_taut_j": t1_taut_j,
        "canon": canon,
        "f0_i": f0_i, "f0_j": f0_j,
        "fp1_i": fp1_i, "fp1_j": fp1_j,
        "fp2_i": fp2_i, "fp2_j": fp2_j,
        "fp3_i": fp3_i, "fp3_j": fp3_j,
        "L_taut": L_taut, "R_taut": R_taut,
        "K_taut": K_taut, "X_taut": X_taut,
        "dspl": dspl, "dspr": dspr,
        "eq_lhs_var": eq_lhs_var,
        "n_vars1": n_vars1,
        "case_a_3": case_a_3, "case_a_le2": case_a_le2,
        "b0_i": b0_i, "b1_i": b1_i, "b2_i": b2_i,
        "b3_classes": b3_classes,
        "loose_cls_per_eq": loose_cls_per_eq,
        "brproj_i": brproj_i, "brproj_j": brproj_j,
        "parsed": parsed,
    }


def _t1_canon_mask(canon, n):
    """Build (n,n) bool mask: True where canon[i] == canon[j]."""
    mask = np.zeros((n, n), dtype=bool)
    canon_to_idxs = {}
    for i, c in enumerate(canon):
        canon_to_idxs.setdefault(c, []).append(i)
    for c, idxs in canon_to_idxs.items():
        arr = np.array(idxs, dtype=np.int64)
        ii, jj = np.meshgrid(arr, arr, indexing="ij")
        mask[ii.ravel(), jj.ravel()] = True
    return mask


def _dspine_mask(dsp_i, dsp_j_depths, eq_lhs_var_j, parsed):
    """Build mask where Eq1 has spine depth n>=1 AND Eq2 spine depth m>=1
    (with same x as bare LHS) AND n does NOT divide m.

    dsp_i: array[n] of spine depths for Eq1 (0 if not pure-spine pattern).
    dsp_j_depths: function (j) -> int spine depth for Eq2's right side using
        Eq2's LHS variable. We'll pass an array of length n giving for each j
        the spine depth of p_j['rhs'] using p_j['lhs'] as the variable.
    """
    n = len(parsed)
    n_arr = dsp_i  # per-i
    m_arr = dsp_j_depths  # per-j
    # mask[i,j] = (n_arr[i] >= 1) & (m_arr[j] >= 1) & (m_arr[j] % n_arr[i] != 0)
    n_safe = np.maximum(n_arr, 1)  # avoid /0; we mask by n_arr>=1 anyway
    valid_i = (n_arr >= 1)[:, None]
    valid_j = (m_arr >= 1)[None, :]
    mod = (m_arr[None, :] % n_safe[:, None])
    return valid_i & valid_j & (mod != 0)


def _b3_mask(b3_classes, n):
    """Build B3-SAME and B3-CROSS masks.
    B3_SAME: classes(i) ∩ classes(j) non-empty.
    B3_CROSS: any c1 in classes(i), c2 in classes(j) with c2 in B3_CROSS_EDGES[c1].
    """
    same = np.zeros((n, n), dtype=bool)
    cross = np.zeros((n, n), dtype=bool)

    # Group equations by class membership
    class_to_idx = {c: [] for c in CLASS_FNS}
    for i, cs in enumerate(b3_classes):
        for c in cs:
            class_to_idx[c].append(i)

    # SAME: for each class, all (i,j) where both are in that class
    for c, idxs in class_to_idx.items():
        if not idxs:
            continue
        arr = np.array(idxs, dtype=np.int64)
        ii, jj = np.meshgrid(arr, arr, indexing="ij")
        same[ii.ravel(), jj.ravel()] = True

    # CROSS: edges c1 -> c2
    for c1, edges in B3_CROSS_EDGES.items():
        for c2 in edges:
            i_idx = class_to_idx.get(c1, [])
            j_idx = class_to_idx.get(c2, [])
            if not i_idx or not j_idx:
                continue
            ai = np.array(i_idx, dtype=np.int64)
            aj = np.array(j_idx, dtype=np.int64)
            ii, jj = np.meshgrid(ai, aj, indexing="ij")
            cross[ii.ravel(), jj.ravel()] = True

    return same, cross


def _b3_loose_mask(loose_cls_per_eq, n_vars1, L_taut, R_taut, n):
    """B3-LOOSE mask. For each class C in {112a,112b,76a,76b}: mask[i,j] iff
    Eq1 loose-matches C AND Eq2 loose-matches C AND |Eq1 vars|>=3 AND
    appropriate model is tautology in BOTH Eq1 and Eq2."""
    mask = np.zeros((n, n), dtype=bool)
    class_to_idx = {c: [] for c in ("112a", "112b", "76a", "76b")}
    for i, cs in enumerate(loose_cls_per_eq):
        for c in cs:
            if c in class_to_idx:
                class_to_idx[c].append(i)

    for cls, idxs in class_to_idx.items():
        if not idxs:
            continue
        idx_arr = np.array(idxs, dtype=np.int64)
        # gate (ii) per i: n_vars1>=3
        i_ok = (n_vars1[idx_arr] >= 3)
        # gate (iv) for class
        if cls in ("112a", "76a"):
            taut = L_taut
        else:
            taut = R_taut
        i_taut = taut[idx_arr]
        valid_i = idx_arr[i_ok & i_taut]
        if len(valid_i) == 0:
            continue
        # j must also be in idxs and be tautology in same model
        j_ok = taut[idx_arr]
        valid_j = idx_arr[j_ok]
        if len(valid_j) == 0:
            continue
        ii, jj = np.meshgrid(valid_i, valid_j, indexing="ij")
        mask[ii.ravel(), jj.ravel()] = True
    return mask


def _b_sub_mask(parsed, n):
    """Build B-SUB mask. This is O(n^2) tree unifications. For tractability
    on the full 22M ETP, we build it as follows:
      For each j, we DON'T iterate every i; instead, we observe that B-SUB
      requires σ(LHS1)=LHS2 AND σ(RHS1)=RHS2. We pre-bucket equations by
      a coarse hash and then do per-pair unification within buckets.
    For the full ETP, this is too expensive. We approximate B_SUB by:
      - skip in vectorized version (i.e. mask of zeros). Document as
        "B_SUB approximate -- vectorized run drops it."
    """
    return np.zeros((n, n), dtype=bool)


def _brproj_narrow_mask(brproj_i, brproj_j, R_taut, L_taut, n):
    """B-RPROJ-narrow:
      Eq1 shape OK (per-i), Eq2.LHS compound (per-j),
      R valid AND L NOT valid → both Eq1 and Eq2 R-tautology AND
      (Eq1 not L-tautology OR Eq2 not L-tautology -> L not in valid_models).
    """
    # R valid: R_taut[i] AND R_taut[j]
    r_valid = R_taut[:, None] & R_taut[None, :]
    # L valid: L_taut[i] AND L_taut[j]
    l_valid = L_taut[:, None] & L_taut[None, :]
    return brproj_i[:, None] & brproj_j[None, :] & r_valid & ~l_valid


def build_fires_for_rule(ctx: ETPContext, feats: dict):
    """Closure that returns the candidate-fire mask for each rule. The driver
    then walks RULE_ORDER and assigns the first-firing rule per (i,j).
    """
    n = ctx.n_eq
    parsed = feats["parsed"]

    # Pre-build d_spine arrays for Eq2 (using Eq2's LHS as variable):
    # For each j: spine depth of p_j['rhs'] using p_j['lhs'] (var) name.
    dspl_j = np.zeros(n, dtype=np.int32)
    dspr_j = np.zeros(n, dtype=np.int32)
    for j, p in enumerate(parsed):
        if _is_var(p["lhs"]):
            dspl_j[j] = is_pure_left_spine(p["rhs"], p["lhs"].name)
            dspr_j[j] = is_pure_right_spine(p["rhs"], p["lhs"].name)

    # Pre-built static masks
    t1_canon_mask_cache = {"m": None}

    def get_t1_mask():
        if t1_canon_mask_cache["m"] is not None:
            return t1_canon_mask_cache["m"]
        canon_eq_mask = _t1_canon_mask(feats["canon"], n)
        # Eq2 tautology fires for any i, j where eq2 tautology (per-j)
        m = (np.broadcast_to(feats["t1_taut_j"][None, :], (n, n))
             | canon_eq_mask)
        t1_canon_mask_cache["m"] = m
        return m

    b3_masks_cache = {"same": None, "cross": None}

    def ensure_b3():
        if b3_masks_cache["same"] is None:
            same, cross = _b3_mask(feats["b3_classes"], n)
            b3_masks_cache["same"] = same
            b3_masks_cache["cross"] = cross

    b3_loose_cache = {"m": None}

    def get_b3_loose():
        if b3_loose_cache["m"] is None:
            b3_loose_cache["m"] = _b3_loose_mask(
                feats["loose_cls_per_eq"], feats["n_vars1"],
                feats["L_taut"], feats["R_taut"], n)
        return b3_loose_cache["m"]

    def fires_for_rule(name):
        if name == "S0a":
            return np.broadcast_to(feats["s0a"][:, None], (n, n)).copy()
        if name == "S0b":
            return np.broadcast_to(feats["s0b"][:, None], (n, n)).copy()
        if name == "T1":
            return get_t1_mask()
        if name == "F0":
            return feats["f0_i"][:, None] & feats["f0_j"][None, :]
        if name == "FP1_TRUE":
            return feats["fp1_i"][:, None] & feats["fp1_j"][None, :]
        if name == "FP1_FALSE":
            return feats["fp1_i"][:, None] & ~feats["fp1_j"][None, :]
        if name == "FP2_TRUE":
            return feats["fp2_i"][:, None] & feats["fp2_j"][None, :]
        if name == "FP2_FALSE":
            return feats["fp2_i"][:, None] & ~feats["fp2_j"][None, :]
        if name == "FP3_TRUE":
            return feats["fp3_i"][:, None] & feats["fp3_j"][None, :]
        if name == "FP3_FALSE":
            return feats["fp3_i"][:, None] & ~feats["fp3_j"][None, :]
        if name == "L":
            # Eq1 L-taut AND Eq2 NOT L-taut
            return feats["L_taut"][:, None] & ~feats["L_taut"][None, :]
        if name == "R":
            return feats["R_taut"][:, None] & ~feats["R_taut"][None, :]
        if name == "K":
            return feats["K_taut"][:, None] & ~feats["K_taut"][None, :]
        if name == "X":
            return feats["X_taut"][:, None] & ~feats["X_taut"][None, :]
        if name == "D_SPINE_L":
            # Eq1: bare LHS + pure left-spine depth>=1
            # Eq2: bare LHS + pure left-spine depth>=1 + n∤m
            n_arr = feats["dspl"]
            m_arr = dspl_j
            # avoid div by zero
            n_safe = np.maximum(n_arr, 1)
            valid_i = (n_arr >= 1)[:, None]
            valid_j = (m_arr >= 1)[None, :] & feats["eq_lhs_var"][None, :]
            mod = (m_arr[None, :] % n_safe[:, None])
            return valid_i & valid_j & (mod != 0)
        if name == "D_SPINE_R":
            n_arr = feats["dspr"]
            m_arr = dspr_j
            n_safe = np.maximum(n_arr, 1)
            valid_i = (n_arr >= 1)[:, None]
            valid_j = (m_arr >= 1)[None, :] & feats["eq_lhs_var"][None, :]
            mod = (m_arr[None, :] % n_safe[:, None])
            return valid_i & valid_j & (mod != 0)
        if name == "CASE_A_3VARS_TRUE":
            # All four models aborted: Eq1 NOT L-taut AND NOT R-taut AND NOT K-taut AND NOT X-taut.
            # Plus per-i case_a_3 flag.
            no_model_i = (~feats["L_taut"]) & (~feats["R_taut"]) & (~feats["K_taut"]) & (~feats["X_taut"])
            return np.broadcast_to((no_model_i & feats["case_a_3"])[:, None], (n, n)).copy()
        if name == "CASE_A_LE2VARS_FALSE":
            no_model_i = (~feats["L_taut"]) & (~feats["R_taut"]) & (~feats["K_taut"]) & (~feats["X_taut"])
            return np.broadcast_to((no_model_i & feats["case_a_le2"])[:, None], (n, n)).copy()
        if name == "B0":
            return np.broadcast_to(feats["b0_i"][:, None], (n, n)).copy()
        if name == "B1":
            return np.broadcast_to(feats["b1_i"][:, None], (n, n)).copy()
        if name == "B2":
            return np.broadcast_to(feats["b2_i"][:, None], (n, n)).copy()
        if name == "B_SUB":
            # Vectorized B_SUB skipped for the full ETP; we return zeros.
            # (Per-pair unification on 22M pairs is intractable.)
            return _b_sub_mask(parsed, n)
        if name == "B3_SAME":
            ensure_b3()
            return b3_masks_cache["same"]
        if name == "B3_CROSS":
            ensure_b3()
            return b3_masks_cache["cross"]
        if name == "B3_LOOSE":
            return get_b3_loose()
        if name == "B_RPROJ_NARROW":
            return _brproj_narrow_mask(
                feats["brproj_i"], feats["brproj_j"],
                feats["R_taut"], feats["L_taut"], n)
        if name == "DEFAULT_FALSE":
            return np.ones((n, n), dtype=bool)
        raise KeyError(f"Unknown rule {name!r}")

    return fires_for_rule


def run_full_etp_summary(ctx: ETPContext, feats: dict | None = None) -> dict:
    if feats is None:
        feats = _per_eq_features(ctx)
    fires_for_rule = build_fires_for_rule(ctx, feats)
    return run_full_etp(ctx, fires_for_rule, RULE_ORDER, TRUE_RULES,
                        progress_label="yan-biao-ETP")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _md_table_for_split(s: dict) -> str:
    n, nc = s["n"], s["n_correct"]
    cf = s["confusion"]
    out = [f"### `{s['dataset']}`  —  accuracy {nc}/{n} = {nc/n*100:.2f}%"]
    out.append("")
    out.append(f"Confusion: TP={cf['tp']}, FP={cf['fp']}, TN={cf['tn']}, FN={cf['fn']}")
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
        out.append(f"| {rule} | {verdict} | {bs['n']} | {correct} | {wrong} | {prec:.1f}% |")
    out.append("")
    return "\n".join(out)


def main():
    out_dir = ROOT / "analysis" / "results" / "yan-biao"
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.stderr.write("Loading ETP context (parse + compile + gold)...\n")
    t0 = time.time()
    ctx = load_etp_context(load_gold=True)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s "
                     f"(n_eq={ctx.n_eq}, gold loaded={ctx.gold is not None})\n")

    sys.stderr.write("Computing per-equation features...\n")
    t0 = time.time()
    feats = _per_eq_features(ctx)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s\n")

    summaries = {}

    sys.stderr.write("\n=== Splits ===\n")
    for stem in SPLITS:
        sys.stderr.write(f"  running {stem}...\n")
        s = run_on_split(stem, ctx)
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
    md = ["# yan-biao.txt programmatic checker — summary", ""]
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
