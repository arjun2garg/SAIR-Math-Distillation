# `data/` — inputs and ground truth

| file | size | source | required for |
|---|---:|---|---|
| `equations.txt` | 159 KB | [Equational Theories Project](https://github.com/leanprover-community/equational_theories) | every checker |
| `outcomes_bool.npy` | 22 MB | derived from ETP `outcomes.json` | full-ETP run |
| `sair_eval/<split>.jsonl` | <1 MB each | [SAIRfoundation/equational-theories-selected-problems](https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems) | per-split runs |
| `full_etp_cache.pkl` *(optional)* | 163 MB | locally generated, gitignored | speeds up full-ETP run, not required |

## Regenerating `outcomes_bool.npy` from ETP

```python
import json, numpy as np
d = json.load(open("data/outcomes.json"))
np.save("data/outcomes_bool.npy", np.array(d["outcomes"], dtype=bool))
```

Where `outcomes.json` is the 4694×4694 implication matrix published by the
ETP project.

## Downloading the SAIR splits

```bash
mkdir -p data/sair_eval
for split in normal hard hard1 hard2 hard3 \
             evaluation_normal evaluation_hard evaluation_extra_hard evaluation_order5; do
  curl -sL "https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems/resolve/main/data/${split}.jsonl" \
       -o "data/sair_eval/${split}.jsonl"
done
```

## Notes on `full_etp_cache.pkl`

Some sub-pipelines (not in this repo) cache the gold matrix together with
witness-magma satisfaction tables in a single pickle. If `full_etp_cache.pkl`
is present, `analysis/_common.py` reads the gold matrix from it; otherwise it
falls back to `outcomes_bool.npy`. The two paths produce identical results.
