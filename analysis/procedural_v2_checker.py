"""Deterministic implementation of the procedural_v2 cheatsheet decision rules.

The cheatsheet at cheatsheets/procedural_v2.txt asks an LLM to compute purely
syntactic properties of two equations and then fire a fixed cascade of rules
D1..D10. None of that needs an LLM. This module computes the properties and
fires the rules in pure Python, then verifies its output against the 50-problem
run in results/20260407_012624_gpt-oss-120b_procedural_v2.json.

Run:  python3 analysis/procedural_v2_checker.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Reuse the existing parser
sys.path.insert(0, str(Path(__file__).parent))
from parse_equation import Var, Op, Node, parse_equation, _collect_vars  # noqa: E402


REPO = Path(__file__).resolve().parent.parent
RESULT_JSON = REPO / "results" / "20260407_012624_gpt-oss-120b_procedural_v2.json"
LLM_EFFECTIVE_ACC = 0.86


# ---------------------------------------------------------------------------
# Property helpers
# ---------------------------------------------------------------------------

def lhs_form(lhs: Node) -> str:
    """'bare' if LHS is one variable; 'product' if x ◇ y (two distinct vars);
    'deeper' otherwise."""
    if isinstance(lhs, Var):
        return "bare"
    if isinstance(lhs.left, Var) and isinstance(lhs.right, Var):
        return "product"
    return "deeper"


def leftmost_var(node: Node) -> str:
    while isinstance(node, Op):
        node = node.left
    return node.name


def rightmost_var(node: Node) -> str:
    while isinstance(node, Op):
        node = node.right
    return node.name


def spine(rhs: Node, lhs_var: str) -> str:
    """Walk from RHS root to the leftmost occurrence of `lhs_var`. At each Op,
    record 'L' if that occurrence sits in the left subtree, else 'R'.
    Returns 'none' (var not in rhs), 'L^n', 'R^n', or 'mixed'."""
    if lhs_var not in _collect_vars(rhs):
        return "none"
    path: list[str] = []
    node = rhs
    while isinstance(node, Op):
        if lhs_var in _collect_vars(node.left):
            path.append("L")
            node = node.left
        else:
            path.append("R")
            node = node.right
    # node is now the Var(lhs_var) — the leftmost occurrence
    if not path:
        # rhs was the bare var itself — treat as none-length spine; classify
        # as "L^0" style. Use "none" so D7/D8 (which need L^n with n>=1) don't
        # misfire on bare-var RHS.
        return "none"
    if all(p == "L" for p in path):
        return f"L^{len(path)}"
    if all(p == "R" for p in path):
        return f"R^{len(path)}"
    return "mixed"


def spine_length(spine_str: str) -> int | None:
    m = re.fullmatch(r"L\^(\d+)", spine_str)
    return int(m.group(1)) if m else None


def spine_length_right(spine_str: str) -> int | None:
    m = re.fullmatch(r"R\^(\d+)", spine_str)
    return int(m.group(1)) if m else None


def spine_kind(spine_str: str) -> str:
    """Return 'L', 'R', 'mixed', or 'none'."""
    if spine_str == "mixed":
        return "mixed"
    if spine_str == "none":
        return "none"
    if spine_str.startswith("L^"):
        return "L"
    if spine_str.startswith("R^"):
        return "R"
    return "none"


def has_squared_with_extra_free(t: Node, lhs_var: str) -> bool:
    """Spine.md Rule 4 collapse-trick syntactic indicator (loose v1 version).

    Some `(v ◇ v)` subterm exists and T contains a Var outside that subtree
    whose name is neither `v` nor `lhs_var`. Empirically near-anti-rule
    (~23% precision) — see has_squared_with_extra_free_strict.
    """
    squared: list[tuple[Node, str]] = []

    def find(n: Node) -> None:
        if isinstance(n, Op):
            if (
                isinstance(n.left, Var)
                and isinstance(n.right, Var)
                and n.left.name == n.right.name
            ):
                squared.append((n, n.left.name))
            find(n.left)
            find(n.right)

    find(t)
    if not squared:
        return False

    def has_extra_var(n: Node, skip: Node, v: str) -> bool:
        if n is skip:
            return False
        if isinstance(n, Var):
            return n.name != v and n.name != lhs_var
        return has_extra_var(n.left, skip, v) or has_extra_var(n.right, skip, v)

    for sq_node, v in squared:
        if has_extra_var(t, sq_node, v):
            return True
    return False


def has_squared_with_extra_free_stricter(t: Node, lhs_var: str) -> bool:
    """Strict + condition (c): the extra free variable w must occur somewhere
    in T at a position that is NOT inside any (u ◇ u) squared subterm."""
    # Collect all squared subterm nodes (any squared variable).
    squared_nodes: list[tuple[Node, str]] = []

    def find(n: Node) -> None:
        if isinstance(n, Op):
            if (
                isinstance(n.left, Var)
                and isinstance(n.right, Var)
                and n.left.name == n.right.name
            ):
                squared_nodes.append((n, n.left.name))
            find(n.left)
            find(n.right)

    find(t)
    if not squared_nodes:
        return False
    all_squared = {id(sq) for sq, _ in squared_nodes}

    # vars_outside_all_squares: Var occurrences in T that are NOT contained in
    # any squared subterm.
    def vars_unsquared(n: Node) -> set[str]:
        if id(n) in all_squared:
            return set()
        if isinstance(n, Var):
            return {n.name}
        return vars_unsquared(n.left) | vars_unsquared(n.right)

    unsquared = vars_unsquared(t)

    def vars_outside(n: Node, skip: Node) -> set[str]:
        if n is skip:
            return set()
        if isinstance(n, Var):
            return {n.name}
        return vars_outside(n.left, skip) | vars_outside(n.right, skip)

    for sq_node, v in squared_nodes:
        outside = vars_outside(t, sq_node)
        # (a) v appears nowhere else
        if v in outside:
            continue
        # (b) some real third var w ≠ v, w ≠ lhs_var
        # (c) AND that w appears somewhere outside any squared subterm
        for w in outside:
            if w != v and w != lhs_var and w in unsquared:
                return True
    return False


def has_squared_with_extra_free_strict(t: Node, lhs_var: str) -> bool:
    """Tighter collapse-trick indicator.

    Requires SOME (v ◇ v) subterm such that:
      1. v appears nowhere else in T (kills `(z ◇ z) ◇ z` and `y ◇ (y ◇ y)`),
      2. some other variable w ≠ v, w ≠ lhs_var occurs in T outside that
         (v ◇ v) subterm — i.e. there is a real "third" free variable to
         become half of the y ◇ w product after substitution.
    """
    squared: list[tuple[Node, str]] = []

    def find(n: Node) -> None:
        if isinstance(n, Op):
            if (
                isinstance(n.left, Var)
                and isinstance(n.right, Var)
                and n.left.name == n.right.name
            ):
                squared.append((n, n.left.name))
            find(n.left)
            find(n.right)

    find(t)
    if not squared:
        return False

    def vars_outside(n: Node, skip: Node) -> set[str]:
        if n is skip:
            return set()
        if isinstance(n, Var):
            return {n.name}
        return vars_outside(n.left, skip) | vars_outside(n.right, skip)

    for sq_node, v in squared:
        outside = vars_outside(t, sq_node)
        # condition 1: v appears nowhere else
        if v in outside:
            continue
        # condition 2: some real third var exists outside
        if any(w != v and w != lhs_var for w in outside):
            return True
    return False


def free_outer(eq: dict) -> str:
    """'right' if RHS root is (A ◇ z) and z is a Var appearing nowhere else
    in the equation; 'left' if (z ◇ A) similarly; else 'no'."""
    rhs = eq["rhs"]
    if not isinstance(rhs, Op):
        return "no"
    all_other_vars = _collect_vars(eq["lhs"])

    # right: rhs = (A ◇ z) with z a Var, z not in lhs and not in A
    if isinstance(rhs.right, Var):
        z = rhs.right.name
        a_vars = _collect_vars(rhs.left)
        if z not in a_vars and z not in all_other_vars:
            return "right"
    # left: rhs = (z ◇ A) similarly
    if isinstance(rhs.left, Var):
        z = rhs.left.name
        a_vars = _collect_vars(rhs.right)
        if z not in a_vars and z not in all_other_vars:
            return "left"
    return "no"


def props(eq: dict) -> dict:
    lhs, rhs = eq["lhs"], eq["rhs"]
    form = lhs_form(lhs)
    lhs_var = lhs.name if isinstance(lhs, Var) else None
    return {
        "lhs_form": form,
        "lhs_var": lhs_var,
        "x_in_rhs": (lhs_var in eq["rhs_vars"]) if lhs_var else None,
        "spine": spine(rhs, lhs_var) if lhs_var else "n/a",
        "leftmost": leftmost_var(rhs),
        "rightmost": rightmost_var(rhs),
        "free_outer": free_outer(eq),
    }


# ---------------------------------------------------------------------------
# Decision cascade
# ---------------------------------------------------------------------------

def compute_features(eq_raw: str) -> dict:
    """Parse + extract every field needed by `decide_features`. Call once
    per equation, then reuse across all pairings."""
    e = parse_equation(eq_raw)
    p = props(e)
    sk = spine_kind(p["spine"])
    n_l = spine_length(p["spine"])
    n_r = spine_length_right(p["spine"])
    # Collapse-trick indicator: only meaningful when Eq has form x = x ◇ T,
    # i.e. depth-1 left spine with bare LHS.
    collapse_indicator = False
    collapse_indicator_strict = False
    collapse_indicator_stricter = False
    if (
        p["lhs_form"] == "bare"
        and sk == "L"
        and n_l == 1
        and isinstance(e["rhs"], Op)
    ):
        collapse_indicator = has_squared_with_extra_free(
            e["rhs"].right, p["lhs_var"]
        )
        collapse_indicator_strict = has_squared_with_extra_free_strict(
            e["rhs"].right, p["lhs_var"]
        )
        collapse_indicator_stricter = has_squared_with_extra_free_stricter(
            e["rhs"].right, p["lhs_var"]
        )
    # Count occurrences of lhs_var in rhs
    def _count_var(node, name):
        if isinstance(node, Var):
            return 1 if node.name == name else 0
        return _count_var(node.left, name) + _count_var(node.right, name)
    x_occ_rhs = _count_var(e["rhs"], p["lhs_var"]) if p["lhs_var"] else None
    rhs_n_ops = e["n_ops_rhs"]
    # Maximum count of any non-lhs-var variable in rhs (used by D5e)
    if p["lhs_var"] is not None:
        other_vars = (e["lhs_vars"] | e["rhs_vars"]) - {p["lhs_var"]}
        max_other_count = max((_count_var(e["rhs"], v) for v in other_vars), default=0)
    else:
        max_other_count = 0
    return {
        "canonical": e["canonical"],
        "is_trivial": e["is_trivial"],
        "n_vars": e["n_vars"],
        "rhs_is_var": e["rhs_is_var"],
        "rhs_is_bare_var": isinstance(e["rhs"], Var),
        "rhs_var_name": e["rhs"].name if isinstance(e["rhs"], Var) else None,
        "lhs_var_set": e["lhs_vars"],
        "x_occ_rhs": x_occ_rhs,
        "rhs_n_ops": rhs_n_ops,
        "max_other_count": max_other_count,
        "lhs_form": p["lhs_form"],
        "lhs_var": p["lhs_var"],
        "x_in_rhs": p["x_in_rhs"],
        "spine": p["spine"],
        "spine_n": n_l,
        "spine_n_l": n_l,
        "spine_n_r": n_r,
        "spine_kind": sk,
        "leftmost": p["leftmost"],
        "rightmost": p["rightmost"],
        "free_outer": p["free_outer"],
        "collapse_indicator": collapse_indicator,
        "collapse_indicator_strict": collapse_indicator_strict,
        "collapse_indicator_stricter": collapse_indicator_stricter,
    }


def decide_features(f1: dict, f2: dict) -> tuple[str, bool]:
    """Fast path: fire D1..D10 directly on precomputed feature dicts."""
    if f2["is_trivial"]:
        return "D1", True
    if f1["canonical"] == f2["canonical"]:
        return "D2", True
    if (
        f1["lhs_form"] == "bare"
        and f1["rhs_is_var"]
        and f1["rhs_var_name"] != f1["lhs_var"]
    ):
        return "D3", True
    if f1["lhs_form"] == "bare" and f1["x_in_rhs"] is False:
        return "D4", True
    if (
        f1["lhs_form"] == "bare"
        and f1["free_outer"] == "right"
        and f1["leftmost"] != f1["lhs_var"]
    ):
        return "D5", True
    if (
        f1["lhs_form"] == "bare"
        and f1["free_outer"] == "left"
        and f1["rightmost"] != f1["lhs_var"]
    ):
        return "D5b", True
    if f1["is_trivial"] and not f2["is_trivial"]:
        return "D6", False
    # D7: Eq1 L^n, Eq2 leftmost ≠ x
    if (
        f1["spine_n_l"] is not None
        and f2["lhs_form"] == "bare"
        and f2["leftmost"] != f2["lhs_var"]
    ):
        return "D7", False
    # D7b: Eq1 L^n, Eq2 spine is R^m or mixed (left-zero magma).
    if (
        f1["spine_kind"] == "L"
        and f2["lhs_form"] == "bare"
        and f2["spine_kind"] in ("R", "mixed")
    ):
        return "D7b", False
    # D7c: Eq1 R^n, Eq2 rightmost ≠ x (right-zero magma).
    if (
        f1["spine_kind"] == "R"
        and f2["lhs_form"] == "bare"
        and f2["rightmost"] != f2["lhs_var"]
    ):
        return "D7c", False
    # D8: Eq1 L^n, Eq2 L^m, n ∤ m
    n, m = f1["spine_n_l"], f2["spine_n_l"]
    if n is not None and m is not None and (n == 0 or m % n != 0):
        return "D8", False
    # D8b: Eq1 R^n, Eq2 R^m, n ∤ m
    nr, mr = f1["spine_n_r"], f2["spine_n_r"]
    if nr is not None and mr is not None and (nr == 0 or mr % nr != 0):
        return "D8b", False
    # D9 (tightened): mixed spine + free outer + ≥3 vars
    if (
        f1["lhs_form"] == "bare"
        and f1["spine_kind"] == "mixed"
        and f1["free_outer"] != "no"
        and f1["n_vars"] >= 3
    ):
        return "D9", True
    # D9b: collapse trick (depth-1 left spine + squared subterm + extra free var)
    if (
        f1["collapse_indicator"]
        and f2["lhs_form"] == "bare"
        and f2["leftmost"] == f2["lhs_var"]
    ):
        return "D9b", True
    return "D10", False


def decide_features_v2(f1: dict, f2: dict) -> tuple[str, bool]:
    """v1 cascade with the speculative TRUE rules (D9, D9b) removed."""
    rule, ans = decide_features(f1, f2)
    if rule in ("D9", "D9b"):
        return "D10", False
    return rule, ans


def decide_features_v3(f1: dict, f2: dict) -> tuple[str, bool]:
    """Sound-only: v2 (which already drops D9/D9b). Same as v2 — kept as
    a named alias for clarity in the eval table."""
    return decide_features_v2(f1, f2)


def decide_features_v6(f1: dict, f2: dict) -> tuple[str, bool]:
    """v2 + tightest D9b (stricter predicate, conditions a+b+c) + old D9."""
    rule, ans = decide_features_v2(f1, f2)
    if rule == "D10":
        if (
            f1["collapse_indicator_stricter"]
            and f2["lhs_form"] == "bare"
            and f2["leftmost"] == f2["lhs_var"]
        ):
            return "D9bSS", True
        if f1["n_vars"] >= 4 and f1["lhs_form"] == "bare":
            return "D9old", True
    return rule, ans


def decide_features_v5(f1: dict, f2: dict) -> tuple[str, bool]:
    """v2 + tightened D9b (strict collapse predicate) + old D9 appended.

    Drops new D9 entirely (subsumed by D5/D5b) and uses
    `collapse_indicator_strict` instead of the loose `collapse_indicator`.
    """
    rule, ans = decide_features_v2(f1, f2)
    if rule == "D10":
        # D9b strict: depth-1 left spine, strict collapse predicate, Eq2
        # leftmost is its LHS-var.
        if (
            f1["collapse_indicator_strict"]
            and f2["lhs_form"] == "bare"
            and f2["leftmost"] == f2["lhs_var"]
        ):
            return "D9bS", True
        # Old D9: 4+ vars + bare LHS → TRUE
        if f1["n_vars"] >= 4 and f1["lhs_form"] == "bare":
            return "D9old", True
    return rule, ans


def decide_features_v4(f1: dict, f2: dict) -> tuple[str, bool]:
    """v2 plus the ORIGINAL D9 ('4+ vars + bare LHS → TRUE') appended at the
    end (just before D10)."""
    rule, ans = decide_features_v2(f1, f2)
    if rule == "D10" and f1["n_vars"] >= 4 and f1["lhs_form"] == "bare":
        return "D9old", True
    return rule, ans


def decide_features_v7(f1: dict, f2: dict) -> tuple[str, bool]:
    """v4 + D5c (sound mixed-spine collapse) inserted before D9old, and
    + D4dual (rhs is bare var with var not in lhs vars) → TRUE.

    D5c: lhs_form=bare AND n_vars>=4 AND spine_kind=mixed
         AND x appears exactly once in rhs → TRUE.
    D4d: rhs is single Var v AND v not in lhs vars → TRUE.
    """
    rule, ans = decide_features_v2(f1, f2)
    if rule != "D10":
        return rule, ans
    # D4d (D4-dual): symmetric rule for when rhs is bare var.
    if f1.get("rhs_is_bare_var") and f1.get("rhs_var_name") is not None and (
        f1["rhs_var_name"] not in f1.get("lhs_var_set", set())
    ):
        return "D4d", True
    # D5c: sound mixed-spine collapse
    if (
        f1["lhs_form"] == "bare"
        and f1["n_vars"] >= 4
        and f1["spine_kind"] == "mixed"
        and f1.get("x_occ_rhs") == 1
    ):
        return "D5c", True
    if f1["n_vars"] >= 4 and f1["lhs_form"] == "bare":
        return "D9old", True
    return "D10", False


def decide_features_v8(f1: dict, f2: dict) -> tuple[str, bool]:
    """v7 minus D9old (sound rules + D5c + D4d only)."""
    rule, ans = decide_features_v7(f1, f2)
    if rule == "D9old":
        return "D10", False
    return rule, ans


def decide_features_v13(f1: dict, f2: dict) -> tuple[str, bool]:
    """v12 + sound FALSE rules D10s-1 and D10s-2.

    D10s-1: Eq1 lhs not bare AND Eq2 lhs bare → FALSE.
    D10s-2: Eq1 lhs deeper AND Eq2 lhs product → FALSE.

    Both fire only when no upstream rule matches (i.e., would otherwise
    route to D9old or D10). They don't change cascade accuracy (D10
    already says FALSE) but upgrade ~5.4M pairs from heuristic to sound.
    """
    rule, ans = decide_features_v12(f1, f2)
    if rule != "D10" and rule != "D9old":
        return rule, ans
    if f1["lhs_form"] != "bare" and f2["lhs_form"] == "bare":
        return "D10s1", False
    if f1["lhs_form"] == "deeper" and f2["lhs_form"] == "product":
        return "D10s2", False
    return rule, ans


def decide_features_v12(f1: dict, f2: dict) -> tuple[str, bool]:
    """v10 + D5e (sound rule: nv=3 mixed-spine collapse, asymmetric vars).

    D5e: lhs_form=bare AND n_vars==3 AND spine_kind=mixed
         AND x_occ_rhs == 1 AND rhs_n_ops <= 4
         AND max non-x var count in rhs >= 3 → TRUE.

    The `rhs_n_ops <= 4` cap matters for OOD safety: without it the
    predicate fails on community-bench Eq1s with rhs_n_ops=5.
    """
    rule, ans = decide_features_v10(f1, f2)
    if rule != "D10" and rule != "D9old":
        return rule, ans
    if (
        f1["lhs_form"] == "bare"
        and f1["n_vars"] == 3
        and f1["spine_kind"] == "mixed"
        and f1.get("x_occ_rhs") == 1
        and f1.get("rhs_n_ops", 0) <= 4
        and f1.get("max_other_count", 0) >= 3
    ):
        return "D5e", True
    return rule, ans


def decide_features_v11(f1: dict, f2: dict) -> tuple[str, bool]:
    """v10 + flipped D9old sub-buckets.

    For Eq1 with spine_kind in ('L','R') reaching D9old, predict FALSE
    instead of TRUE — empirically this sub-bucket is only ~14% TRUE,
    so flipping gives ~86% precision on ~1.2M pairs.
    """
    rule, ans = decide_features_v10(f1, f2)
    if rule == "D9old" and f1["spine_kind"] in ("L", "R"):
        return "D9old_flip", False
    return rule, ans


def decide_features_v10(f1: dict, f2: dict) -> tuple[str, bool]:
    """v7 + D5d (sound rule for nv=3 mixed-spine collapse with shallow rhs).

    D5d: lhs_form=bare AND n_vars==3 AND spine_kind=mixed
         AND x_occ_rhs == 1 AND rhs_n_ops <= 3 → TRUE.
    """
    rule, ans = decide_features_v7(f1, f2)
    if rule != "D10" and rule != "D9old":
        return rule, ans
    # D5d (sound) — try BEFORE D9old falls back
    if (
        f1["lhs_form"] == "bare"
        and f1["n_vars"] == 3
        and f1["spine_kind"] == "mixed"
        and f1.get("x_occ_rhs") == 1
        and f1.get("rhs_n_ops", 0) <= 3
    ):
        return "D5d", True
    return rule, ans


def decide_features_v9(f1: dict, f2: dict) -> tuple[str, bool]:
    """v7 with D9old restricted to spine_kind == 'mixed' only.

    The L-spine and R-spine sub-buckets of D9old have ~12-14% precision and
    are net-harmful; the mixed sub-bucket (after D5c siphons off the sound
    1x case) is ~53% — still imperfect but the only sub-bucket worth keeping
    on curated benchmarks.
    """
    rule, ans = decide_features_v7(f1, f2)
    if rule == "D9old" and f1["spine_kind"] != "mixed":
        return "D10", False
    return rule, ans


def decide_features_v0(f1: dict, f2: dict) -> tuple[str, bool]:
    """Original D1..D10 cascade, kept for before/after comparison."""
    if f2["is_trivial"]:
        return "D1", True
    if f1["canonical"] == f2["canonical"]:
        return "D2", True
    if (
        f1["lhs_form"] == "bare"
        and f1["rhs_is_var"]
        and f1["rhs_var_name"] != f1["lhs_var"]
    ):
        return "D3", True
    if f1["lhs_form"] == "bare" and f1["x_in_rhs"] is False:
        return "D4", True
    if (
        f1["lhs_form"] == "bare"
        and f1["free_outer"] == "right"
        and f1["leftmost"] != f1["lhs_var"]
    ):
        return "D5", True
    if (
        f1["lhs_form"] == "bare"
        and f1["free_outer"] == "left"
        and f1["rightmost"] != f1["lhs_var"]
    ):
        return "D5b", True
    if f1["is_trivial"] and not f2["is_trivial"]:
        return "D6", False
    if (
        f1["spine_n"] is not None
        and f2["lhs_form"] == "bare"
        and f2["leftmost"] != f2["lhs_var"]
    ):
        return "D7", False
    n, m = f1["spine_n"], f2["spine_n"]
    if n is not None and m is not None and (n == 0 or m % n != 0):
        return "D8", False
    if f1["n_vars"] >= 4 and f1["lhs_form"] == "bare":
        return "D9", True
    return "D10", False


def decide(eq1_raw: str, eq2_raw: str) -> tuple[str, bool]:
    return decide_features(compute_features(eq1_raw), compute_features(eq2_raw))


def _decide_legacy(eq1_raw: str, eq2_raw: str) -> tuple[str, bool]:
    e1 = parse_equation(eq1_raw)
    e2 = parse_equation(eq2_raw)
    p1 = props(e1)
    p2 = props(e2)

    # D1: Eq2 is "x = x"
    if e2["is_trivial"]:
        return "D1", True
    # D2: Eq1 ≡ Eq2 up to renaming
    if e1["canonical"] == e2["canonical"]:
        return "D2", True
    # D3: Eq1 LHS bare AND Eq1 RHS is one variable ≠ LHS-var
    if p1["lhs_form"] == "bare" and isinstance(e1["rhs"], Var) and e1["rhs"].name != p1["lhs_var"]:
        return "D3", True
    # D4: Eq1 LHS bare AND Eq1 X_IN_RHS=no
    if p1["lhs_form"] == "bare" and p1["x_in_rhs"] is False:
        return "D4", True
    # D5: Eq1 FREE_OUTER=right AND Eq1 LEFTMOST ≠ Eq1 LHS-var
    # (only meaningful when LHS is a single variable)
    if p1["lhs_form"] == "bare" and p1["free_outer"] == "right" and p1["leftmost"] != p1["lhs_var"]:
        return "D5", True
    # D5b: Eq1 FREE_OUTER=left AND Eq1 RIGHTMOST ≠ Eq1 LHS-var
    if p1["lhs_form"] == "bare" and p1["free_outer"] == "left" and p1["rightmost"] != p1["lhs_var"]:
        return "D5b", True
    # D6: Eq1 trivial and Eq2 not
    if e1["is_trivial"] and not e2["is_trivial"]:
        return "D6", False
    # D7: Eq1 SPINE=L^n AND Eq2 LHS bare AND Eq2 LEFTMOST ≠ Eq2 LHS-var
    if (
        spine_length(p1["spine"]) is not None
        and p2["lhs_form"] == "bare"
        and p2["leftmost"] != p2["lhs_var"]
    ):
        return "D7", False
    # D8: Eq1 SPINE=L^n AND Eq2 SPINE=L^m AND n does not divide m
    n = spine_length(p1["spine"])
    m = spine_length(p2["spine"])
    if n is not None and m is not None and (n == 0 or m % n != 0):
        return "D8", False
    # D9: Eq1 has 4+ distinct vars AND Eq1 LHS bare
    if e1["n_vars"] >= 4 and p1["lhs_form"] == "bare":
        return "D9", True
    # D10: default
    return "D10", False


# ---------------------------------------------------------------------------
# Verification driver
# ---------------------------------------------------------------------------

_RULE_RE = re.compile(r"Rule fired:\s*(D\d+b?)", re.IGNORECASE)
_ANSWER_RE = re.compile(r"Answered\s+(TRUE|FALSE)", re.IGNORECASE)


def parse_llm_trace(raw: str | None) -> tuple[str | None, bool | None]:
    if not raw:
        return None, None
    rm = _RULE_RE.search(raw)
    am = _ANSWER_RE.search(raw)
    rule = rm.group(1) if rm else None
    if rule:
        rule = rule[0].upper() + rule[1:].lower()  # D5b stays D5b
    ans: bool | None
    if am:
        ans = am.group(1).upper() == "TRUE"
    else:
        ans = None
    return rule, ans


def main() -> int:
    data = json.loads(RESULT_JSON.read_text())
    results = data["results"]
    print(f"Loaded {len(results)} problems from {RESULT_JSON.name}\n")

    det_rule_counts: Counter[str] = Counter()
    correct = 0
    parse_errors = 0
    rule_agree = 0
    rule_compared = 0
    answer_agree = 0
    answer_compared = 0
    mismatches: list[tuple[str, str, str | None, bool, bool | None, bool]] = []

    v0_correct = 0
    flips: list[tuple[str, str, bool, str, bool, bool]] = []
    for r in results:
        pid = r["problem_id"]
        eq1, eq2 = r["equation1"], r["equation2"]
        gold = r["gold_answer"]
        try:
            f1 = compute_features(eq1)
            f2 = compute_features(eq2)
            det_rule, det_ans = decide_features(f1, f2)
            v0_rule, v0_ans = decide_features_v0(f1, f2)
        except Exception as e:
            parse_errors += 1
            print(f"  PARSE ERROR {pid}: {e}")
            continue
        det_rule_counts[det_rule] += 1
        if det_ans == gold:
            correct += 1
        if v0_ans == gold:
            v0_correct += 1
        if v0_ans != det_ans:
            flips.append((pid, v0_rule, v0_ans, det_rule, det_ans, gold))

        llm_rule, llm_ans = parse_llm_trace(r.get("raw_response"))
        if llm_rule is not None:
            rule_compared += 1
            if llm_rule == det_rule:
                rule_agree += 1
        if llm_ans is not None:
            answer_compared += 1
            if llm_ans == det_ans:
                answer_agree += 1

        if llm_rule is not None and llm_rule != det_rule:
            mismatches.append((pid, det_rule, llm_rule, det_ans, llm_ans, gold))

    n = len(results)
    acc = correct / n
    print("=" * 70)
    print(f"Deterministic accuracy vs gold (v1): {correct}/{n} = {acc:.3f}")
    print(f"Deterministic accuracy vs gold (v0): {v0_correct}/{n} = {v0_correct/n:.3f}")
    if flips:
        print(f"\nFlips (v0 → v1) [{len(flips)}]:")
        print(f"  {'pid':<14} {'v0_rule':<7} {'v0':<6} {'v1_rule':<7} {'v1':<6} {'gold':<5}")
        for pid, vr, va, dr, da, g in flips:
            print(f"  {pid:<14} {vr:<7} {str(va):<6} {dr:<7} {str(da):<6} {str(g):<5}")
        print()
    print(f"LLM effective accuracy (reference):           {LLM_EFFECTIVE_ACC:.3f}")
    print(f"Parse errors:                                  {parse_errors}")
    print()
    print("Deterministic rule firing distribution:")
    for rule in sorted(det_rule_counts):
        print(f"  {rule:5s}: {det_rule_counts[rule]}")
    print()
    print(f"Rule agreement with LLM trace:   {rule_agree}/{rule_compared}")
    print(f"Answer agreement with LLM trace: {answer_agree}/{answer_compared}")
    print()
    if mismatches:
        print(f"Rule mismatches ({len(mismatches)}):")
        print(f"  {'pid':<14} {'det':<5} {'llm':<5} {'det_ans':<8} {'llm_ans':<8} {'gold':<5}")
        for pid, dr, lr, da, la, g in mismatches:
            print(f"  {pid:<14} {dr:<5} {lr or '?':<5} {str(da):<8} {str(la):<8} {str(g):<5}")
    else:
        print("No rule mismatches with LLM trace.")

    if acc < LLM_EFFECTIVE_ACC:
        print(f"\nFAIL: deterministic accuracy {acc:.3f} < LLM {LLM_EFFECTIVE_ACC:.3f}")
        return 1
    print(f"\nOK: deterministic accuracy {acc:.3f} >= LLM {LLM_EFFECTIVE_ACC:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
