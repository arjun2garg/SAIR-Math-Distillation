# `analysis/` — multi-cheatsheet programmatic harness

The cross-cheatsheet generalization study lives here. Each cheatsheet is
transcribed into a deterministic Python cascade and run against every
HuggingFace SAIR split + the full 22M-pair ETP cross-product.

## Files

```
parse_equation.py          # term parser
magma_counterexamples.py   # per-equation satisfaction evaluator
_common.py                 # ETP context, magma library, vectorized full-ETP runner
aj_checker.py              # one cascade per cheatsheet
dufius_checker.py
eucalyptus_checker.py
pi_checker.py
reza_jamei_checker.py
arjun_garg_checker.py
vt_checker.py
yan-biao_checker.py
aggregate.py               # combine results into RESULTS_AUTO.md + COMPARISON.json
RESULTS.md                 # curated comparison report
RESULTS_AUTO.md            # auto-generated index from aggregate.py
results/<cheatsheet>/      # per-split JSON, full_etp.json, SUMMARY.md, summary.json
```

## Usage

Run a single cheatsheet (writes to `results/<cs>/`):

```bash
python arjun_garg_checker.py
```

Run all of them:

```bash
for cs in aj dufius eucalyptus pi reza_jamei arjun_garg vt yan-biao; do
  python "${cs}_checker.py"
done
python aggregate.py
```

## How a checker is structured

Every checker exports the same shape:

```python
RULE_ORDER = [...]                    # cascade order, first-match-wins
TRUE_RULES = {...}                    # subset of RULE_ORDER that fires TRUE

def fires_for_rule(rule_name) -> bool[4694, 4694]:
    """Per-rule (i, j) candidate mask, irrespective of cascade position."""

def main():
    ctx = load_etp_context(load_gold=True)
    for split in SPLITS:
        s = run_split(split, ctx, ...)   # scalar per-problem runner
        save_summary(s, ...)
    s_etp = run_full_etp(ctx, fires_for_rule, RULE_ORDER, TRUE_RULES)  # vectorized
    save_summary(s_etp, ...)
```

The full-ETP run walks `RULE_ORDER`, assigning each `(i, j)` to the FIRST
rule whose mask is True. The last rule must therefore fire everywhere
(typically a `DEFAULT_*` mask of all-True).

## What `_common.py` provides

- `load_etp_context(load_gold=True)` — parsed equations, compiled
  satisfaction-checkers, the (4694, 4694) gold matrix, magma sat-vector cache.
- `MAGMA_LIB` — named witness magmas (orders 2/3/4) plus an
  `affine_table(a, b, n)` helper for `x*y = a*x + b*y mod n`.
- `magma_masks(ctx, names)` — `(4694, 4694)` FALSE-witness masks per magma.
- `run_split(stem, ctx, ...)` — scalar per-problem runner for HF splits.
- `run_full_etp(ctx, fires_for_rule, rule_order, true_rules)` — vectorized
  runner over the 22M cross-product. Returns a per-rule breakdown +
  confusion matrix + accuracy.
- `summarize`, `print_summary`, `save_summary` — output helpers.

## Output format

For each run, `results/<cs>/<split>.json`:

```json
{
  "dataset": "hard3",
  "n": 400,
  "n_correct": 297,
  "accuracy": 0.7425,
  "by_rule": {"M2": {"n": 34, "tp": 0, "tn": 34, "fp": 0, "fn": 0}, ...},
  "rule_order": [...],
  "true_rules": [...],
  "confusion": {"tp": 163, "fp": 71, "tn": 134, "fn": 32},
  "rows": [...]              // dropped from full_etp.json (too large)
}
```

`SUMMARY.md` is the same data in human-readable Markdown.
