# `data/` — local setup

Nothing in this directory is committed. The baselines read from files you
populate locally. The required inputs are:

## 1. ETP implication data

From the [Equational Theories Project](https://github.com/leanprover-community/equational_theories):

- `data/equations.txt` — 4694 base equations, one per line (1-indexed).
- `data/outcomes.json` — full 4694 × 4694 implication matrix with ground
  truth, published as `outcomes.json` in the ETP project.

After downloading `outcomes.json`, convert it to the packed boolean form
every script expects:

```python
import json, numpy as np
d = json.load(open("data/outcomes.json"))
np.save("data/outcomes_bool.npy", np.array(d["outcomes"], dtype=bool))
```

You can then delete `outcomes.json` — the kept scripts only read
`outcomes_bool.npy` (except `eval_checker_full.py`, which reads
`outcomes.json` directly; keep it around if you plan to run that script).

## 2. SAIR competition splits

From the [SAIR competition page](https://competition.sair.foundation/competitions/mathematics-distillation-challenge-equational-theories-stage1/overview):

```
data/training/problems.json
data/validation/problems.json
data/validation/answers.json
data/community_bench.json
```

`training/problems.json` is consumed by `build_bank_lookup.py`.
`validation/{problems,answers}.json` and `community_bench.json` are
consumed by the evaluation scripts.

## 3. Generated artifacts

Running `python analysis/magma_mining.py` populates `data/magma_mining/`
with:

- `bank_*.json` — per-library magma specifications
- `sigs_*.npy`, `sat_*.npy`, `refuted_*.npy` — per-library equation
  signatures
- `sat_merged_v2.npy`, `refuted_merged_v2.npy` — merged bank across
  libraries (this is what `cascade_v14.py` reads)
- `results_*.json` — coverage / precision per library

Running `python analysis/cascade_v14.py` additionally writes
`data/magma_mining/cascade_v14_report.json`.

## Expected final layout

```
data/
├── equations.txt
├── outcomes_bool.npy            # packed from outcomes.json
├── outcomes.json                # only if running eval_checker_full.py
├── community_bench.json
├── training/
│   └── problems.json
├── validation/
│   ├── problems.json
│   └── answers.json
└── magma_mining/                # produced by analysis/magma_mining.py
    ├── bank_*.json
    ├── sat_merged_v2.npy
    ├── refuted_merged_v2.npy
    └── ...
```
