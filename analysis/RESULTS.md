# Programmatic cheatsheet evaluation — combined results

**Date:** 2026-04-30
**Method:** for each cheatsheet, the rules were transcribed into a deterministic Python cascade. Each cascade was then run on every HuggingFace SAIR split (practice + evaluation), plus the full 4694×4694 = **22,033,636-pair ETP cross-product** (ground truth from `data/full_etp_cache.pkl`). This measures the **ceiling** of each cheatsheet under perfect rule execution — real LLM accuracy will be at or below these numbers.

**Cheatsheets evaluated:** `aj`, `dufius`, `eucalyptus`, `pi`, `reza_jamei`, `arjun_garg`, `vt`, `yan-biao`. (`arjun_garg` = `cheatsheets/arjun_garg.txt`, the locked ship.)

**Code:** `analysis/_common.py` (shared utilities), `analysis/<cs>_checker.py` per cheatsheet, `analysis/aggregate.py`. Per-cheatsheet outputs in `analysis/results/<cs>/`.

---

## 1. Headline: overall accuracy by split

Always-TRUE / always-FALSE baselines:
- Full 22M ETP: **always-TRUE = 37.12%**, **always-FALSE = 62.88%** (gold has 8,178,279 TRUE / 22,033,636 total).
- HF practice/evaluation splits are roughly balanced ≈ 50/50 (always-pick = ~50%).

| split | n | aj | dufius | eucalyptus | pi | reza_jamei | arjun_garg | vt | yan-biao |
|-------|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| normal | 1000 | 97.10% | 84.80% | 74.30% | 68.10% | 97.30% | **98.70%** | 89.80% | 96.90% |
| hard | 200 | 60.50% | 67.00% | 63.00% | 49.50% | 61.00% | 65.00% | 55.50% | **72.00%** |
| hard1 | 69 | 59.42% | 69.57% | 65.22% | 46.38% | 65.22% | 68.12% | 53.62% | **72.46%** |
| hard2 | 200 | 78.00% | **92.50%** | 50.00% | 50.00% | 89.50% | 90.00% | 50.00% | 83.00% |
| hard3 | 400 | 79.50% | 73.25% | 51.50% | 86.00% | 74.75% | 74.25% | **86.50%** | 71.00% |
| evaluation_normal | 200 | 86.50% | 88.00% | 56.50% | 58.00% | **94.00%** | 93.00% | 64.50% | 82.50% |
| evaluation_hard | 200 | 91.00% | **92.50%** | 57.00% | 79.50% | 73.00% | 76.50% | 83.50% | 84.00% |
| evaluation_extra_hard | 200 | 84.50% | 65.00% | 50.00% | **97.50%** | 45.50% | 9.50% | **97.50%** | 54.50% |
| evaluation_order5 | 200 | **90.50%** | 80.00% | 70.50% | 68.50% | 86.00% | 89.50% | 77.00% | 88.50% |
| **full_etp** | **22,033,636** | 96.17% | 81.87% | 80.28% | 62.00% | 96.90% | **98.24%** | 90.57% | 97.09% |

### Per-cheatsheet at-a-glance

| cheatsheet | full ETP | best split | worst split | dominant rule on extra-hard |
|---|---:|---|---|---|
| **arjun_garg** | **98.24%** | normal 98.70% | extra-hard 9.50% | F1 (65/65 wrong) + B2a (100/112 wrong) |
| **yan-biao** | 97.09% | normal 96.90% | extra-hard 54.50% | DEFAULT_FALSE (191 fires, 100 right) |
| **reza_jamei** | 96.90% | normal 97.30% | extra-hard 45.50% | B2a TRUE (115 fires, 100 wrong) |
| **aj** | 96.17% | normal 97.10% | hard 60.50% | M7_knuth catches 69 FALSE pairs cleanly |
| **vt** | 90.57% | extra-hard 97.50% | hard1 53.62% | H3 100/100 + DEFAULT_TRUE 93/93 |
| **dufius** | 81.87% | hard2 92.50% | extra-hard 65.00% | C1 fires 47×, every one wrong |
| **eucalyptus** | 80.28% | normal 74.30% | extra-hard 50.00% | CLASSIFY_DEFAULT_FALSE absorbs 100 TRUE pairs as FN |
| **pi** | 62.00% | extra-hard 97.50% | hard1 46.38% | H3 100/100 + DEFAULT_TRUE 76/76 |

---

## 2. Findings worth noting

**(a) The "extra-hard" split inverts the usual ranking.** arjun_garg — best on the full ETP at 98.24% — scores **9.50%** on `evaluation_extra_hard`, worse than always-TRUE/always-FALSE. reza_jamei (96.9% full ETP) and yan-biao (97.1%) crater similarly at 45.5% and 54.5%. Conversely, `pi` (62% full ETP, ≈always-FALSE baseline) and `vt` (90.6% full ETP) tie at the top of `evaluation_extra_hard` (97.5%) — both rely on the heuristic `H3` catching 100/100 of that split's gold-FALSE pairs and `DEFAULT_TRUE` correctly absorbing the gold-TRUE residual. This is exactly the finding in `SAIR_HF_EVAL_FINDINGS.md` for arjun_garg, now confirmed across the cheatsheet bank.

**(b) The structural defaults invert.** arjun_garg's `B2a` (M=1 ∧ S=0 → TRUE) fires 112 times on extra-hard with 10.7% precision; the same rule is 92.5% precise on the full ETP. arjun_garg's `F1` (Eq1 has ≤2 vars → FALSE) fires 65 times on extra-hard with **0%** precision (all 65 are gold-TRUE). reza_jamei's `B2a` is 13.0% precise on extra-hard but 89.2% on hard3. dufius's `C1` (rhsVars=4 → TRUE) fires 47 times on extra-hard at 0% precision; on hard3 it's silent. The extra-hard curators picked pairs where every TRUE-leaning structural prior is wrong.

**(c) The witness layer is dead on extra-hard for every cheatsheet.** On `evaluation_extra_hard`:
- `arjun_garg`: all 9 small magmas (L1–M7) plus D8 fire **zero** times.
- `aj` (most witness-heavy, 57 magmas): only `M7_knuth` fires (69 catches, all correct).
- All others: their soundness-witnesses fire near-zero. Most predictions come from defaults / heuristics.

This generalizes the arjun_garg observation in `SAIR_HF_EVAL_FINDINGS.md` §3 to the full sheet bank.

**(d) The full-ETP ceiling is high — but partly always-FALSE in disguise.** The full ETP is 62.88% FALSE; pi at 62.00% is essentially the always-FALSE baseline. arjun_garg (98.24%), yan-biao (97.1%), reza_jamei (96.9%), aj (96.2%) genuinely beat the baseline by 33–35 pp; vt (90.6%) by ~28 pp; dufius (81.9%) and eucalyptus (80.3%) by ~17–19 pp.

---

## 3. Per-rule drivers on hard3 and evaluation_extra_hard

### `hard3` (n=400) — top contributing rules per cheatsheet (by correct count)

| cheatsheet | top 3 |
|---|---|
| aj | STEP8_DEFAULT_TRUE (195/277, 70.4%), M4_wraparound (34/34, 100%), Aff_3_2_4 (18/18, 100%) |
| dufius | B2a (66/74, 89.2%), C13 (34/47, 72.3%), B2c (24/38, 63.2%) |
| eucalyptus | CLASSIFY_DEFAULT_FALSE (174/368, 47.3%), T3_Z3_NEG (11/11, 100%), HARD_022 (7/7, 100%) |
| pi | DEFAULT_TRUE (184/236, 78.0%), A1 (42/42, 100%), A2 (33/33, 100%) |
| reza_jamei | B2a (144/217, 66.4%), W10 (42/42, 100%), W9 (33/33, 100%) |
| arjun_garg | B2a (138/203, 68.0%), M3 (42/42, 100%), M2 (34/34, 100%) |
| vt | DEFAULT_TRUE (183/228, 80.3%), A1 (42/42, 100%), A2 (33/33, 100%) |
| yan-biao | DEFAULT_FALSE (186/293, 63.5%), B2 (24/25, 96.0%), B3_LOOSE (23/27, 85.2%) |

### `evaluation_extra_hard` (n=200) — top wrong-firing rules

| cheatsheet | wrong-firing rules |
|---|---|
| aj | (no wrong-firers — magma rules 100% precise; all 31 wrong are STEP8_DEFAULT_TRUE absorbing FALSE pairs as TRUE) |
| dufius | C1 (47 wrong / 47 fires, 0%), B2c (16/16, 0%), B1 (7/7, 0%) |
| eucalyptus | CLASSIFY_DEFAULT_FALSE (100 wrong / 131 fires, 23.7%) |
| pi | H5 (3/3), H6 (2/2) — only 5 wrong-firings total |
| reza_jamei | B2a (100 wrong / 115 fires, 13.0%), B1 (7/7, 0%), B2d (2/2, 0%) |
| arjun_garg | B2a (100 wrong / 112 fires, 10.7%), F1 (65/65, 0%), B2c (16/16, 0%) |
| vt | H5 (3/3), H6 (2/2) — only 5 wrong-firings total |
| yan-biao | DEFAULT_FALSE (91 wrong / 191 fires, 52.4%) |

---

## 3a. What rules actually carry `evaluation_extra_hard`?

The pi/vt 97.5% on extra-hard and aj's 84.5% come from very different mechanisms. Looking at every rule that scored ≥1 correct verdict on `evaluation_extra_hard` and tracking it across other splits + the full 22M ETP reveals which rules **generalize** and which only **overfit** the curated split.

### pi/vt's top scorer: `H3` (heuristic FALSE)

`H3` (pi.txt / vt.txt): if Eq1 has a bare LHS, `kind = M` (mixed L/R path to bare var), `occ = 2`, and `RP(Eq1) = false` → predict FALSE.

| split | H3 fires | correct | precision |
|---|---:|---:|---:|
| **evaluation_extra_hard** | 100 | 100 | **100.0%** |
| evaluation_hard | 52 | 37 | 71.2% |
| hard3 | 8 | 8 | 100.0% (tiny n) |
| evaluation_normal | 24 | 4 | 16.7% |
| **full ETP** | **891,170** | **154,039** | **17.3%** |

H3 perfectly partitions the gold-FALSE half of `evaluation_extra_hard` and is actively misleading almost everywhere else. This is **rule-level overfitting**: the structural pattern characterizes extra-hard's curated FALSEs, but it isn't a sound algebraic argument, so on the broader equation universe it fires ~5× more often than it should.

### pi/vt's residual catcher: `DEFAULT_TRUE`

After H3 skims off all 100 gold-FALSEs, the remaining ~100 problems are exactly the gold-TRUEs that DEFAULT_TRUE absorbs cleanly. On the full ETP this rule is 31% precise — i.e. another overfit pattern.

| split | pi DEFAULT_TRUE | vt DEFAULT_TRUE |
|---|---|---|
| evaluation_extra_hard | 76/76 (100%) | 93/93 (100%) |
| hard3 | 184/236 (78%) | 183/228 (80%) |
| **full ETP** | **3.28M / 10.56M (31%)** | **3.15M / 4.00M (79%)** |

So pi+vt's 97.5% on extra-hard is the **product** of two tightly co-fit rules, neither of which generalizes. (vt's DEFAULT_TRUE generalizes better than pi's because vt has more upstream rules consuming the natural-distribution TRUEs.)

### aj's actually-sound winner: `M7_knuth` (Knuth central groupoid, order 4)

`(a,b)*(c,d) = (b,c)` over `S = {(0,0),(0,1),(1,0),(1,1)}`. Sound finite witness magma: if it satisfies Eq1 and refutes Eq2, FALSE is provably correct.

| split | n | M7 fires | % of split | correct | precision |
|---|---:|---:|---:|---:|---:|
| normal | 1,000 | 1 | 0.10% | 1 | 100% |
| hard | 200 | 19 | 9.50% | 19 | 100% |
| hard1 | 69 | 6 | 8.70% | 6 | 100% |
| hard2 | 200 | 6 | 3.00% | 6 | 100% |
| hard3 | 400 | 12 | 3.00% | 12 | 100% |
| evaluation_normal | 200 | 2 | 1.00% | 2 | 100% |
| evaluation_hard | 200 | 37 | 18.50% | 37 | 100% |
| **evaluation_extra_hard** | 200 | **69** | **34.50%** | **69** | **100%** |
| evaluation_order5 | 200 | 4 | 2.00% | 4 | 100% |
| **full_etp** | 22,033,636 | **37,132** | **0.169%** | 37,132 | **100%** |

**M7 is highly selective, and the curated splits selected *for* it.** On the natural full-ETP distribution, M7 fires on only 0.169% of the 22M pairs (37,132 catches), accounting for just 0.27% of all 13.86M gold-FALSE pairs. But on `evaluation_extra_hard` it fires on 34.5% of problems — a ~200× concentration. On `evaluation_hard` it's 18.5% (~110× concentration).

### eucalyptus's `HARD_*` blocks (targeted Cayley tables)

eucalyptus.txt ships specific tables keyed to specific Eq1 strings. Two of them carry on extra-hard:

| rule | extra_hard | full ETP |
|---|---:|---:|
| HARD_022 (table `[[0,2,1],[2,1,0],[1,0,2]]`) | 61/61 (100%) | 9,232/9,232 (100%) |
| HARD_014 (Z₃-add) | 8/8 (100%) | 9,232/9,232 (100%) |

Sound by construction; high precision everywhere. Limited reach (each fires <10K times across the full ETP) because the keying is by exact Eq1 string.

### arjun_garg / reza_jamei — the same rules that win on full ETP *invert* on extra-hard

| arjun_garg rule | full ETP | extra_hard |
|---|---:|---:|
| B2a (M=1, S=0 → TRUE) | 3.56M / 3.85M (**92%**) | 12 / 112 (**11%**) |
| F1 (≤2 vars → FALSE) | 506K / 527K (**96%**) | 0 / 65 (**0%**) |
| B2b (M=1, S=1, V=2 → TRUE) | 700K / 715K (**98%**) | 7 / 7 (100%) |

B2a and F1 are great structural priors on the natural distribution and worse than coin-flip on extra-hard, exactly because the curators selected *for* counterexamples to those priors. Same story for reza_jamei's B2a (86% full ETP, 13% extra-hard). 

Note: I (arjun_garg) got this cascade from the public reza_jamei cheat sheet, which is why it is the same.

### Summary: who carried extra-hard, and how it generalizes

| rule | extra-hard role | generalizes? |
|---|---|---|
| pi/vt **H3** | 100/100 (FALSE side) | No — 17% on full ETP, overfit |
| pi/vt **DEFAULT_TRUE** | 100/76, 100/93 (TRUE residual) | Partially — 31% (pi) / 79% (vt) on full ETP |
| aj **M7_knuth** | 69/69 (FALSE side) | **Yes — 100% always; sound witness** |
| eucalyptus **HARD_022/014** | 69/200 between them | **Yes — 100% always; sound but narrow keying** |
| arjun_garg/reza_jamei **B2a, F1** | inverted on extra-hard | Yes elsewhere — 92%/96% on full ETP |

---

## 4. How to read this

- **Sound rule = 100% precision.** Magma-witness rules (`Mn_*`, `Aff_*`, `T2_*`, `T3_*`, `W*`, `L1`/`L2`/`L3`, `K`, `X`, `D_SPINE_*`) are sound by construction: if a finite magma satisfies Eq1 and refutes Eq2, FALSE is provably correct. Anything below 100% on these would indicate a bug — none observed.
- **Structural / default rules carry the wrongness.** When you see <60% precision, it's almost always a default branch (B2a, B2d, DEFAULT_TRUE, DEFAULT_FALSE, CLASSIFY_DEFAULT_FALSE) or a structural heuristic (C1, F1, B1).
- **Programmatic ceiling ≠ LLM accuracy.** These numbers are upper bounds. A real LLM following the cheatsheet will be at or below — model error in rule execution can only subtract.

---

## 5. Files

- Shared utilities: `analysis/_common.py`
- Per-cheatsheet checker: `analysis/<cs>_checker.py`
- Aggregator: `analysis/aggregate.py`
- Per-cheatsheet results (incl. SUMMARY.md, per-split JSON, full_etp.json, summary.json): `analysis/results/<cs>/`
- Combined raw stats: `analysis/results/COMPARISON.json`
- This file: `analysis/RESULTS.md`

To re-run any cheatsheet: `python3 analysis/<cs>_checker.py`. Each script regenerates that cheatsheet's full result tree.

## 6. Caveats

- **eucalyptus**'s "Classification" step is intuition-only; it was collapsed into `CLASSIFY_DEFAULT_FALSE` per the cheatsheet's own "If uncertain, FALSE" hint. This drives most of eucalyptus's wrongness.
- **aj**'s Step 3 (bilinear matrix magmas), Step 4 (partial subterm algebra), and Step 5 (perturbation method) are not finite-Cayley-table primitives and were not implemented; M15 (S_3), M17 (truncated free), M19 (medial over Q), M20 ((N,+)) skipped. Step 1+6 + a small affine sweep gave 96.17% full ETP.
- **yan-biao**'s `B_SUB` (substitution unification) runs scalar on the small splits but is skipped (zero-mask) for the 22M ETP run — per-pair tree unification is intractable in numpy. `B3_LOOSE`'s "exactly one dirty slot" is approximated as ≤1.
- All other cheatsheets' rules are implemented faithfully.
