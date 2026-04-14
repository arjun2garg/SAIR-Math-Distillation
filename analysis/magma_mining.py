"""Mine decision rules from small-magma counterexamples.

Strategy (inspired by other_cheatsheets/three_element_focus.txt):
  For a small bank of finite magmas M_1..M_k, compute per equation E a bitmask
  signature S(E) of magmas in which E holds. Then for any pair (Eq1, Eq2):
      Eq1 implies Eq2  =>  S(Eq1) is a subset of S(Eq2)
  Equivalently: if there exists a magma in S(Eq1) \\ S(Eq2), then Eq1 ⇏ Eq2
  (FALSE) — that magma is an explicit counterexample.

This gives a SOUND FALSE rule (subject to magma evaluation correctness):
no false negatives (we never wrongly call something FALSE), only missed FALSE
predictions for pairs whose counterexamples lie outside the bank.

Outputs:
  data/magma_signatures.npy   uint64 array, one per equation, bitmask over bank
  data/magma_bank.json        list of magma definitions
  analysis/magma_results.txt  precision/coverage on ETP and on validation subsets
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Callable

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.parse_equation import Op, Var, parse_all_equations  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


# ---------------------------------------------------------------------------
# Equation -> compiled checker
# ---------------------------------------------------------------------------

def compile_equation(eq: dict) -> Callable[[list[list[int]], int], bool]:
    """Build a fast Python function that returns True iff the equation holds
    in the magma given by table M (size n).

    Table is a flat list of length n*n, indexed M[a*n + b].
    """
    var_order = sorted(eq["lhs_vars"] | eq["rhs_vars"])
    n_vars = len(var_order)
    var_idx = {v: i for i, v in enumerate(var_order)}

    def expr_src(node) -> str:
        if isinstance(node, Var):
            return f"v{var_idx[node.name]}"
        l = expr_src(node.left)
        r = expr_src(node.right)
        return f"M[({l})*n+({r})]"

    L = expr_src(eq["lhs"])
    R = expr_src(eq["rhs"])

    # Build nested for loops as a single function.
    src = ["def check(M, n):"]
    indent = "    "
    for i in range(n_vars):
        src.append(indent * (i + 1) + f"for v{i} in range(n):")
    body_indent = indent * (n_vars + 1)
    src.append(body_indent + f"if {L} != {R}: return False")
    src.append(indent + "return True")
    code = "\n".join(src)
    ns: dict = {}
    exec(code, ns)
    return ns["check"]


# ---------------------------------------------------------------------------
# Magma bank
# ---------------------------------------------------------------------------

def make_table(n: int, fn) -> list[int]:
    return [fn(a, b) for a in range(n) for b in range(n)]


def standard_bank() -> list[dict]:
    bank: list[dict] = []

    # 2-element magmas: enumerate all 16 (one entry per cell ∈ {0,1}, 4 cells).
    for bits in range(16):
        t = [(bits >> i) & 1 for i in range(4)]
        bank.append({"name": f"2elt_{bits:02d}", "n": 2, "table": t})

    # 3-element named magmas from the cheatsheet
    bank.append({"name": "left_cycle3", "n": 3,
                 "table": make_table(3, lambda a, b: (a + 1) % 3)})
    bank.append({"name": "right_cycle3", "n": 3,
                 "table": make_table(3, lambda a, b: (b + 1) % 3)})

    # Single-spike-zero variants on {0,1,2}
    def spike(p, q, r):
        t = [0] * 9
        t[p * 3 + q] = r
        return t

    for (p, q, r) in [(0, 1, 2), (1, 1, 2), (1, 0, 2), (2, 0, 1),
                      (0, 0, 1), (0, 2, 1), (1, 2, 0), (2, 1, 0)]:
        bank.append({"name": f"spike_{p}{q}_{r}", "n": 3, "table": spike(p, q, r)})

    return bank


def conservative_3elt_bank(limit: int | None = None) -> list[dict]:
    """All 3-element magmas where a*b ∈ {a,b} for distinct a,b. Diagonal free.

    Off-diagonal: 6 cells, each binary (left or right input) → 2^6 = 64.
    Diagonal: 3 cells, each ∈ {0,1,2} → 27.
    Total: 64*27 = 1728 conservative magmas.
    """
    out = []
    n = 3
    pairs = [(a, b) for a in range(n) for b in range(n) if a != b]
    diag = [(a, a) for a in range(n)]
    count = 0
    for off_bits in range(1 << len(pairs)):
        for d0 in range(n):
            for d1 in range(n):
                for d2 in range(n):
                    t = [0] * 9
                    for k, (a, b) in enumerate(pairs):
                        t[a * n + b] = a if ((off_bits >> k) & 1) else b
                    t[0] = d0
                    t[1 * n + 1] = d1
                    t[2 * n + 2] = d2
                    out.append({"name": f"cons3_{count}", "n": 3, "table": t})
                    count += 1
                    if limit is not None and count >= limit:
                        return out
    return out


def random_3elt_bank(k: int, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(k):
        t = rng.integers(0, 3, size=9).tolist()
        out.append({"name": f"rand3_{i}", "n": 3, "table": t})
    return out


def enumerate_all_bank(n: int) -> list[dict]:
    """Enumerate every magma of order n. Cells = n*n, each in {0..n-1}.
    Returns n**(n*n) entries — only feasible for n=2 (16) and n=3 (19683)."""
    out = []
    cells = n * n
    total = n ** cells
    for k in range(total):
        t = []
        x = k
        for _ in range(cells):
            t.append(x % n)
            x //= n
        out.append({"name": f"all{n}_{k}", "n": n, "table": t})
    return out


def commutative_bank(n: int, limit: int | None = None) -> list[dict]:
    """All commutative magmas of order n: a*b == b*a. Free cells = n + n*(n-1)/2."""
    out = []
    pairs = []
    for a in range(n):
        for b in range(a, n):
            pairs.append((a, b))
    free = len(pairs)
    total = n ** free
    count = 0
    for k in range(total):
        vals = []
        x = k
        for _ in range(free):
            vals.append(x % n)
            x //= n
        t = [0] * (n * n)
        for (a, b), v in zip(pairs, vals):
            t[a * n + b] = v
            t[b * n + a] = v
        out.append({"name": f"comm{n}_{count}", "n": n, "table": t})
        count += 1
        if limit is not None and count >= limit:
            return out
    return out


def idempotent_commutative_bank(n: int, limit: int | None = None) -> list[dict]:
    """Idempotent (a*a=a) and commutative magmas of order n. Free cells = n*(n-1)/2."""
    out = []
    pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    free = len(pairs)
    total = n ** free
    count = 0
    for k in range(total):
        vals = []
        x = k
        for _ in range(free):
            vals.append(x % n)
            x //= n
        t = [0] * (n * n)
        for d in range(n):
            t[d * n + d] = d
        for (a, b), v in zip(pairs, vals):
            t[a * n + b] = v
            t[b * n + a] = v
        out.append({"name": f"idcomm{n}_{count}", "n": n, "table": t})
        count += 1
        if limit is not None and count >= limit:
            return out
    return out


def random_n_elt_bank(n: int, k: int, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(k):
        t = rng.integers(0, n, size=n * n).tolist()
        out.append({"name": f"rand{n}_{i}", "n": n, "table": t})
    return out


# ---------------------------------------------------------------------------
# Signature computation
# ---------------------------------------------------------------------------

def compute_signatures(equations: list[dict], bank: list[dict]) -> np.ndarray:
    """Returns array of shape (n_eq, n_words) of uint64. Bit k = eq holds in bank[k]."""
    n_eq = len(equations)
    n_b = len(bank)
    n_words = (n_b + 63) // 64

    sigs = np.zeros((n_eq, n_words), dtype=np.uint64)

    # Pre-compile all equations once.
    t0 = time.time()
    checkers = [compile_equation(eq) for eq in equations]
    print(f"  compiled {n_eq} equations in {time.time()-t0:.1f}s", flush=True)

    t0 = time.time()
    for k, m in enumerate(bank):
        M = m["table"]
        n = m["n"]
        word = k // 64
        bit = np.uint64(1) << np.uint64(k % 64)
        for i, ck in enumerate(checkers):
            if ck(M, n):
                sigs[i, word] |= bit
        if (k + 1) % 25 == 0 or k + 1 == n_b:
            print(f"  magma {k+1}/{n_b} ({m['name']}) elapsed {time.time()-t0:.1f}s",
                  flush=True)
    return sigs


# ---------------------------------------------------------------------------
# Rule evaluation: S(eq1) ⊄ S(eq2)  =>  predict FALSE
# ---------------------------------------------------------------------------

def eval_false_rule(sigs: np.ndarray, outcomes: np.ndarray) -> dict:
    """Predict FALSE for pair (i,j) iff exists bit set in sig[i] but not sig[j].
    Outcomes: int8 matrix (0/1), 1 = TRUE (Eq i implies Eq j).
    """
    n = sigs.shape[0]
    fires = 0
    correct = 0  # rule fires AND ground truth is FALSE
    # vectorize per row
    for i in range(n):
        diff = sigs[i] & ~sigs  # (n, n_words)
        fires_i = np.any(diff != 0, axis=1)  # bool array length n
        # exclude self
        fires_i[i] = False
        f = int(fires_i.sum())
        c = int(np.sum(fires_i & (outcomes[i] == 0)))
        fires += f
        correct += c
    total_pairs = n * (n - 1)
    total_false = int((outcomes == 0).sum() - (n if outcomes.diagonal().sum() == n else 0))
    # outcomes diag are likely 1 (eq implies itself); subtract n self pairs from total false count is 0
    total_false = int(((outcomes == 0).sum()))
    coverage = fires / total_pairs
    precision = correct / fires if fires else float("nan")
    recall = correct / total_false if total_false else float("nan")
    return dict(fires=fires, correct=correct, total_pairs=total_pairs,
                total_false=total_false, coverage=coverage,
                precision=precision, recall=recall)


def eval_on_validation(sigs: np.ndarray, problems: list[dict],
                       answers: dict) -> dict:
    """Evaluate FALSE rule on validation problems, broken down by difficulty."""
    by_diff: dict[str, dict] = {}
    for p in problems:
        i = p["eq1_id"] - 1
        j = p["eq2_id"] - 1
        gt = answers[p["id"]]
        diff = p["difficulty"]
        d = by_diff.setdefault(diff, dict(fires=0, fires_correct=0,
                                          total=0, total_false=0))
        d["total"] += 1
        if not gt:
            d["total_false"] += 1
        # rule fires?
        a = sigs[i]; b = sigs[j]
        if int(np.any((a & ~b) != 0)):
            d["fires"] += 1
            if not gt:
                d["fires_correct"] += 1
    for d in by_diff.values():
        d["precision"] = d["fires_correct"] / d["fires"] if d["fires"] else float("nan")
        d["recall"] = d["fires_correct"] / d["total_false"] if d["total_false"] else float("nan")
    return by_diff


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_validation_only(bank, tag, equations, problems, answers, out_dir):
    """Fast path: only evaluate on validation set (no ETP). Use to screen banks."""
    print(f"\n=== {tag}: validation-only ({len(bank)} magmas) ===", flush=True)
    sigs = compute_signatures(equations, bank)
    val_stats = eval_on_validation(sigs, problems, answers)
    for diff, d in sorted(val_stats.items()):
        print(f"  {diff}: fires={d['fires']}/{d['total']} prec={d['precision']:.3f}"
              f" recall={d['recall']:.3f} (false_total={d['total_false']})",
              flush=True)
    return sigs, val_stats


def run(bank: list[dict], tag: str, equations, outcomes, problems, answers,
        out_dir: str):
    print(f"\n=== Running bank '{tag}' with {len(bank)} magmas ===", flush=True)
    sigs = compute_signatures(equations, bank)

    # ETP
    etp_stats = eval_false_rule(sigs, outcomes)
    print(f"  ETP: fires={etp_stats['fires']:,} prec={etp_stats['precision']:.4f}"
          f" recall={etp_stats['recall']:.4f} coverage={etp_stats['coverage']:.4f}",
          flush=True)

    # Validation
    val_stats = eval_on_validation(sigs, problems, answers)
    for diff, d in sorted(val_stats.items()):
        print(f"  {diff}: fires={d['fires']}/{d['total']} prec={d['precision']:.3f}"
              f" recall={d['recall']:.3f} (false_total={d['total_false']})",
              flush=True)

    # save
    np.save(os.path.join(out_dir, f"sigs_{tag}.npy"), sigs)
    with open(os.path.join(out_dir, f"bank_{tag}.json"), "w") as f:
        json.dump(bank, f)
    with open(os.path.join(out_dir, f"results_{tag}.json"), "w") as f:
        json.dump({"etp": {k: (float(v) if isinstance(v, float) else int(v))
                            for k, v in etp_stats.items()},
                    "validation": {diff: {k: (float(v) if isinstance(v, float) else int(v))
                                            for k, v in d.items()}
                                    for diff, d in val_stats.items()},
                    "n_magmas": len(bank)}, f, indent=2)
    return sigs, etp_stats, val_stats


def targeted_search_etp(equations, outcomes, base_bank, attempts_per_pair=200,
                        sizes=(2, 3, 4, 5), max_pairs=4000) -> list[dict]:
    """Targeted search over UNRESOLVED FALSE pairs in the full ETP outcomes
    matrix (limited to max_pairs to keep runtime bounded)."""
    print(f"\n=== ETP targeted search (max {max_pairs} pairs) ===", flush=True)
    sigs = compute_signatures(equations, base_bank)
    n_eq = sigs.shape[0]

    # Find FALSE pairs not currently fired
    print("  finding unresolved ETP FALSE pairs...", flush=True)
    unresolved = []
    for i in range(n_eq):
        diff = sigs[i] & ~sigs
        fires_i = np.any(diff != 0, axis=1)
        # FALSE outcome and rule does not fire
        cand = np.where((outcomes[i] == 0) & ~fires_i)[0]
        for j in cand:
            if i != j:
                unresolved.append((int(i), int(j)))
                if len(unresolved) >= max_pairs:
                    break
        if len(unresolved) >= max_pairs:
            break
    print(f"  unresolved sample: {len(unresolved)}", flush=True)

    checkers = [compile_equation(eq) for eq in equations]
    rng = np.random.default_rng(7)
    new_magmas = []
    found = 0
    for idx, (i, j) in enumerate(unresolved):
        ck_i = checkers[i]; ck_j = checkers[j]
        for trial in range(attempts_per_pair):
            n = sizes[trial % len(sizes)]
            t = rng.integers(0, n, size=n * n).tolist()
            if ck_i(t, n) and not ck_j(t, n):
                new_magmas.append({"name": f"etp_{i}_{j}", "n": n, "table": t})
                found += 1
                break
        if (idx + 1) % 200 == 0:
            print(f"  {idx+1}/{len(unresolved)} {found} new", flush=True)
    print(f"  total new magmas: {found}", flush=True)
    return new_magmas


def targeted_search(equations, problems, answers, base_bank, attempts_per_pair=2000,
                    sizes=(3, 4, 5)) -> list[dict]:
    """For each FALSE validation pair NOT covered by base_bank, look for a magma
    counterexample by random sampling. Return list of NEW magmas found."""
    print("\n=== Targeted search on unresolved validation FALSE pairs ===", flush=True)
    sigs = compute_signatures(equations, base_bank)

    # find unresolved FALSE pairs
    unresolved = []
    for p in problems:
        if answers[p["id"]]:
            continue
        i = p["eq1_id"] - 1
        j = p["eq2_id"] - 1
        a = sigs[i]; b = sigs[j]
        if not int(np.any((a & ~b) != 0)):
            unresolved.append((p["id"], p["difficulty"], i, j))
    print(f"  unresolved FALSE pairs: {len(unresolved)}", flush=True)

    checkers = [compile_equation(eq) for eq in equations]
    rng = np.random.default_rng(42)
    new_magmas = []
    found = 0
    for idx, (pid, diff, i, j) in enumerate(unresolved):
        ck_i = checkers[i]; ck_j = checkers[j]
        hit = None
        for trial in range(attempts_per_pair):
            n = sizes[trial % len(sizes)]
            t = rng.integers(0, n, size=n * n).tolist()
            if ck_i(t, n) and not ck_j(t, n):
                hit = (n, t)
                break
        if hit is not None:
            n, t = hit
            new_magmas.append({"name": f"tgt_{pid}", "n": n, "table": t})
            found += 1
        if (idx + 1) % 25 == 0:
            print(f"  {idx+1}/{len(unresolved)} processed; {found} new magmas",
                  flush=True)
    print(f"  total new magmas: {found}", flush=True)
    return new_magmas


def main():
    print("Loading equations...", flush=True)
    equations = parse_all_equations(os.path.join(DATA, "equations.txt"))
    print(f"  {len(equations)} equations", flush=True)

    print("Loading outcomes...", flush=True)
    outcomes = np.load(os.path.join(DATA, "outcomes_bool.npy"))
    print(f"  shape {outcomes.shape}", flush=True)

    print("Loading validation set...", flush=True)
    problems = json.load(open(os.path.join(DATA, "validation/problems.json")))
    answers = json.load(open(os.path.join(DATA, "validation/answers.json")))
    print(f"  {len(problems)} problems", flush=True)

    out_dir = os.path.join(DATA, "magma_mining")
    os.makedirs(out_dir, exist_ok=True)

    which = sys.argv[1] if len(sys.argv) > 1 else "standard"
    if which == "standard":
        bank = standard_bank()
        run(bank, "standard", equations, outcomes, problems, answers, out_dir)
    elif which == "cons3":
        bank = standard_bank() + conservative_3elt_bank()
        run(bank, "cons3", equations, outcomes, problems, answers, out_dir)
    elif which == "rand3":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        bank = standard_bank() + conservative_3elt_bank() + random_3elt_bank(n, seed=1)
        run(bank, "rand3", equations, outcomes, problems, answers, out_dir)
    elif which == "rand4":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        bank = (standard_bank()
                + conservative_3elt_bank()
                + random_3elt_bank(2000, seed=1)
                + random_n_elt_bank(4, n, seed=2))
        run(bank, "rand4", equations, outcomes, problems, answers, out_dir)
    elif which == "comm4":
        bank = standard_bank() + enumerate_all_bank(3) + commutative_bank(4)
        run_validation_only(bank, "comm4", equations, problems, answers, out_dir)
    elif which == "etp_targeted":
        base = standard_bank() + enumerate_all_bank(3)
        new = targeted_search_etp(equations, outcomes, base,
                                  attempts_per_pair=500, sizes=(2, 3, 4, 5),
                                  max_pairs=2000)
        bank = base + new
        run(bank, "etp_targeted", equations, outcomes, problems, answers, out_dir)
    elif which == "structured":
        bank = (standard_bank()
                + enumerate_all_bank(3)              # all 19683 order-3 magmas
                + commutative_bank(4)                # all 4^10 = ~1M order-4 commutative
                )
        run(bank, "structured", equations, outcomes, problems, answers, out_dir)
    elif which == "all3":
        bank = standard_bank() + enumerate_all_bank(3)
        run(bank, "all3", equations, outcomes, problems, answers, out_dir)
    elif which == "idcomm4":
        bank = (standard_bank()
                + enumerate_all_bank(3)
                + idempotent_commutative_bank(4)
                + idempotent_commutative_bank(5, limit=20000))
        run(bank, "idcomm4", equations, outcomes, problems, answers, out_dir)
    elif which == "overnight":
        # Largest practical bank — run unattended.
        bank = (standard_bank()
                + enumerate_all_bank(3)                          # 19683
                + idempotent_commutative_bank(4)                 # 4096
                + idempotent_commutative_bank(5, limit=20000)    # 20k
                + random_n_elt_bank(4, 5000, seed=11)
                + random_n_elt_bank(5, 3000, seed=12)
                + random_n_elt_bank(6, 2000, seed=13)
                + random_n_elt_bank(7, 1000, seed=14))
        run(bank, "overnight", equations, outcomes, problems, answers, out_dir)
    elif which == "targeted":
        base = (standard_bank()
                + conservative_3elt_bank()
                + random_3elt_bank(3000, seed=1))
        new = targeted_search(equations, problems, answers, base,
                              attempts_per_pair=int(sys.argv[2]) if len(sys.argv) > 2 else 5000,
                              sizes=(3, 4, 5, 6))
        bank = base + new
        run(bank, "targeted", equations, outcomes, problems, answers, out_dir)
    elif which == "big":
        n4 = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        bank = (standard_bank()
                + conservative_3elt_bank()
                + random_3elt_bank(3000, seed=1)
                + random_n_elt_bank(4, n4, seed=2)
                + random_n_elt_bank(5, n4 // 4, seed=3))
        run(bank, "big", equations, outcomes, problems, answers, out_dir)


if __name__ == "__main__":
    main()
