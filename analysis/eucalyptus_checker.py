"""Programmatic ("ceiling") checker for the eucalyptus.txt cheatsheet.

eucalyptus.txt cascade implemented:

  Fast-path TRUE rules:
      X1_tautology_eq2     - Eq2 LHS == Eq2 RHS structurally
      X2_singleton_collapse - Eq1 has lone-variable side absent from other

  Tier 1 (algebraic) FALSE witnesses:
      L_constzero  - constant-zero magma satisfies Eq1, refutes Eq2
      LP           - left projection
      RP           - right projection

  Tier 2 (boolean) FALSE witnesses:
      T2_AND, T2_OR, T2_XOR, T2_XNOR, T2_LEFT_NOT, T2_RIGHT_NOT,
      T2_NAND, T2_NOR, T2_IMPLY, T2_NIMPLY, T2_C_IMPLY, T2_C_NIMPLY,
      T2_CONSTANT_1

  Tier 3 (modular Z3) FALSE witnesses:
      T3_Z3_ADD, T3_Z3_NEG, T3_Z3_SUB

  Hard countermodels directory (Eq1 exact-string match):
      HARD_001 ... HARD_NNN

  Default (Classification step, base rate FALSE):
      CLASSIFY_DEFAULT_FALSE

TRUE_RULES = {X1_tautology_eq2, X2_singleton_collapse}.
Everything else commits FALSE.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))

from parse_equation import Op, Var, parse_equation, canonical_form  # noqa: E402

from _common import (  # noqa: E402
    ETPContext,
    MAGMA_LIB,
    SPLITS,
    affine_table,
    get_sat_vector,
    load_etp_context,
    load_split,
    print_summary,
    run_full_etp,
    save_summary,
    summarize,
)


CHEATSHEET_PATH = ROOT / "cheatsheets" / "eucalyptus.txt"


# ---------------------------------------------------------------------------
# 1. Tier 2 / Tier 3 magma tables (register any not already in MAGMA_LIB)
# ---------------------------------------------------------------------------

def _t(rows):
    return np.array(rows, dtype=np.int8)


# Tier 2 boolean magmas, indexed by behavior on (0*0, 0*1, 1*0, 1*1)
T2_TABLES = {
    "T2_AND":         _t([[0, 0], [0, 1]]),  # 0,0,0,1
    "T2_OR":          _t([[0, 1], [1, 1]]),  # 0,1,1,1
    "T2_XOR":         _t([[0, 1], [1, 0]]),  # 0,1,1,0
    "T2_XNOR":        _t([[1, 0], [0, 1]]),  # 1,0,0,1
    "T2_LEFT_NOT":    _t([[1, 1], [0, 0]]),  # 1,1,0,0  (NOT a)
    "T2_RIGHT_NOT":   _t([[1, 0], [1, 0]]),  # 1,0,1,0  (NOT b)
    "T2_NAND":        _t([[1, 1], [1, 0]]),  # 1,1,1,0
    "T2_NOR":         _t([[1, 0], [0, 0]]),  # 1,0,0,0
    "T2_IMPLY":       _t([[1, 1], [0, 1]]),  # 1,1,0,1   (a -> b)
    "T2_NIMPLY":      _t([[0, 0], [1, 0]]),  # 0,0,1,0   (a NIMPLY b)
    "T2_C_IMPLY":     _t([[1, 0], [1, 1]]),  # 1,0,1,1   (b -> a)
    "T2_C_NIMPLY":    _t([[0, 1], [0, 0]]),  # 0,1,0,0   (b NIMPLY a)
    "T2_CONSTANT_1":  _t([[1, 1], [1, 1]]),  # 1,1,1,1
}

# Tier 3 modular magmas on Z_3
T3_TABLES = {
    "T3_Z3_ADD": affine_table(1, 1, 3),    # (a+b) mod 3
    "T3_Z3_NEG": affine_table(-1, -1, 3),  # (-a-b) mod 3
    "T3_Z3_SUB": affine_table(1, -1, 3),   # (a-b) mod 3
}

# Tier 1 magmas — already in MAGMA_LIB:
#   L3_constzero3 (use this for "Constant" - works any size, eucalyptus example
#                  "x = y*z -> x = 0" requires order >=2; order 3 is safe.)
#   L1_leftproj3, L2_rightproj3
TIER1_NAMES = {
    "L_constzero": "L3_constzero3",
    "LP":          "L1_leftproj3",
    "RP":          "L2_rightproj3",
}

# Register Tier 2/3 in MAGMA_LIB
for _n, _tbl in T2_TABLES.items():
    MAGMA_LIB.setdefault(_n, _tbl)
for _n, _tbl in T3_TABLES.items():
    MAGMA_LIB.setdefault(_n, _tbl)


# ---------------------------------------------------------------------------
# 2. Hard countermodels directory — parse cheatsheet
# ---------------------------------------------------------------------------

_HARD_BLOCK_RE = re.compile(
    r"\*\*Size\s+(\d+)\*\*\s*Table\s*`(\[\[[^`]+\]\])`\s*\n→\s*(.+?)(?=\n\*\*Size|\n##|\Z)",
    re.DOTALL,
)


def parse_hard_countermodels(text: str) -> list[dict]:
    """Parse hard-countermodel blocks from eucalyptus.txt text.

    Returns: list of dicts {size, table (np.ndarray), eq1_strings (list[str])}.
    """
    blocks = []
    for m in _HARD_BLOCK_RE.finditer(text):
        size = int(m.group(1))
        table_lit = m.group(2)
        eq_block = m.group(3).strip()
        # Parse table literal (it's a JSON-like nested int list).
        try:
            table_rows = json.loads(table_lit)
        except json.JSONDecodeError:
            continue
        table = np.array(table_rows, dtype=np.int8)
        # Equations are separated by ';' on a single (logical) line.
        eq_strs = [s.strip() for s in eq_block.split(";") if s.strip()]
        blocks.append({"size": size, "table": table, "eq1_strings": eq_strs})
    return blocks


def build_eq_canon_index(parsed: list[dict]) -> dict[str, int]:
    """Map canonical-equation-string -> equation index (0-based)."""
    idx = {}
    for i, p in enumerate(parsed):
        idx.setdefault(p["canonical"], i)
    return idx


def resolve_hard_eq_ids(blocks: list[dict], canon_idx: dict[str, int]
                        ) -> list[dict]:
    """For each hard block, parse each Eq1 string into canonical form,
    resolve to equation IDs.  Returns per-block dicts:
        {table, size, eq1_ids: [int, ...], unmatched: [str, ...]}
    """
    out = []
    for b in blocks:
        ids = []
        unmatched = []
        for s in b["eq1_strings"]:
            try:
                p = parse_equation(s)
                cf = canonical_form(p["lhs"], p["rhs"])
                if cf in canon_idx:
                    ids.append(canon_idx[cf])
                else:
                    unmatched.append(s)
            except Exception:  # parse error
                unmatched.append(s)
        out.append({"table": b["table"], "size": b["size"],
                    "eq1_ids": sorted(set(ids)),
                    "unmatched": unmatched})
    return out


# ---------------------------------------------------------------------------
# 3. Per-equation predicate flags for fast paths
# ---------------------------------------------------------------------------

def _is_var(n):
    return isinstance(n, Var)


def _all_vars(node):
    if isinstance(node, Var):
        return {node.name}
    return _all_vars(node.left) | _all_vars(node.right)


def _tree_eq(a, b):
    if isinstance(a, Var) and isinstance(b, Var):
        return a.name == b.name
    if isinstance(a, Op) and isinstance(b, Op):
        return _tree_eq(a.left, b.left) and _tree_eq(a.right, b.right)
    return False


def x1_flag_eq2(p):
    """Eq2 sides are structurally identical."""
    return _tree_eq(p["lhs"], p["rhs"])


def x2_flag_eq1(p):
    """Eq1 has a lone-variable side absent from the other side."""
    L, R = p["lhs"], p["rhs"]
    if isinstance(L, Var) and L.name not in _all_vars(R):
        return True
    if isinstance(R, Var) and R.name not in _all_vars(L):
        return True
    return False


# ---------------------------------------------------------------------------
# 4. Build the rule-order list (dynamic — depends on hard block count)
# ---------------------------------------------------------------------------

TIER1_RULES = ["L_constzero", "LP", "RP"]
TIER2_RULES = list(T2_TABLES.keys())
TIER3_RULES = list(T3_TABLES.keys())

FAST_PATH_RULES = ["X1_tautology_eq2", "X2_singleton_collapse"]
DEFAULT_RULE = "CLASSIFY_DEFAULT_FALSE"

TRUE_RULES = {"X1_tautology_eq2", "X2_singleton_collapse"}


def make_rule_order(n_hard_blocks: int) -> list[str]:
    """Cascade order: fast-path TRUE → Tier 1 FALSE → Tier 2 FALSE
    → Tier 3 FALSE → HARD_xxx FALSE → CLASSIFY_DEFAULT_FALSE.

    Per the cheatsheet, "Check Hard Countermodels FIRST" — but a HARD rule
    only fires on the listed Eq1 set, so placing it before/after Tier 1-3 has
    no effect on the verdict (HARD never fires where Tier rules already
    handle the case). For attribution clarity we place HARD after Tiers, so
    Tiers' broad coverage is reported first; HARD then catches anything
    Tiers missed.
    """
    order = list(FAST_PATH_RULES)
    order += TIER1_RULES
    order += TIER2_RULES
    order += TIER3_RULES
    order += [f"HARD_{i:03d}" for i in range(n_hard_blocks)]
    order.append(DEFAULT_RULE)
    return order


# ---------------------------------------------------------------------------
# 5. Per-equation features and rule fire masks
# ---------------------------------------------------------------------------

def precompute_features(ctx: ETPContext, hard_resolved: list[dict]):
    """Build vectorized features:

      - x1_eq2[j]: bool[n_eq] (whether equation j is a tautology)
      - x2_eq1[i]: bool[n_eq]
      - sat[r][i]: bool[n_eq] = does magma `r` satisfy equation i (universally)
      - hard_eq1_set[h]: set of equation indices for HARD_h
    """
    n = ctx.n_eq
    parsed = ctx.parsed

    x1_eq2 = np.array([x1_flag_eq2(p) for p in parsed], dtype=bool)
    x2_eq1 = np.array([x2_flag_eq1(p) for p in parsed], dtype=bool)

    # Per-magma satisfaction vector (uses ctx.sat_cache via get_sat_vector)
    magma_sat = {}
    for rule, magma_name in [(r, TIER1_NAMES[r]) for r in TIER1_RULES]:
        magma_sat[rule] = get_sat_vector(ctx, magma_name, MAGMA_LIB[magma_name])
    for r in TIER2_RULES:
        magma_sat[r] = get_sat_vector(ctx, r, MAGMA_LIB[r])
    for r in TIER3_RULES:
        magma_sat[r] = get_sat_vector(ctx, r, MAGMA_LIB[r])

    # Hard countermodel blocks: per-block sat vector & Eq1-id restriction
    hard_features = []
    for h, hb in enumerate(hard_resolved):
        size = hb["size"]
        table = hb["table"]
        rname = f"HARD_{h:03d}"
        sv = get_sat_vector(ctx, rname, table)
        ids = np.array(hb["eq1_ids"], dtype=np.int64)
        mask_eq1 = np.zeros(n, dtype=bool)
        if ids.size:
            mask_eq1[ids] = True
        hard_features.append({
            "rule_name": rname,
            "sat": sv,
            "eq1_mask": mask_eq1,
            "size": size,
            "n_listed": int(ids.size),
            "unmatched": hb["unmatched"],
        })

    return {
        "x1_eq2": x1_eq2,
        "x2_eq1": x2_eq1,
        "magma_sat": magma_sat,
        "hard": hard_features,
    }


def build_fires_for_rule(ctx: ETPContext, feats: dict, rule_order: list[str]):
    """Closure: rule_name -> bool[n_eq, n_eq] candidate fire mask."""
    n = ctx.n_eq

    def fires(name: str) -> np.ndarray:
        if name == "X1_tautology_eq2":
            return np.broadcast_to(feats["x1_eq2"][None, :], (n, n)).copy()
        if name == "X2_singleton_collapse":
            return np.broadcast_to(feats["x2_eq1"][:, None], (n, n)).copy()
        if name in feats["magma_sat"]:
            sv = feats["magma_sat"][name]
            return sv[:, None] & ~sv[None, :]
        if name.startswith("HARD_"):
            for h in feats["hard"]:
                if h["rule_name"] == name:
                    sv = h["sat"]
                    em = h["eq1_mask"]
                    # Only fire when i is in the listed set AND magma is a
                    # FALSE witness for (i,j).
                    return (em[:, None]
                            & sv[:, None]
                            & ~sv[None, :])
            raise KeyError(f"HARD rule {name!r} not registered")
        if name == DEFAULT_RULE:
            return np.ones((n, n), dtype=bool)
        raise KeyError(f"Unknown rule {name!r}")

    return fires


# ---------------------------------------------------------------------------
# 6. Scalar predict for split rows
# ---------------------------------------------------------------------------

def predict_scalar(i: int, j: int, feats: dict, rule_order: list[str]) -> str:
    """Return the rule that fires at (i, j) under cascade order."""
    if feats["x1_eq2"][j]:
        return "X1_tautology_eq2"
    if feats["x2_eq1"][i]:
        return "X2_singleton_collapse"
    for r in TIER1_RULES + TIER2_RULES + TIER3_RULES:
        sv = feats["magma_sat"][r]
        if sv[i] and not sv[j]:
            return r
    for h in feats["hard"]:
        if h["eq1_mask"][i] and h["sat"][i] and not h["sat"][j]:
            return h["rule_name"]
    return DEFAULT_RULE


# For out-of-universe equations (evaluation_order5 has eq IDs > 4694)
# we need to compute features on-the-fly.
def predict_scalar_ad_hoc(p1: dict, p2: dict, feats: dict, ctx: ETPContext,
                          parsed_eq_str: dict[str, int]) -> str:
    """Same cascade for a (p1, p2) where parse-tree dicts are given but
    indices may be out-of-universe.  The ad-hoc magma sat checks are computed
    by `magma_counterexamples.satisfaction_vector` at runtime."""
    from magma_counterexamples import compile_equation, satisfaction_vector
    if x1_flag_eq2(p2):
        return "X1_tautology_eq2"
    if x2_flag_eq1(p1):
        return "X2_singleton_collapse"
    compiled1 = compile_equation(p1["lhs"], p1["rhs"])
    compiled2 = compile_equation(p2["lhs"], p2["rhs"])

    def sat_pair(table):
        sv = satisfaction_vector(table, [compiled1, compiled2])
        return bool(sv[0]), bool(sv[1])

    for r, mn in [(r, TIER1_NAMES[r]) for r in TIER1_RULES]:
        s1, s2 = sat_pair(MAGMA_LIB[mn])
        if s1 and not s2:
            return r
    for r in TIER2_RULES + TIER3_RULES:
        s1, s2 = sat_pair(MAGMA_LIB[r])
        if s1 and not s2:
            return r
    # Hard countermodels: only if Eq1 string canonicalizes into the listed set.
    cf1 = canonical_form(p1["lhs"], p1["rhs"])
    cf1_eq_idx = parsed_eq_str.get(cf1)
    if cf1_eq_idx is not None:
        for h in feats["hard"]:
            if h["eq1_mask"][cf1_eq_idx]:
                s1, s2 = sat_pair(MAGMA_LIB[h["rule_name"]])
                if s1 and not s2:
                    return h["rule_name"]
    return DEFAULT_RULE


# ---------------------------------------------------------------------------
# 7. Per-split runner
# ---------------------------------------------------------------------------

def run_on_split(stem: str, ctx: ETPContext, feats: dict,
                 rule_order: list[str],
                 canon_idx: dict[str, int]) -> dict:
    problems = load_split(stem)
    rows = []
    for p in problems:
        i_id = p["eq1_id"]
        j_id = p["eq2_id"]
        i = i_id - 1
        j = j_id - 1
        if 0 <= i < ctx.n_eq and 0 <= j < ctx.n_eq:
            rule = predict_scalar(i, j, feats, rule_order)
        else:
            p1 = (ctx.parsed[i] if 0 <= i < ctx.n_eq
                  else parse_equation(p["equation1"]))
            p2 = (ctx.parsed[j] if 0 <= j < ctx.n_eq
                  else parse_equation(p["equation2"]))
            rule = predict_scalar_ad_hoc(p1, p2, feats, ctx, canon_idx)
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
    return summarize(rows, rule_order, TRUE_RULES, dataset_name=stem)


# ---------------------------------------------------------------------------
# 8. Driver
# ---------------------------------------------------------------------------

def _md_table_for_split(s: dict) -> str:
    n, nc = s["n"], s["n_correct"]
    cf = s["confusion"]
    out = [f"### `{s['dataset']}`  —  accuracy {nc}/{n} = {nc/n*100:.2f}%"]
    out.append("")
    out.append(f"Confusion: TP={cf['tp']}, FP={cf['fp']}, "
               f"TN={cf['tn']}, FN={cf['fn']}")
    out.append("")
    out.append("| rule | verdict | fires | correct | wrong | precision |")
    out.append("|------|---------|------:|--------:|------:|----------:|")
    for rule in s["rule_order"]:
        bs = s["by_rule"].get(rule,
                              {"n": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0})
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
    out_dir = ROOT / "analysis" / "results" / "eucalyptus"
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.stderr.write("Loading ETP context (parse + compile + gold)...\n")
    t0 = time.time()
    ctx = load_etp_context(load_gold=True)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s "
                     f"(n_eq={ctx.n_eq}, gold loaded={ctx.gold is not None})\n")

    canon_idx = build_eq_canon_index(ctx.parsed)

    sys.stderr.write("Parsing hard countermodels from cheatsheet...\n")
    text = CHEATSHEET_PATH.read_text()
    hard_blocks = parse_hard_countermodels(text)
    hard_resolved = resolve_hard_eq_ids(hard_blocks, canon_idx)
    n_hard = len(hard_resolved)
    n_listed_total = sum(len(h["eq1_ids"]) for h in hard_resolved)
    n_unmatched = sum(len(h["unmatched"]) for h in hard_resolved)
    sys.stderr.write(f"  parsed {n_hard} hard blocks; "
                     f"{n_listed_total} Eq1 IDs resolved; "
                     f"{n_unmatched} Eq1 strings unmatched.\n")
    if n_unmatched:
        for h in hard_resolved:
            for s in h["unmatched"]:
                sys.stderr.write(f"    [warn] unmatched Eq1: {s!r}\n")

    rule_order = make_rule_order(n_hard)

    sys.stderr.write("Computing per-equation features (sat vectors)...\n")
    t0 = time.time()
    feats = precompute_features(ctx, hard_resolved)
    sys.stderr.write(f"  done in {time.time()-t0:.1f}s\n")

    summaries = {}

    sys.stderr.write("\n=== Splits ===\n")
    for stem in SPLITS:
        sys.stderr.write(f"  running {stem}...\n")
        s = run_on_split(stem, ctx, feats, rule_order, canon_idx)
        save_summary(s, out_dir / f"{stem}.json", drop_rows=False)
        summaries[stem] = {k: v for k, v in s.items() if k != "rows"}
        print_summary(s)

    sys.stderr.write("\n=== Full ETP (4694x4694 = 22M pairs) ===\n")
    t0 = time.time()
    fires_for_rule = build_fires_for_rule(ctx, feats, rule_order)
    full = run_full_etp(ctx, fires_for_rule, rule_order, TRUE_RULES,
                        progress_label="eucalyptus-ETP")
    sys.stderr.write(f"  full ETP done in {time.time()-t0:.1f}s\n")
    save_summary(full, out_dir / "full_etp.json", drop_rows=True)
    if not full.get("skipped"):
        summaries["full_etp"] = full
    print_summary(full)

    combined = {
        "splits": {stem: summaries[stem] for stem in SPLITS},
        "full_etp": full,
        "hard_countermodels": {
            "n_blocks": n_hard,
            "n_eq1_ids_resolved": n_listed_total,
            "n_eq1_strings_unmatched": n_unmatched,
        },
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(combined, f, indent=2)

    md = ["# eucalyptus.txt programmatic checker — summary", ""]
    md.append("## Overall accuracy")
    md.append("")
    md.append("| dataset | n | accuracy |")
    md.append("|---------|--:|---------:|")
    for stem in SPLITS:
        s = summaries[stem]
        md.append(f"| {stem} | {s['n']} | "
                  f"{s['n_correct']}/{s['n']} = "
                  f"{s['n_correct']/s['n']*100:.2f}% |")
    md.append(f"| full_etp | {full['n']} | "
              f"{full['n_correct']}/{full['n']} = "
              f"{full['n_correct']/full['n']*100:.4f}% |")
    md.append("")
    md.append(f"Hard countermodels parsed: {n_hard} blocks, "
              f"{n_listed_total} Eq1 IDs resolved "
              f"({n_unmatched} strings unmatched).")
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
