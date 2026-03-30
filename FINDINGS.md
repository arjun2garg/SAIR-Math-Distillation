# Equational Theories Challenge — Findings

## Problem Overview

Given two equations over a binary operation ◇ on a magma, determine if Equation 1 implies Equation 2 (i.e., every magma satisfying Eq1 must also satisfy Eq2). Training set is 38% TRUE / 62% FALSE.

---

## Experiment Log

### 2026-03-30 — Initial exploration with Llama-70B

Ran 6 experiments across 5 cheatsheet variants on the training set.

| Cheatsheet | n | Acc | F1 | Bias | Parse | Notes |
|---|---|---|---|---|---|---|
| example.txt | 10 | 0.70 | 0.00 | -0.30 | 100% | All FALSE predictions |
| v2_structured | 10 | 0.50 | 0.00 | -0.17 | 80% | Verbose → truncated responses |
| v3_concise | 10 | 0.70 | 0.67 | +0.30 | 100% | Looked promising at small n |
| v4_patterns | 10 | 0.60 | 0.40 | -0.08 | 90% | Pattern-matching heuristics |
| v3_concise | 20 | 0.30 | 0.30 | +0.30 | 100% | Collapsed — too many FPs |
| v5_hybrid | 20 | 0.50 | 0.00 | -0.24 | 90% | Back to FALSE bias |

---

## Key Findings

### 1. Llama-70B cannot do the algebra

The model never constructs valid counterexamples or derivations. Its reasoning is hand-wavy: "given the abstract nature of these equations…" followed by a guess. It cannot reliably perform the substitution and rewriting steps needed to prove or disprove implications.

### 2. Prompt wording controls bias, not accuracy

The cheatsheet primarily determines whether the model defaults to TRUE or FALSE when uncertain (which is almost always):
- **Generic/long prompts** → FALSE bias (high TN, zero TP, F1≈0)
- **Prompts hinting "lean TRUE"** → TRUE bias (catches TPs but many FPs)
- Neither approach produces reliable accuracy — just shifts the confusion matrix.

### 3. Longer prompts make things worse

More detailed instructions (v2_structured, v5_hybrid) led to:
- Truncated responses hitting the 4096 token limit
- Parse failures (model never reaches "Answered TRUE/FALSE")
- No accuracy improvement despite more guidance

Concise prompts consistently outperform verbose ones on parse rate.

### 4. Small samples are misleading

v3_concise appeared strong at n=10 (70% acc, 0.67 F1) but collapsed to 30% accuracy at n=20. Always validate on ≥20 problems before drawing conclusions.

### 5. Structural heuristic: "x = [no x on RHS]" → TRUE

When Eq1 has the form `x = f(y, z, ...)` where x does **not** appear on the right side, it forces all elements to be equal (since for any a, b: `a = f(...) = b`). This makes any Eq2 trivially satisfied → always TRUE.

This pattern accounted for 3 of 7 TRUE cases in the 20-problem sample. The model fails to apply this rule consistently despite being told about it.

### 6. The hard cases share the same Eq1 form

When both equations have the form `x = [expr containing x on RHS]`, distinguishing TRUE from FALSE requires genuine algebraic reasoning (constructing counterexample magmas or deriving Eq2 from Eq1). No simple structural signal separates them — this is where the model fails most.

---

## Cheatsheet Design Principles (so far)

- **Keep it short.** Under 800 bytes. The model loses focus with long prompts.
- **End with a clear format instruction.** "Answered TRUE or Answered FALSE" parses reliably.
- **Don't ask the model to construct counterexamples.** It can't do it and wastes tokens trying.
- **Heuristic rules work when they apply** but the model doesn't follow them reliably.
- **Bias is a dial, not a fix.** Tuning prompt wording shifts TP/FP tradeoff but doesn't improve overall accuracy.

---

## Open Questions

- Can we encode the "x not on RHS → TRUE" rule more forcefully so the model actually applies it?
- Are there other structural heuristics beyond the "forces all equal" pattern?
- Would a different model (gpt-oss-120b, grok-fast) handle the algebra better, or hit the same wall?
- Could we use the cheatsheet to provide pre-computed facts (e.g., known equivalence classes) rather than asking the model to reason?
- The competition allows 10KB cheatsheets — could we pack lookup tables or decision rules into that space?
