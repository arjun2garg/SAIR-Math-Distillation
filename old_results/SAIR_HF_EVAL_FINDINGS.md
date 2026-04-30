# Programmatic v10b evaluation on the SAIR HuggingFace problem set

**Date:** 2026-04-30
**Cheatsheet under test:** `cheatsheets/bank_lookup_v10b.txt` (locked ship)
**Dataset:** [`SAIRfoundation/equational-theories-selected-problems`](https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems)
**Method:** programmatic execution of the v10b cascade (no LLM) — measures the cheatsheet's ceiling under perfect rule execution.

---

## 1. Headline numbers

| split | n | TRUE/FALSE | accuracy | notes |
|---|---:|---:|---:|---|
| `evaluation_extra_hard` | 200 | 100/100 | **9.5%** | worse than always-TRUE/always-FALSE (50%) |
| `hard3` | 400 | 195/205 | **74.2%** | within the regime v10b was tuned for |

The 9.5% is not a bug — it's a genuine finding that the extra-hard curators picked problems where every structural prior in v10b is inverted. See §3.

---

## 2. Rule-by-rule breakdown

### `evaluation_extra_hard` (n=200)

| rule | verdict | fires | correct | wrong | precision | comment |
|---|---|---:|---:|---:|---:|---|
| L1 | FALSE | 0 | – | – | – | never |
| L2 | FALSE | 0 | – | – | – | never |
| L3 | FALSE | 0 | – | – | – | never |
| M1 | FALSE | 0 | – | – | – | never |
| M2 | FALSE | 0 | – | – | – | never |
| M3 | FALSE | 0 | – | – | – | never |
| M4 | FALSE | 0 | – | – | – | never |
| M6 | FALSE | 0 | – | – | – | never |
| M7 | FALSE | 0 | – | – | – | never |
| D8 | FALSE | 0 | – | – | – | never |
| T1 | TRUE  | 0 | – | – | – | never |
| T3 | TRUE  | 0 | – | – | – | never |
| T4 | TRUE  | 0 | – | – | – | never |
| **F1**  | FALSE | **65**  | 0   | 65  | **0.0%**   | all 65 are gold-TRUE — pure FN |
| B1  | FALSE | 0   | –   | –   | –          | never |
| **B2a** | TRUE  | **112** | 12  | 100 | **10.7%**  | 12 gold-TRUE / 100 gold-FALSE |
| **B2b** | TRUE  | **7**   | 7   | 0   | **100.0%** | only clean rule on this set |
| **B2c** | FALSE | **16**  | 0   | 16  | **0.0%**   | all 16 are gold-TRUE — pure FN |

Confusion matrix:

|             | pred TRUE | pred FALSE |
|---          |---:|---:|
| gold TRUE   | 19 | 81 |
| gold FALSE  | 100 | 0 |

### `hard3` (n=400)

| rule | verdict | fires | correct | wrong | precision | comment |
|---|---|---:|---:|---:|---:|---|
| L1 | FALSE | 0 | – | – | – | never |
| L2 | FALSE | 0 | – | – | – | never |
| L3 | FALSE | 0 | – | – | – | never |
| M1 | FALSE | 0 | – | – | – | never |
| **M2** | FALSE | **34** | 34 | 0 | **100.0%** | sound left-cycle catches |
| **M3** | FALSE | **42** | 42 | 0 | **100.0%** | sound right-cycle catches |
| **M4** | FALSE | **14** | 14 | 0 | **100.0%** | sound spike-zero catches |
| M6 | FALSE | 0 | – | – | – | never |
| **M7** | FALSE | **1**  | 1  | 0  | **100.0%** | 1 sound right-neg |
| D8 | FALSE | 0 | – | – | – | never |
| T1 | TRUE  | 0 | – | – | – | never |
| T3 | TRUE  | 0 | – | – | – | never |
| **T4** | TRUE  | **1** | 1 | 0 | **100.0%** | 1 collapsing-Eq1 |
| **F1**  | FALSE | **36**  | 26  | 10 | **72.2%** | mostly works |
| **B1**  | FALSE | **13**  | 5   | 8  | **38.5%** | below chance |
| **B2a** | TRUE  | **203** | 138 | 65 | **68.0%** | workhorse, biggest leak |
| **B2b** | TRUE  | **30**  | 24  | 6  | **80.0%** | solid TRUE shortcut |
| **B2c** | FALSE | **26**  | 12  | 14 | **46.2%** | below chance |

Confusion matrix:

|             | pred TRUE | pred FALSE |
|---          |---:|---:|
| gold TRUE   | 163 | 32 |
| gold FALSE  | 71  | 134 |

- TRUE  precision 69.7% / recall 83.6%
- FALSE precision 80.7% / recall 65.4%

---

## 3. What this tells us

**The witness layer is dead on extra-hard.** All 9 small magmas (L1, L2, L3, M1, M2, M3, M4, M6, M7) and the spine rule D8 fire **zero** times. Curators selected pairs where 2- and 3-element witnesses cannot separate Eq1 from Eq2. The TRUE shortcuts T1/T3/T4 also never fire — no `x=x`, `x=y`, or LHS-bare-with-disjoint-vars problems made the cut.

**The structural defaults invert on extra-hard.**

| rule | proxy hard tier | extra-hard |
|---|---:|---:|
| F1  | strong FALSE signal | 65/65 are gold-TRUE — flipped |
| B2a | reasonable TRUE prior | 100/112 are gold-FALSE — flipped |
| B2c | weak FALSE prior | 16/16 are gold-TRUE — flipped |

The 65 + 100 + 16 = 181 problems where these three rules fire all become wrong, dragging accuracy below random.

**Hard3 looks like the regime v10b was built for.** M2/M3/M4/M7/T4 fire 92 times at 100% precision. F1 and B2a perform within the bands they hit on the n=50 hard proxy. The leakage on B1 (38.5%) and B2c (46.2%) suggests the structural-default branch is the most fragile across distributions.

**Practical takeaway.** v10b is a *proxy-tuned cheatsheet*. Its accuracy depends entirely on whether the input distribution matches the calibration set:
- Witness-firable distributions → strong (the 100%-precision rules carry).
- Witness-empty distributions → only B2a/B2b/B2c/F1 are left, and those swing wildly with the dataset's TRUE/FALSE-by-shape priors.

If a future benchmark resembles `evaluation_extra_hard`, v10b cannot help — the rules either don't fire or fire with inverted polarity. Improving on extra-hard requires either (a) larger / different witnesses that *do* separate these pairs, or (b) different structural priors than M / S / V.

---

## 4. How to run programmatic checks yourself

### 4.1 What "programmatic" means here

The v10b cheatsheet is a cascade of rules. Each rule is decidable in code:
- **L1–L3, M1–M7**: "does small magma X satisfy Eq1 but refute Eq2?" — a finite computation over a 2- or 3-element op-table.
- **D8**: spine-divisibility check on the parse tree.
- **T1/T3/T4**: parse-feature predicates (LHS bare, RHS vars, etc.).
- **F1**: variable count.
- **B1/B2a/B2b/B2c**: structural defaults derived from M (min total var occurrences), S (LHS op count), V (LHS distinct vars).

Running the cascade in code gives you the **ceiling**: accuracy if a model executes the rules with zero error. Real LLM accuracy is always at or below this number.

### 4.2 Minimum viable script

The runner is `analysis/eval_v10b_on_eval_extra_hard.py`. It accepts a JSONL filename in `data/sair_eval/` as its argument:

```bash
# extra-hard (the default)
python3 analysis/eval_v10b_on_eval_extra_hard.py

# any other split — pass the basename
python3 analysis/eval_v10b_on_eval_extra_hard.py hard3.jsonl
python3 analysis/eval_v10b_on_eval_extra_hard.py evaluation_hard.jsonl
python3 analysis/eval_v10b_on_eval_extra_hard.py evaluation_normal.jsonl
```

Each run writes `data/sair_eval/v10b_<stem>_rule_breakdown.json` with one row per problem (`id`, `eq1_id`, `eq2_id`, `gold`, `rule`, `pred`, `correct`).

### 4.3 Downloading a HuggingFace SAIR split

Splits live at `https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems/resolve/main/data/<split>.jsonl`. Drop them into `data/sair_eval/`:

```bash
mkdir -p data/sair_eval
curl -sL https://huggingface.co/datasets/SAIRfoundation/equational-theories-selected-problems/resolve/main/data/<split>.jsonl \
     -o data/sair_eval/<split>.jsonl
```

Available splits (as of 2026-04-30): `normal`, `hard`, `hard1`, `hard2`, `hard3`, `evaluation_normal`, `evaluation_hard`, `evaluation_extra_hard`, `evaluation_order5`.

Each row has `id`, `index`, `difficulty`, `eq1_id`, `eq2_id`, `equation1`, `equation2`, `answer` (boolean).

### 4.4 ID alignment with `data/equations.txt`

The HuggingFace `eq1_id` / `eq2_id` are **1-indexed line numbers into our `data/equations.txt`** (4694 equations). The `*` operator in HuggingFace strings and the `◇` operator in our text file are equivalent — both parsers (`analysis/parse_equation.py`) normalize them. We verified this on a sample (eq1_id 1487 → line 1487 of `equations.txt`, matching equation strings). No remapping needed.

### 4.5 What the script does, in pieces

```python
# 1. Load all 4694 equations and their parse trees.
eqs_raw = parse_all_equations("data/equations.txt")
parsed  = [parse_equation(e["raw"]) for e in eqs_raw]

# 2. For each of the 9 small witness magmas, compute a satisfaction vector:
#    sat[i] = True iff equation i+1 holds in this magma.
compiled = [compile_equation(e["lhs"], e["rhs"]) for e in eqs_raw]
sat_vecs = {name: satisfaction_vector(MAGMA_TABLE, compiled)
            for name, MAGMA_TABLE in V5_MAGMAS.items()}

# 3. mask[i,j] = sat[i] & ~sat[j]  (sound FALSE witness for Eq_{i+1} ⇒ Eq_{j+1}).
magma_masks = {name: sat_vecs[name][:, None] & ~sat_vecs[name][None, :]
               for name in MAGMA_ORDER}

# 4. For each problem, walk the v10b cascade in fixed order:
#    L1 → L2 → L3 → M1 → M2 → M3 → M4 → M6 → M7 → D8 →
#    T1 → T3 → T4 → F1 → B1/B2a/B2b/B2c
def programmatic_v10b_rule(magma_hits, p1, p2):
    for name in MAGMA_ORDER:
        if magma_hits[name]: return name
    if d8_fires(p1, p2): return "D8"
    if t1_fires(p2):     return "T1"
    if t3_fires(p1):     return "T3"
    if t4_fires(p1):     return "T4"
    if f1_fires(p1):     return "F1"
    return b_rule(p1)    # B1 / B2a / B2b / B2c
```

Predicted verdict: TRUE iff the firing rule is in `{T1, T3, T4, B2a, B2b}`.

### 4.6 Running on a different cheatsheet

If you want to test, say, v11 or a custom variant:

1. Copy `analysis/rule_breakdown_v10b.py` (the n=50 proxy version) or the new `eval_v10b_on_eval_extra_hard.py`.
2. Edit `MAGMA_ORDER` / `V5_MAGMAS` to match the new sheet's witness bank.
3. Edit `programmatic_v10b_rule()` to reflect the new cascade order and any new TRUE/FALSE rules.
4. Edit `V10B_TRUE_RULES` (the set of names whose verdict is TRUE) so the predicted-truth lookup stays correct.

The parser, magma engine (`analysis/magma_counterexamples.py`), and equation-id alignment all stay the same.

### 4.7 Sanity checks before trusting a programmatic number

- **Always-TRUE / always-FALSE baseline**: 50% on a balanced split. Anything below ~55% means rules are firing with inverted polarity for that distribution; report it as such instead of saying the cheatsheet is "broken."
- **Compare to model accuracy on the same split**: programmatic ceiling should be ≥ model accuracy. If it isn't, your rule implementation diverges from the prompt text.
- **Check rule-firing counts**: rules with 0 firings are dead in this distribution and contribute no signal. Rules with 100% precision but tiny `n` are scaffolding worth keeping — see `memory/feedback_rules_as_scaffolding.md` (a logically redundant rule can still be load-bearing for the LLM).

---

## 5. Files of record

- Script: `analysis/eval_v10b_on_eval_extra_hard.py`
- Data: `data/sair_eval/evaluation_extra_hard.jsonl`, `data/sair_eval/hard3.jsonl`
- Per-problem rows:
  - `data/sair_eval/v10b_evaluation_extra_hard_rule_breakdown.json`
  - `data/sair_eval/v10b_hard3_rule_breakdown.json`
- Cheatsheet: `cheatsheets/bank_lookup_v10b.txt`
- Parser: `analysis/parse_equation.py`
- Magma engine: `analysis/magma_counterexamples.py`
- Reference proxy script: `analysis/rule_breakdown_v10b.py`
