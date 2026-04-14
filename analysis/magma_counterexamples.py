"""Mine sound FALSE answers via finite-magma counterexamples.

For each equation we precompile a function that, given a magma op-table T
of size N, returns True iff the equation holds for *all* assignments of its
variables to {0..N-1}.

If a magma m satisfies Eq1 but not Eq2, then Eq1 -> Eq2 is provably FALSE.
We OR these refutations across a library of small magmas to obtain a
sound REFUTED[i,j] matrix.

Usage:
    .venv/bin/python analysis/magma_counterexamples.py build
    .venv/bin/python analysis/magma_counterexamples.py eval
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from parse_equation import Op, Var, parse_all_equations  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
EQS_PATH = REPO / "data/equations.txt"
OUT_DIR = REPO / "data/counterex"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Per-equation precompiled satisfaction check
# ---------------------------------------------------------------------------

def _eval_node(node, assigns):
    """Evaluate a parse tree at a stack of variable assignments.

    `assigns` is a dict {var_name: np.ndarray of shape (k,)} where k is the
    total number of assignments being evaluated in parallel.

    Returns an np.ndarray of shape (k,) of element values (T-indices).
    Closes over `T` in the calling scope by returning a function that takes T.
    """
    raise NotImplementedError  # use the closure builder below


def compile_equation(lhs, rhs):
    """Return a function `check(T) -> bool` that evaluates whether the
    equation holds on every assignment to {0..N-1}, where N = T.shape[0]."""
    # Collect variables in deterministic order
    vars_set = set()

    def collect(n):
        if isinstance(n, Var):
            vars_set.add(n.name)
        else:
            collect(n.left)
            collect(n.right)

    collect(lhs)
    collect(rhs)
    var_names = sorted(vars_set)
    nvars = len(var_names)

    # The "assignment grid": for each variable, an axis. We evaluate vectorized
    # by passing flat arrays. We precompute index arrays once per N.

    def build(T):
        N = T.shape[0]
        if nvars == 0:
            grids = [np.zeros(1, dtype=np.int64)]  # unused; eq has no vars
            k = 1
            assigns = {}
        else:
            ranges = [np.arange(N) for _ in range(nvars)]
            mesh = np.meshgrid(*ranges, indexing="ij")
            assigns = {var_names[i]: mesh[i].ravel() for i in range(nvars)}
            k = N**nvars

        def evalnode(n):
            if isinstance(n, Var):
                return assigns[n.name]
            l = evalnode(n.left)
            r = evalnode(n.right)
            return T[l, r]

        return evalnode(lhs), evalnode(rhs)

    def check(T):
        L, R = build(T)
        return bool(np.array_equal(L, R))

    check.nvars = nvars
    check.var_names = var_names
    return check


# ---------------------------------------------------------------------------
# Compile all equations once
# ---------------------------------------------------------------------------

def load_compiled():
    eqs = parse_all_equations(str(EQS_PATH))
    compiled = []
    for eq in eqs:
        compiled.append(compile_equation(eq["lhs"], eq["rhs"]))
    return compiled


# ---------------------------------------------------------------------------
# Compute satisfaction vector for one magma
# ---------------------------------------------------------------------------

def satisfaction_vector(T, compiled):
    out = np.zeros(len(compiled), dtype=bool)
    for i, c in enumerate(compiled):
        if c(T):
            out[i] = True
    return out


# ---------------------------------------------------------------------------
# Magma library generators
# ---------------------------------------------------------------------------

def all_magmas_n(N):
    """Yield every N×N op table over {0..N-1} (there are N^(N*N) of them)."""
    cells = N * N
    for tup in itertools.product(range(N), repeat=cells):
        yield np.array(tup, dtype=np.int8).reshape(N, N)


def random_magmas(N, count, seed=0):
    rng = np.random.default_rng(seed)
    for _ in range(count):
        yield rng.integers(0, N, size=(N, N), dtype=np.int8)


def structured_magmas(N):
    """A handful of structured magmas: projections, constants, mod arithmetic."""
    out = []
    # Constant magmas
    for c in range(N):
        T = np.full((N, N), c, dtype=np.int8)
        out.append(("const_%d" % c, T))
    # Left projection: a*b = a
    out.append(("left_proj", np.tile(np.arange(N, dtype=np.int8)[:, None], (1, N))))
    # Right projection
    out.append(("right_proj", np.tile(np.arange(N, dtype=np.int8)[None, :], (N, 1))))
    # Cyclic add (Z/n)
    add = (np.arange(N)[:, None] + np.arange(N)[None, :]) % N
    out.append(("zn_add", add.astype(np.int8)))
    # Cyclic sub
    sub = (np.arange(N)[:, None] - np.arange(N)[None, :]) % N
    out.append(("zn_sub", sub.astype(np.int8)))
    # Multiplication mod N
    mul = (np.arange(N)[:, None] * np.arange(N)[None, :]) % N
    out.append(("zn_mul", mul.astype(np.int8)))
    # Max / min
    out.append(("max", np.maximum(np.arange(N)[:, None], np.arange(N)[None, :]).astype(np.int8)))
    out.append(("min", np.minimum(np.arange(N)[:, None], np.arange(N)[None, :]).astype(np.int8)))
    return out


# ---------------------------------------------------------------------------
# Build phase
# ---------------------------------------------------------------------------

def build():
    print("Loading equations + compiling…")
    t0 = time.time()
    compiled = load_compiled()
    print(f"  compiled {len(compiled)} equations in {time.time()-t0:.1f}s")

    sat_vectors = []
    labels = []

    def add(name, T):
        v = satisfaction_vector(T, compiled)
        sat_vectors.append(v)
        labels.append(name)
        return v

    # ----- N = 2: enumerate all 16 -----
    print("\nN=2: all 16 magmas")
    t0 = time.time()
    for idx, T in enumerate(all_magmas_n(2)):
        v = add(f"n2_{idx:02d}", T)
        print(f"  n2_{idx:02d} satisfies {int(v.sum())}/4694")
    print(f"  N=2 done in {time.time()-t0:.1f}s")

    # ----- N = 3: structured + random sample -----
    print("\nN=3: structured + 2000 random")
    t0 = time.time()
    for name, T in structured_magmas(3):
        v = add(f"n3_{name}", T)
    for i, T in enumerate(random_magmas(3, 2000, seed=3)):
        add(f"n3_rand{i:04d}", T)
    print(f"  N=3 done in {time.time()-t0:.1f}s")

    # ----- N = 4: structured + random sample -----
    print("\nN=4: structured + 2000 random")
    t0 = time.time()
    for name, T in structured_magmas(4):
        add(f"n4_{name}", T)
    for i, T in enumerate(random_magmas(4, 2000, seed=4)):
        add(f"n4_rand{i:04d}", T)
    print(f"  N=4 done in {time.time()-t0:.1f}s")

    # ----- N = 5: structured + random sample -----
    print("\nN=5: structured + 1000 random")
    t0 = time.time()
    for name, T in structured_magmas(5):
        add(f"n5_{name}", T)
    for i, T in enumerate(random_magmas(5, 1000, seed=5)):
        add(f"n5_rand{i:04d}", T)
    print(f"  N=5 done in {time.time()-t0:.1f}s")

    S = np.stack(sat_vectors).astype(bool)  # (M, 4694)
    print(f"\nSat matrix shape: {S.shape}, total True {S.sum()}")
    np.save(OUT_DIR / "sat.npy", S)
    (OUT_DIR / "labels.json").write_text(json.dumps(labels))
    print(f"Saved to {OUT_DIR}/sat.npy and labels.json")


# ---------------------------------------------------------------------------
# Refutation matrix
# ---------------------------------------------------------------------------

def build_refuted(S):
    """REFUTED[i,j] = True iff some magma satisfies eq i and not eq j."""
    n_eq = S.shape[1]
    REFUTED = np.zeros((n_eq, n_eq), dtype=bool)
    for m in range(S.shape[0]):
        sat = S[m]  # (n_eq,)
        # contribute outer product sat[:,None] & ~sat[None,:]
        REFUTED |= sat[:, None] & ~sat[None, :]
    return REFUTED


# ---------------------------------------------------------------------------
# Eval phase
# ---------------------------------------------------------------------------

def eval_():
    S = np.load(OUT_DIR / "sat.npy")
    print(f"Loaded sat matrix {S.shape}")

    print("Building refutation matrix…")
    t0 = time.time()
    REFUTED = build_refuted(S)
    print(f"  done in {time.time()-t0:.1f}s; refuted={REFUTED.sum()}")

    np.save(OUT_DIR / "refuted.npy", REFUTED)

    # ----- Soundness + coverage on full Lean graph -----
    gold = np.load(REPO / "data/outcomes_bool.npy").astype(bool)
    n_pairs = gold.size - gold.shape[0]  # excl diagonal

    diag = np.eye(gold.shape[0], dtype=bool)
    refuted_off = REFUTED & ~diag

    # Soundness: every refuted pair should be FALSE in gold
    bad = refuted_off & gold
    print(f"\nFull Lean graph:")
    print(f"  refuted off-diag = {refuted_off.sum():,}")
    print(f"  unsound (refuted but gold TRUE) = {bad.sum()}")
    n_false = (~gold & ~diag).sum()
    print(f"  total gold FALSE = {n_false:,}")
    print(f"  refuted/false = {refuted_off.sum() / n_false:.4f} "
          f"(coverage of FALSE pairs)")
    print(f"  refuted/all = {refuted_off.sum() / n_pairs:.4f}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build()
    elif cmd == "eval":
        eval_()
    else:
        print(f"Unknown command {cmd}")
        sys.exit(2)
