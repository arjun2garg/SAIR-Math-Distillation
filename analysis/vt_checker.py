"""Programmatic ("ceiling") checker for the vt.txt cheatsheet.

Implements every named rule of vt.txt's deterministic cascade:

  Step 1 (TRUE shortcuts):    X1, X2, X3
  Step 2 (FALSE separators):  LP, RP, XOR
  Step 3 (forced behavior):   F1_TRUE/F1_FALSE, F2_TRUE/F2_FALSE,
                              F3_TRUE/F3_FALSE, F4_TRUE/F4_FALSE
  Step 4 (FALSE affine):      A1..A10, C_PROBE
  Step 5 (FALSE heuristics):  H1..H6
  Step 6 (TRUE hubs):         HUB_Eq41, HUB_Eq46, HUB_Eq6
  Step 7 (default):           DEFAULT_TRUE

The cascade walks the rules in vt.txt order. Each rule has a single verdict
(TRUE or FALSE); the first rule whose mask is True for (i, j) wins.

Two entry points:
    run_on_split(stem, ctx)        -> per-split scalar evaluation
    run_full_etp_summary(ctx)      -> vectorized 4694x4694 evaluation

The driver runs all 9 SAIR splits + the full ETP and writes results to
`analysis/results/vt/`.
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

RULE_ORDER = [
    # Step 1 — TRUE shortcuts
    "X1", "X2", "X3",
    # Step 2 — FALSE separators
    "LP", "RP", "XOR",
    # Step 3 — forced behavior (TRUE or FALSE depending on Eq2)
    "F1_TRUE", "F1_FALSE",
    "F2_TRUE", "F2_FALSE",
    "F3_TRUE", "F3_FALSE",
    "F4_TRUE", "F4_FALSE",
    # Step 4 — FALSE affine probes
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "C_PROBE",
    # Step 5 — FALSE heuristics
    "H1", "H2", "H3", "H4", "H5", "H6",
    # Step 6 — TRUE hubs
    "HUB_Eq41", "HUB_Eq46", "HUB_Eq6",
    # Step 7 — default
    "DEFAULT_TRUE",
]

TRUE_RULES = {
    "X1", "X2", "X3",
    "F1_TRUE", "F2_TRUE", "F3_TRUE", "F4_TRUE",
    "HUB_Eq41", "HUB_Eq46", "HUB_Eq6",
    "DEFAULT_TRUE",
}


# ---------------------------------------------------------------------------
# 2. Tree helpers
# ---------------------------------------------------------------------------

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


def left_spine_depth(node):
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


def _is_var(n):
    return isinstance(n, Var)


def tree_eq(a, b):
    if isinstance(a, Var) and isinstance(b, Var):
        return a.name == b.name
    if isinstance(a, Op) and isinstance(b, Op):
        return tree_eq(a.left, b.left) and tree_eq(a.right, b.right)
    return False


def canonicalize_equation(lhs, rhs):
    """Canonical form for equation up to variable renaming AND side-swap."""
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
# 3. Step-0 features per equation
# ---------------------------------------------------------------------------

def _bare_features(p):
    """Compute bare/kind/occ/shortest_len features per Eq1 spec from vt.txt."""
    L, R = p["lhs"], p["rhs"]
    bare = None  # 'L' if LHS is bare, 'R' if RHS is bare, None
    bare_var = None
    other = None
    if _is_var(L) and not _is_var(R):
        bare = "L"
        bare_var = L.name
        other = R
    elif _is_var(R) and not _is_var(L):
        bare = "R"
        bare_var = R.name
        other = L
    elif _is_var(L) and _is_var(R):
        # Both sides bare variables — treat as bare with the same var (or singleton)
        bare = "L"
        bare_var = L.name
        other = R  # This is a Var
    if bare is None:
        return {"bare": False, "kind": "N", "occ": 0, "shortest_len": 0,
                "bare_var": None}

    # If other is a Var, occ = 1 if equal name else 0; kind = "X" if absent
    if _is_var(other):
        if other.name == bare_var:
            return {"bare": True, "kind": "L", "occ": 1, "shortest_len": 0,
                    "bare_var": bare_var}
        else:
            return {"bare": True, "kind": "X", "occ": 0, "shortest_len": 0,
                    "bare_var": bare_var}

    # Walk other tree, collecting all paths to occurrences of bare_var
    paths = []  # list of strings of L/R

    def walk(n, path):
        if isinstance(n, Var):
            if n.name == bare_var:
                paths.append(path)
            return
        walk(n.left, path + "L")
        walk(n.right, path + "R")

    walk(other, "")

    occ = len(paths)
    if occ == 0:
        return {"bare": True, "kind": "X", "occ": 0, "shortest_len": 0,
                "bare_var": bare_var}

    # First-occurrence path = first appended path (left-to-right traversal)
    first_path = paths[0]
    if all(c == "L" for c in first_path):
        kind = "L"
    elif all(c == "R" for c in first_path):
        kind = "R"
    else:
        kind = "M"
    shortest_len = min(len(p) for p in paths)
    return {"bare": True, "kind": kind, "occ": occ, "shortest_len": shortest_len,
            "bare_var": bare_var}


def _features(p):
    """Return all step-0 features for one equation."""
    L, R = p["lhs"], p["rhs"]
    lm_l, lm_r = leftmost(L), leftmost(R)
    rm_l, rm_r = rightmost(L), rightmost(R)
    LP = (lm_l == lm_r)
    RP = (rm_l == rm_r)
    a, b = _occ_dict(L), _occ_dict(R)
    keys = set(a) | set(b)
    XOR = all((a.get(k, 0) % 2) == (b.get(k, 0) % 2) for k in keys)
    vars_ = a.keys() | b.keys()
    n_vars = len(vars_)
    dup = sum(a.values()) + sum(b.values()) - n_vars
    bf = _bare_features(p)
    return {
        "leftmost_lhs": lm_l, "leftmost_rhs": lm_r,
        "rightmost_lhs": rm_l, "rightmost_rhs": rm_r,
        "LP": LP, "RP": RP, "XOR": XOR,
        "vars": n_vars, "dup": dup,
        "bare": bf["bare"], "kind": bf["kind"],
        "occ": bf["occ"], "shortest_len": bf["shortest_len"],
        "bare_var": bf["bare_var"],
    }


# ---------------------------------------------------------------------------
# 4. Step-1 TRUE shortcuts
# ---------------------------------------------------------------------------

def fires_X1(p1, p2):
    """X1: Eq2's two sides syntactically identical."""
    return tree_eq(p2["lhs"], p2["rhs"])


def fires_X2(p1, p2):
    """X2: Eq1 and Eq2 are the same law up to rename or side-swap."""
    return canonicalize_equation(p1["lhs"], p1["rhs"]) == \
        canonicalize_equation(p2["lhs"], p2["rhs"])


def fires_X3(p1, p2):
    """X3: Eq1 has a lone-variable side absent from the other."""
    L, R = p1["lhs"], p1["rhs"]
    if _is_var(L) and L.name not in all_vars(R):
        return True
    if _is_var(R) and R.name not in all_vars(L):
        return True
    return False


# ---------------------------------------------------------------------------
# 5. Step-3 forced behavior recognition
# ---------------------------------------------------------------------------

def f1_eq1_match(p):
    """F1: Eq1 matches `x = x*y` (any rename or side-swap, x != y)."""
    L, R = p["lhs"], p["rhs"]
    for A, B in ((L, R), (R, L)):
        if _is_var(A) and isinstance(B, Op) and _is_var(B.left) and _is_var(B.right):
            if A.name == B.left.name and B.left.name != B.right.name:
                return True
    return False


def f2_eq1_match(p):
    """F2: Eq1 matches `x = y*x`."""
    L, R = p["lhs"], p["rhs"]
    for A, B in ((L, R), (R, L)):
        if _is_var(A) and isinstance(B, Op) and _is_var(B.left) and _is_var(B.right):
            if A.name == B.right.name and B.left.name != B.right.name:
                return True
    return False


def f3_eq1_match(p):
    """F3: both sides products of bare variables, share left child, differ in right."""
    L, R = p["lhs"], p["rhs"]
    if not (isinstance(L, Op) and isinstance(R, Op)):
        return False
    if not (_is_var(L.left) and _is_var(L.right)
            and _is_var(R.left) and _is_var(R.right)):
        return False
    return (L.left.name == R.left.name) and (L.right.name != R.right.name)


def f4_eq1_match(p):
    """F4: both sides products of bare variables, share right child, differ in left."""
    L, R = p["lhs"], p["rhs"]
    if not (isinstance(L, Op) and isinstance(R, Op)):
        return False
    if not (_is_var(L.left) and _is_var(L.right)
            and _is_var(R.left) and _is_var(R.right)):
        return False
    return (L.right.name == R.right.name) and (L.left.name != R.left.name)


# ---------------------------------------------------------------------------
# 6. Step-4 affine probes
# ---------------------------------------------------------------------------

# Probe specifications: (p, q, c, m) over Z_m.
PROBES = {
    "A1":  (0,  1, 1, 3),
    "A2":  (1,  0, 1, 3),
    "A3":  (1,  1, 0, 3),
    "A4":  (1, -1, 0, 3),
    "A5":  (-1, -1, 0, 3),
    "A6":  (-1,  2, 0, 4),
    "A7":  (1,  2, 0, 4),
    "A8":  (2,  1, 0, 4),
    "A9":  (2,  1, 1, 4),
    "A10": (-2, -2, 0, 5),
    # "C_PROBE" uses (0,0,1,2) — every product → constant 1.
}


def affine_normal_form(node, var_to_idx, p, q, c, m):
    """Recursively compute the linear normal form of `node`.

    Returns a numpy array of length (n_vars + 1): coefficients[0..n-1] for
    each variable, coefficients[-1] for the constant. All values mod m.
    """
    n = len(var_to_idx)
    if isinstance(node, Var):
        out = np.zeros(n + 1, dtype=np.int64)
        out[var_to_idx[node.name]] = 1
        return out
    L = affine_normal_form(node.left, var_to_idx, p, q, c, m)
    R = affine_normal_form(node.right, var_to_idx, p, q, c, m)
    out = (p * L + q * R) % m
    out[-1] = (out[-1] + c) % m
    return out


def equation_holds_under_probe(p, probe):
    """Compute whether the equation `p` holds under the affine probe."""
    p_, q_, c_, m_ = probe
    vars_in_eq = sorted(all_vars(p["lhs"]) | all_vars(p["rhs"]))
    var_to_idx = {v: i for i, v in enumerate(vars_in_eq)}
    L = affine_normal_form(p["lhs"], var_to_idx, p_, q_, c_, m_)
    R = affine_normal_form(p["rhs"], var_to_idx, p_, q_, c_, m_)
    return np.array_equal(L, R)


# Probe C: every product evaluates to constant 1; lone variables stay variable.
# Encode as: a Var x → {var x: 1, const: 0}; an Op → {const: 1} (no variables).
def c_probe_form(node, var_to_idx):
    """Return (vars-coeffs, const) for probe C. Vars-coeffs is np.int64 array
    of length n_vars; const is 0 or 1."""
    n = len(var_to_idx)
    if isinstance(node, Var):
        out = np.zeros(n, dtype=np.int64)
        out[var_to_idx[node.name]] = 1
        return out, 0
    # Op → constant 1, no variables
    return np.zeros(n, dtype=np.int64), 1


def c_probe_holds(p):
    vars_in_eq = sorted(all_vars(p["lhs"]) | all_vars(p["rhs"]))
    var_to_idx = {v: i for i, v in enumerate(vars_in_eq)}
    Lv, Lc = c_probe_form(p["lhs"], var_to_idx)
    Rv, Rc = c_probe_form(p["rhs"], var_to_idx)
    return np.array_equal(Lv, Rv) and (Lc == Rc)


# ---------------------------------------------------------------------------
# 7. Step-5 heuristics
# ---------------------------------------------------------------------------

def fires_H1(s, t):
    """H1: s_kind=M, s_vars>=4, t_kind=X."""
    return s["kind"] == "M" and s["vars"] >= 4 and t["kind"] == "X"


def fires_H2(s, t):
    """H2: s_kind=L, s_shortest_len=1, s_dup>=3, t_bare=NO, t_dup>=3, t_vars<=3."""
    return (s["kind"] == "L" and s["shortest_len"] == 1 and s["dup"] >= 3
            and (not t["bare"]) and t["dup"] >= 3 and t["vars"] <= 3)


def fires_H3(s, t):
    """H3: s_kind=M, s_occ=2, RP(Eq1)=NO."""
    return s["kind"] == "M" and s["occ"] == 2 and (not s["RP"])


def fires_H4(s, t):
    """H4: s_shortest_len=1, s_occ=3."""
    return s["shortest_len"] == 1 and s["occ"] == 3


def fires_H5(s, t):
    """H5: s_kind=M, s_shortest_len=3, s_occ=2."""
    return s["kind"] == "M" and s["shortest_len"] == 3 and s["occ"] == 2


def fires_H6(s, t):
    """H6: s_kind=L, t_occ=2, t_vars=4."""
    return s["kind"] == "L" and t["occ"] == 2 and t["vars"] == 4


# ---------------------------------------------------------------------------
# 8. Step-6 hub verification
# ---------------------------------------------------------------------------

def hub_eq41_eq1_match(p):
    """Eq1 equates two products with completely disjoint variable sets."""
    L, R = p["lhs"], p["rhs"]
    if not (isinstance(L, Op) and isinstance(R, Op)):
        return False
    return all_vars(L).isdisjoint(all_vars(R))


def hub_eq46_eq1_match(p):
    """Eq1 is P=Q with no variables shared (same as Eq41 recognition).

    Since Eq46 strictly subsumes Eq41 (all products equal is stronger), we
    keep both rule names but use the same recognition predicate; cascading
    will pick up the first one that matches (Eq41).
    """
    return hub_eq41_eq1_match(p)


def hub_eq6_eq1_match(p):
    """Eq1 has a bare variable on one side, other side reduces to a
    self-product (every variable appears with the same name forced equal).

    Recognition: Eq1 has a bare-var side and the non-bare side, when every
    variable other than the bare one is identified with the bare one, would
    still be a valid 'self-product'. The clean canonical pattern: Eq1 looks
    like `x = y◇y` up to rename/side-swap, OR more generally the non-bare
    side is f◇f for some f (possibly itself a tree, but since vt.txt names it
    `x = y◇y`, we use the strict pattern: non-bare side is Op with left==right
    and the result identifies all variables on that side).
    """
    L, R = p["lhs"], p["rhs"]
    for A, B in ((L, R), (R, L)):
        if _is_var(A) and isinstance(B, Op):
            # Strict: B = u*u where u is a single variable (canonical hub).
            if (_is_var(B.left) and _is_var(B.right)
                    and B.left.name == B.right.name):
                return True
    return False


# Hub TRUE iff Eq2 holds in the "easy" magma:
#   HUB-Eq41 and HUB-Eq46: constant magma (all products = c).
#   HUB-Eq6: idempotent magma (a*a=a) — concretely, MAX semilattice.

def constant_magma_holds(p):
    """In constant magma a*b=c, every product = c, lone vars stay as vars.

    Equation holds iff both sides reduce to the same form. Two sides in a
    constant magma: a Var subtree stays as that var; any Op becomes c.
    For the equation to hold over ALL constant magmas, both sides must agree
    on this 'shape' — i.e. either both are the same lone variable, or both
    are products (so both equal c).
    """
    L, R = p["lhs"], p["rhs"]
    if isinstance(L, Op) and isinstance(R, Op):
        return True
    if _is_var(L) and _is_var(R):
        return L.name == R.name
    return False


def idempotent_magma_holds(p):
    """In an idempotent magma (a*a=a), check whether Eq2 holds. We use the
    MAX semilattice on {0,1,2} as a witness; if the equation fails there, we
    know it's not in *all* idempotent magmas. Approximate: check satisfaction
    in the MAX_3 magma. (Computed via the satisfaction-vector cache when
    available; for fallback we check structurally.)

    For structural fallback: since we just need a sound TRUE rule, we use a
    conservative check — Eq2 holds in MAX semilattice iff it holds when
    interpreted via 'leftmost==rightmost' on a totally ordered set... too
    fragile. Instead, use the precomputed satisfaction vector via the magma
    library. We accept the approximation here.
    """
    # Approximation: use the structural check that both sides reduce to the
    # same variable when we assume idempotence collapses self-products. This
    # is too loose. We rely instead on the satisfaction vector when called
    # via vectorized path.
    return None  # signal: use cached satisfaction vector


# ---------------------------------------------------------------------------
# 9. Vectorize per-equation features
# ---------------------------------------------------------------------------

def _per_eq_features(ctx: ETPContext):
    n = ctx.n_eq
    parsed = ctx.parsed
    feats = [_features(p) for p in parsed]

    # Step-0 features as numpy arrays
    LP = np.array([f["LP"] for f in feats], dtype=bool)
    RP = np.array([f["RP"] for f in feats], dtype=bool)
    XOR = np.array([f["XOR"] for f in feats], dtype=bool)

    bare = np.array([f["bare"] for f in feats], dtype=bool)
    kind = np.array([f["kind"] for f in feats])  # str array
    occ = np.array([f["occ"] for f in feats], dtype=np.int32)
    shortest_len = np.array([f["shortest_len"] for f in feats], dtype=np.int32)
    n_vars_arr = np.array([f["vars"] for f in feats], dtype=np.int32)
    dup = np.array([f["dup"] for f in feats], dtype=np.int32)

    # Step-1 X1, X3 are per-equation:
    x1_eq2 = np.array([tree_eq(p["lhs"], p["rhs"]) for p in parsed], dtype=bool)
    x3_eq1 = np.array([fires_X3(p, p) for p in parsed], dtype=bool)

    # X2 — canonical equation form per i; group by canonical form.
    x2_canon = [canonicalize_equation(p["lhs"], p["rhs"]) for p in parsed]

    # Step-3 forced shapes — per Eq1.
    f1_eq1 = np.array([f1_eq1_match(p) for p in parsed], dtype=bool)
    f2_eq1 = np.array([f2_eq1_match(p) for p in parsed], dtype=bool)
    f3_eq1 = np.array([f3_eq1_match(p) for p in parsed], dtype=bool)
    f4_eq1 = np.array([f4_eq1_match(p) for p in parsed], dtype=bool)

    # F1 TRUE iff LP(Eq2)=YES; F2 TRUE iff RP(Eq2)=YES.
    # F3: leftmost match AND left-spine-depth match; F4: rightmost + right-spine-depth.
    f3_eq2 = np.array([(leftmost(p["lhs"]) == leftmost(p["rhs"])
                        and left_spine_depth(p["lhs"]) == left_spine_depth(p["rhs"]))
                       for p in parsed], dtype=bool)
    f4_eq2 = np.array([(rightmost(p["lhs"]) == rightmost(p["rhs"])
                        and right_spine_depth(p["lhs"]) == right_spine_depth(p["rhs"]))
                       for p in parsed], dtype=bool)

    # Step-4 probes — for each probe, per-equation: holds?
    probe_holds = {}
    for name, probe in PROBES.items():
        probe_holds[name] = np.array([equation_holds_under_probe(p, probe)
                                      for p in parsed], dtype=bool)
    probe_holds["C_PROBE"] = np.array([c_probe_holds(p) for p in parsed], dtype=bool)

    # Step-6 hub recognitions — Eq1.
    hub41_eq1 = np.array([hub_eq41_eq1_match(p) for p in parsed], dtype=bool)
    hub46_eq1 = np.array([hub_eq46_eq1_match(p) for p in parsed], dtype=bool)
    hub6_eq1 = np.array([hub_eq6_eq1_match(p) for p in parsed], dtype=bool)

    # Eq2 conditions:
    # - constant magma: as defined; both sides Op or both same-var.
    const_holds = np.array([constant_magma_holds(p) for p in parsed], dtype=bool)
    # - idempotent: use MAX_3 satisfaction vector.
    from _common import MAGMA_LIB, get_sat_vector
    max3_sv = get_sat_vector(ctx, "MAX_3", MAGMA_LIB["MAX_3"])

    return {
        "LP": LP, "RP": RP, "XOR": XOR,
        "bare": bare, "kind": kind, "occ": occ,
        "shortest_len": shortest_len, "n_vars": n_vars_arr, "dup": dup,
        "x1_eq2": x1_eq2, "x3_eq1": x3_eq1, "x2_canon": x2_canon,
        "f1_eq1": f1_eq1, "f2_eq1": f2_eq1,
        "f3_eq1": f3_eq1, "f3_eq2": f3_eq2,
        "f4_eq1": f4_eq1, "f4_eq2": f4_eq2,
        "probe_holds": probe_holds,
        "hub41_eq1": hub41_eq1, "hub46_eq1": hub46_eq1, "hub6_eq1": hub6_eq1,
        "const_holds": const_holds, "max3_sv": max3_sv,
    }


# ---------------------------------------------------------------------------
# 10. Scalar predict (for HF splits)
# ---------------------------------------------------------------------------

def predict_scalar(p1, p2, ctx_extra):
    """Cascade walk for one (p1, p2). ctx_extra carries max3_sv if needed."""
    s = _features(p1)
    t = _features(p2)

    # Step 1
    if fires_X1(p1, p2):
        return "X1"
    if fires_X2(p1, p2):
        return "X2"
    if fires_X3(p1, p2):
        return "X3"

    # Step 2 separators
    if s["LP"] and not t["LP"]:
        return "LP"
    if s["RP"] and not t["RP"]:
        return "RP"
    if s["XOR"] and not t["XOR"]:
        return "XOR"

    # Step 3 forced behavior
    if f1_eq1_match(p1):
        return "F1_TRUE" if t["LP"] else "F1_FALSE"
    if f2_eq1_match(p1):
        return "F2_TRUE" if t["RP"] else "F2_FALSE"
    if f3_eq1_match(p1):
        ok = (leftmost(p2["lhs"]) == leftmost(p2["rhs"])
              and left_spine_depth(p2["lhs"]) == left_spine_depth(p2["rhs"]))
        return "F3_TRUE" if ok else "F3_FALSE"
    if f4_eq1_match(p1):
        ok = (rightmost(p2["lhs"]) == rightmost(p2["rhs"])
              and right_spine_depth(p2["lhs"]) == right_spine_depth(p2["rhs"]))
        return "F4_TRUE" if ok else "F4_FALSE"

    # Step 4 affine probes
    for probe_name, probe in PROBES.items():
        if equation_holds_under_probe(p1, probe) and not equation_holds_under_probe(p2, probe):
            return probe_name
    if c_probe_holds(p1) and not c_probe_holds(p2):
        return "C_PROBE"

    # Step 5 heuristics — only when Eq1 is bare (kind != N)
    if s["bare"]:
        if fires_H1(s, t): return "H1"
        if fires_H2(s, t): return "H2"
        if fires_H3(s, t): return "H3"
        if fires_H4(s, t): return "H4"
        if fires_H5(s, t): return "H5"
        if fires_H6(s, t): return "H6"

    # Step 6 hubs
    if hub_eq41_eq1_match(p1) and constant_magma_holds(p2):
        return "HUB_Eq41"
    if hub_eq46_eq1_match(p1) and constant_magma_holds(p2):
        return "HUB_Eq46"
    if hub_eq6_eq1_match(p1):
        # Idempotent test: use MAX_3 satisfaction.
        max3_sv = ctx_extra["max3_sv"]
        eq2_idx = ctx_extra.get("eq2_idx")
        if eq2_idx is not None and 0 <= eq2_idx < len(max3_sv):
            holds_max3 = bool(max3_sv[eq2_idx])
        else:
            # Fallback: structural — Eq2 holds when leaf sequences are equal
            # (idempotent semilattice satisfies many laws; conservative true).
            holds_max3 = (leaves(p2["lhs"]) == leaves(p2["rhs"]))
        if holds_max3:
            return "HUB_Eq6"

    return "DEFAULT_TRUE"


# ---------------------------------------------------------------------------
# 11. Per-split runner
# ---------------------------------------------------------------------------

def run_on_split(stem: str, ctx: ETPContext, feats: dict) -> dict:
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

        ctx_extra = {"max3_sv": feats["max3_sv"], "eq2_idx": j if 0 <= j < ctx.n_eq else None}
        rule = predict_scalar(p1, p2, ctx_extra)
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
# 12. Vectorized full-ETP runner
# ---------------------------------------------------------------------------

def build_fires_for_rule(ctx: ETPContext, feats: dict):
    n = ctx.n_eq

    # X2 mask: pair (i,j) where canon[i] == canon[j].
    canon_to_i: dict = {}
    for i, c in enumerate(feats["x2_canon"]):
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

    LP = feats["LP"]; RP = feats["RP"]; XOR = feats["XOR"]
    bare = feats["bare"]; kind = feats["kind"]; occ = feats["occ"]
    shortest_len = feats["shortest_len"]
    n_vars = feats["n_vars"]; dup = feats["dup"]

    def fires_for_rule(name: str) -> np.ndarray:
        if name == "X1":
            return np.broadcast_to(feats["x1_eq2"][None, :], (n, n)).copy()
        if name == "X2":
            return get_x2_mask()
        if name == "X3":
            return np.broadcast_to(feats["x3_eq1"][:, None], (n, n)).copy()
        if name == "LP":
            return LP[:, None] & ~LP[None, :]
        if name == "RP":
            return RP[:, None] & ~RP[None, :]
        if name == "XOR":
            return XOR[:, None] & ~XOR[None, :]
        if name == "F1_TRUE":
            return feats["f1_eq1"][:, None] & LP[None, :]
        if name == "F1_FALSE":
            return feats["f1_eq1"][:, None] & ~LP[None, :]
        if name == "F2_TRUE":
            return feats["f2_eq1"][:, None] & RP[None, :]
        if name == "F2_FALSE":
            return feats["f2_eq1"][:, None] & ~RP[None, :]
        if name == "F3_TRUE":
            return feats["f3_eq1"][:, None] & feats["f3_eq2"][None, :]
        if name == "F3_FALSE":
            return feats["f3_eq1"][:, None] & ~feats["f3_eq2"][None, :]
        if name == "F4_TRUE":
            return feats["f4_eq1"][:, None] & feats["f4_eq2"][None, :]
        if name == "F4_FALSE":
            return feats["f4_eq1"][:, None] & ~feats["f4_eq2"][None, :]
        if name in PROBES:
            h = feats["probe_holds"][name]
            return h[:, None] & ~h[None, :]
        if name == "C_PROBE":
            h = feats["probe_holds"]["C_PROBE"]
            return h[:, None] & ~h[None, :]
        if name == "H1":
            f1 = (kind == "M") & (n_vars >= 4)
            f2 = (kind == "X")
            return (bare[:, None] & f1[:, None]) & f2[None, :]
        if name == "H2":
            f1 = (kind == "L") & (shortest_len == 1) & (dup >= 3)
            f2 = (~bare) & (dup >= 3) & (n_vars <= 3)
            return (bare[:, None] & f1[:, None]) & f2[None, :]
        if name == "H3":
            f1 = (kind == "M") & (occ == 2) & (~RP)
            return np.broadcast_to((bare & f1)[:, None], (n, n)).copy()
        if name == "H4":
            f1 = (shortest_len == 1) & (occ == 3)
            return np.broadcast_to((bare & f1)[:, None], (n, n)).copy()
        if name == "H5":
            f1 = (kind == "M") & (shortest_len == 3) & (occ == 2)
            return np.broadcast_to((bare & f1)[:, None], (n, n)).copy()
        if name == "H6":
            f1 = (kind == "L")
            f2 = (occ == 2) & (n_vars == 4)
            return (bare[:, None] & f1[:, None]) & f2[None, :]
        if name == "HUB_Eq41":
            return feats["hub41_eq1"][:, None] & feats["const_holds"][None, :]
        if name == "HUB_Eq46":
            return feats["hub46_eq1"][:, None] & feats["const_holds"][None, :]
        if name == "HUB_Eq6":
            # Eq2 holds in idempotent magma — use MAX_3 satisfaction.
            return feats["hub6_eq1"][:, None] & feats["max3_sv"][None, :]
        if name == "DEFAULT_TRUE":
            return np.ones((n, n), dtype=bool)
        raise KeyError(f"Unknown rule {name!r}")

    return fires_for_rule


def run_full_etp_summary(ctx: ETPContext, feats: dict | None = None) -> dict:
    if feats is None:
        feats = _per_eq_features(ctx)
    fires_for_rule = build_fires_for_rule(ctx, feats)
    return run_full_etp(ctx, fires_for_rule, RULE_ORDER, TRUE_RULES,
                        progress_label="vt-ETP")


# ---------------------------------------------------------------------------
# 13. Driver
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
    out_dir = ROOT / "analysis" / "results" / "vt"
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
        s = run_on_split(stem, ctx, feats)
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

    md = ["# vt.txt programmatic checker — summary", ""]
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
