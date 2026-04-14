# eq-playground

Programmatic baselines for the [SAIR Mathematics Distillation Challenge — Equational Theories](https://competition.sair.foundation/competitions/mathematics-distillation-challenge-equational-theories-stage1/overview).

The challenge asks, for pairs of universally-quantified equations `(E1, E2)`
over a single binary operation: does `E1 ⇒ E2` hold in every magma? Ground
truth is the full 4694 × 4694 implication matrix from the [Equational
Theories Project](https://leanprover-community.github.io/equational_theories/).

This repo contains two baselines:

| Baseline | Kind | Where it lives |
| --- | --- | --- |
| **`cascade_v14`** | Pure Python decision cascade — 18 sound syntactic rules plus a precomputed counterexample bank over small magmas. No LLM calls. | `analysis/cascade_v14.py` |
| **`bank_lookup_v5`** | The same decision logic compressed into a ≤12 KB cheatsheet prompt intended for the competition's weak-judge models. | `cheatsheets/bank_lookup_v5.txt` (generator: `analysis/build_bank_lookup.py`) |

Reference accuracy for `cascade_v14` on the full ETP implication matrix is
~93.6% (and ~66.8% on the hard3 validation slice). The `bank_lookup_v5`
cheatsheet is the same pipeline rendered as an LLM prompt, which trades
some headroom for portability to models that cannot execute code.

## Repo layout

```
analysis/
  parse_equation.py          # term parser, shared
  procedural_v2_checker.py   # feature extraction + 18-rule cascade (v13 rules)
  magma_counterexamples.py   # counterexample-bank lookup helpers
  cascade_v14.py             # ★ best programmatic baseline
  magma_mining.py            # regenerates the counterexample bank
  build_bank_lookup.py       # ★ regenerates the bank_lookup cheatsheet from training data
  eval_checker_full.py       # evaluate cascade vs ETP / validation / community bench
  eval_with_counterex.py     # evaluate cascade overlayed with the counterexample bank
cheatsheets/
  bank_lookup_v5.txt         # ★ final LLM cheatsheet
data/                        # populate locally, see data/README.md
```

## Running the baselines

### 1. Install

```bash
pip install -e .
```

The only runtime dependency is `numpy`.

### 2. Populate `data/`

See [`data/README.md`](data/README.md) for which files are required and
where to get them. At minimum you need:

- `data/equations.txt` — the 4694 base equations
- `data/outcomes_bool.npy` — the 4694 × 4694 implication matrix (convert
  from the ETP project's `outcomes.json`)
- `data/training/problems.json` — training-set pairs (for
  `build_bank_lookup.py`)
- `data/validation/problems.json` + `data/validation/answers.json` — for
  evaluation

### 3. Build the counterexample bank

```bash
python analysis/magma_mining.py
```

Produces `data/magma_mining/{sat_merged_v2,refuted_merged_v2}.npy` plus the
`bank_*.json` metadata files. This step is needed by `cascade_v14.py` and
`eval_with_counterex.py`.

### 4. Run the pure-code baseline

```bash
python analysis/cascade_v14.py
```

Writes `data/magma_mining/cascade_v14_report.json` with per-rule firing
counts and precision, and prints the aggregate accuracy table.

### 5. Regenerate the cheatsheet

```bash
python analysis/build_bank_lookup.py
```

Writes an initial bank-lookup cheatsheet under `cheatsheets/`. The shipped
`bank_lookup_v5.txt` is the polished final version of this family; the
script regenerates the programmatic core from training-set FALSE pairs.

### 6. Evaluate

```bash
python analysis/eval_checker_full.py       # cascade vs ETP / validation / community bench
python analysis/eval_with_counterex.py     # same, plus counterexample bank overlay
```

## Notes

- All scripts expect to be invoked from the repo root; they self-bootstrap
  `sys.path` to find sibling modules.
- Large derived binaries (`outcomes_bool.npy`, `sat_merged_v2.npy`,
  `refuted_merged_v2.npy`) are not committed — regenerate them as
  described above.
