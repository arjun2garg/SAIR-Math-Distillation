# Cheatsheet generalization study — programmatic ceiling on SAIR ETP

Companion code for an upcoming writeup on **how SAIR cheatsheets generalize**.
A "cheatsheet" here is a structured rulebook an LLM follows to decide, for a
pair of universally-quantified equations `(E1, E2)` over a single binary
operation `*`: does `E1 ⇒ E2` hold in every magma?

For each cheatsheet, we transcribe its rules into a deterministic Python
cascade and run that cascade — with **zero LLM error** — across every
HuggingFace SAIR split plus the full **22,033,636-pair ETP cross-product**.
The number you get out is the cheatsheet's **ceiling**: real LLM accuracy will
be at or below this, since model error in rule execution can only subtract.

Ground truth is the 4694×4694 implication matrix from the
[Equational Theories Project](https://leanprover-community.github.io/equational_theories/).
SAIR splits live at the
[SAIRfoundation HuggingFace dataset](https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems).

## Repo layout

```
analysis/
  parse_equation.py          # term parser (shared)
  magma_counterexamples.py   # per-equation satisfaction evaluator (shared)
  _common.py                 # ETP context, magma library, vectorized full-ETP runner
  aj_checker.py              # ── one cascade per cheatsheet ──
  dufius_checker.py
  eucalyptus_checker.py
  pi_checker.py
  reza_jamei_checker.py
  arjun_garg_checker.py
  vt_checker.py
  yan-biao_checker.py
  aggregate.py               # combine per-cheatsheet outputs
  RESULTS.md                 # curated comparison report (per-split + full ETP)
  results/<cheatsheet>/      # per-cheatsheet outputs (per-split JSON, full_etp.json, SUMMARY.md)
cheatsheets/                 # the 8 cheatsheets evaluated
  aj.txt
  arjun_garg.txt
  dufius.txt
  eucalyptus.txt
  pi.txt
  reza_jamei.txt
  vt.txt
  yan-biao.txt
data/
  equations.txt              # 4694 ETP equations
  sair_eval/<split>.jsonl    # the 9 SAIR HF splits
  README.md
old_results/                 # archive of the earlier single-cheatsheet eval
```

## How a programmatic checker works

Every cheatsheet boils down to a **cascade of rules** of three flavours:

1. **Sound finite-magma witnesses.** Pick a Cayley table `M`. Compute
   `sat[i] = (Eq_{i+1} holds in M for every assignment)`. The pair `(i, j)` is
   provably FALSE if `sat[i] ∧ ¬sat[j]`. 100% precision by construction.
2. **Per-equation invariants** (e.g. "leftmost-leaf agrees", "variable parity
   matches"). Same outer-product trick: `holds[i] ∧ ¬holds[j]` is the
   refutation mask.
3. **Structural / heuristic predicates** on parse-tree features (M, S, V,
   bare-LHS, kind, occ, …). These are NOT sound — they're priors. They get
   used as defaults when no sound rule fires.

The shared module `analysis/_common.py` provides:

- A pre-loaded `ETPContext` with parsed equations, the gold matrix, and a
  cache of magma satisfaction vectors.
- A library of named witness magmas (`MAGMA_LIB`) covering everything the 8
  cheatsheets reference (left/right projection, XOR, NAND, BCK, RPS, Knuth
  central groupoid order 4, rectangular band, affine `ax+by mod n`, …).
- A vectorized **`run_full_etp(ctx, fires_for_rule, rule_order, true_rules)`**
  that walks the cascade as `(4694, 4694)` boolean masks. The 22M-pair run
  takes a few seconds per cheatsheet.

A per-cheatsheet checker just declares `RULE_ORDER` and `TRUE_RULES`, plus a
`fires_for_rule(name) -> bool[4694, 4694]` callback. See any of the
`analysis/<cs>_checker.py` files for the full pattern.

## Running it

### 1. Install

```bash
pip install -e .            # installs numpy
```

### 2. Populate `data/`

You need:

- `data/equations.txt` — the 4694 ETP equations (in repo).
- `data/outcomes_bool.npy` — the 4694×4694 ETP gold matrix (in repo, 22 MB).
  Generated from the ETP project's `outcomes.json`; see `data/README.md` for
  the conversion snippet if you ever need to regenerate it.
- `data/sair_eval/<split>.jsonl` — the 9 SAIR HF splits. To download:

  ```bash
  mkdir -p data/sair_eval
  for split in normal hard hard1 hard2 hard3 \
               evaluation_normal evaluation_hard evaluation_extra_hard evaluation_order5; do
    curl -sL "https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems/resolve/main/data/${split}.jsonl" \
         -o "data/sair_eval/${split}.jsonl"
  done
  ```

- `data/full_etp_cache.pkl` *(optional, 163 MB, gitignored)* — combined
  pickle with gold + magma satisfaction matrices, faster to load than the
  raw `.npy`. The harness reads it if present and falls back to
  `outcomes_bool.npy` otherwise.

### 3. Run any cheatsheet

```bash
python analysis/arjun_garg_checker.py
python analysis/aj_checker.py
python analysis/reza_jamei_checker.py
# … etc
```

Each script writes `analysis/results/<cheatsheet>/`:
- `<split>.json` for each HF split (full per-problem rows + per-rule
  breakdown + confusion matrix)
- `full_etp.json` (rows omitted; per-rule breakdown across 22M pairs)
- `summary.json` (everything in one place)
- `SUMMARY.md` (human-readable report)

### 4. Aggregate

```bash
python analysis/aggregate.py
```

Writes `analysis/results/COMPARISON.json` and `analysis/RESULTS_AUTO.md`
(auto-generated index). The curated narrative report stays in
`analysis/RESULTS.md`.

## Adding a new cheatsheet

1. Drop the cheatsheet text under `cheatsheets/<your-name>.txt`.
2. Copy any existing `analysis/<cs>_checker.py` as a template.
3. Define your `RULE_ORDER` and `TRUE_RULES`. Implement each rule as a
   per-equation invariant (→ outer-product mask) or pull a magma table out of
   `MAGMA_LIB`. Add new magmas to `MAGMA_LIB` if needed.
4. Write a `fires_for_rule(name)` that returns a `(4694, 4694)` bool mask per
   rule. The last rule in `RULE_ORDER` must have a default `True`-everywhere
   mask so every pair is covered.
5. Run the script. Outputs land under `analysis/results/<your-name>/`.

## Findings

This repo is the methodology / how-to. Insights about cheatsheet generalization
— which rules generalize from a single split to the full 22M ETP, where
heuristic priors invert on adversarial splits, and which cheatsheets win on
`evaluation_extra_hard` for the right vs wrong reasons — are written up in a
separate post. The raw numbers backing those findings are in
[`analysis/RESULTS.md`](analysis/RESULTS.md), and the per-rule detail is in
`analysis/results/<cheatsheet>/SUMMARY.md`.

## Older work

The previous iteration of this repo focused on a single cheatsheet
(`bank_lookup_v5.txt`, then `arjun_garg`) and is preserved under
[`old_results/`](old_results/) (including the prior README and the
single-cheatsheet HF findings doc).
