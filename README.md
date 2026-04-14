# eq-playground

The challenge asks, for pairs of universally-quantified equations `(E1, E2)`
over a single binary operation: does `E1 ⇒ E2` hold in every magma? Ground
truth is the 4694 × 4694 implication matrix from the [Equational Theories
Project](https://leanprover-community.github.io/equational_theories/).

This repo is the deterministic backbone behind cheatsheet `EQT010003`
(`cheatsheets/bank_lookup_v5.txt`). Two things you can regenerate:

### (A) Best programmatic coverage on the full ETP matrix

```bash
python analysis/cascade_v14.py
```

Reference output on the full 22,028,942-pair matrix:

| metric | value |
| --- | --- |
| Overall accuracy | **93.57%** |
| Sound rules coverage | **91.83%** at **100.00%** precision |
| Non-DEFAULT coverage (sound + D9 heuristic) | **92.92%** at **99.93%** precision |
| Hard3 validation accuracy | **66.75%** |

`cascade_v14` combines 18 sound syntactic rules (D1–D10 family, spine-based
predicates) with a precomputed counterexample bank over ~5,000 small magmas.
Per-rule firings and precision are written to
`data/magma_mining/cascade_v14_report.json`.

### (B) Coverage restricted to rules inside `bank_lookup_v5.txt`

```bash
python analysis/eval_bank_lookup_v5.py
```

This runs only the rules that the LLM is actually instructed to execute
from `cheatsheets/bank_lookup_v5.txt` — T1/T2/T3, L1/L2/L3, M1–M7 (with the
specific 2- and 3-element magmas defined in the cheatsheet), D8, D10, D9,
D5, D5b, plus DEFAULT=TRUE — and reports how much the cheatsheet's
deterministic core would catch if the LLM executed it perfectly.

Reference output on the full ETP matrix:

| metric | value |
| --- | --- |
| Sound rules coverage | **88.16%** at **100.00%** precision |
| Sound + D9 heuristic | **89.40%** at **99.76%** precision |
| Overall accuracy (with DEFAULT=TRUE) | **95.55%** |
| Hard3 sound coverage | **24.25%** at **100%** precision |
| Hard3 overall | **72.75%** |

Per-rule firings are written to
`data/magma_mining/eval_bank_lookup_v5_report.json`.

## Repo layout

```
analysis/
  parse_equation.py          # term parser, shared
  procedural_v2_checker.py   # feature extraction + 18-rule cascade (v13)
  magma_counterexamples.py   # per-equation satisfaction evaluator
  cascade_v14.py             # ★ best programmatic baseline
  magma_mining.py            # regenerates the counterexample bank
  build_bank_lookup.py       # regenerates the bank_lookup cheatsheet from training
  eval_bank_lookup_v5.py     # ★ runs only the bank_lookup_v5.txt rules on the ETP matrix
  eval_checker_full.py       # evaluate v13 cascade vs ETP / validation / community bench
  eval_with_counterex.py     # evaluate cascade overlayed with the counterexample bank
cheatsheets/
  bank_lookup_v5.txt         # ★ final LLM cheatsheet
data/                        # populate locally, see data/README.md
```

## Running locally

### 1. Install

```bash
pip install -e .
```

Only `numpy` is required.

### 2. Populate `data/`

See [`data/README.md`](data/README.md). You need `equations.txt`,
`outcomes_bool.npy`, and the SAIR validation split under `data/validation/`.

### 3. Build the magma counterexample bank

```bash
python analysis/magma_mining.py
```

Produces `data/magma_mining/{sat_merged_v2,refuted_merged_v2}.npy` — both
eval scripts depend on these.

### 4. Reproduce the two baselines

```bash
python analysis/cascade_v14.py           # (A) best programmatic coverage
python analysis/eval_bank_lookup_v5.py   # (B) cheatsheet-only rules
```

Both print a per-rule breakdown + aggregate coverage/precision to stdout
and write a JSON report under `data/magma_mining/`.

### 5. (Optional) Regenerate the cheatsheet

```bash
python analysis/build_bank_lookup.py
```

Regenerates a bank-lookup cheatsheet from `data/training/problems.json`.
The shipped `bank_lookup_v5.txt` is the polished final version.

