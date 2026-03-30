# eq-playground

Local playground for the [SAIR Mathematics Distillation Challenge - Equational Theories](https://competition.sair.foundation/competitions/mathematics-distillation-challenge-equational-theories-stage1/overview).

Test cheatsheets against equational implication problems using the competition's allowed models.

## Quick Start

```bash
# Install
pip install -e .

# Download the ETP dataset (equations + outcomes matrix)
eq-playground download

# Validate your cheatsheet (no API calls)
eq-playground validate --cheatsheet cheatsheets/example.txt --equations data/equations.txt --outcomes data/outcomes.json

# Run evaluation
export OPENROUTER_API_KEY=sk-or-...
eq-playground run \
  --cheatsheet cheatsheets/example.txt \
  --equations data/equations.txt \
  --outcomes data/outcomes.json \
  --model gpt-oss-120b \
  --sample 20 \
  --seed 42 \
  --verbose
```

## Competition Models

| Alias | Full Model |
|-------|-----------|
| `gpt-oss-120b` | `openrouter/openai/gpt-oss-120b` |
| `llama-70b` | `openrouter/meta-llama/llama-3.3-70b-instruct` |
| `gemini-flash-lite` | `openrouter/google/gemini-3.1-flash-lite-preview` |
| `grok-fast` | `openrouter/x-ai/grok-4.1-fast` |

## Cheatsheet Format

Cheatsheets are plain text files (max 10KB) with `{{ equation1 }}` and `{{ equation2 }}` placeholders:

```
You are an expert in universal algebra...

Equation 1: {{ equation1 }}
Equation 2: {{ equation2 }}

Answered TRUE or Answered FALSE.
```

The LLM response is parsed for TRUE/FALSE using these patterns (in order):
1. `Answered TRUE/FALSE`
2. `\boxed{TRUE/FALSE}`
3. Standalone `TRUE`/`FALSE` on a line
4. Last occurrence of `TRUE`/`FALSE` (fallback)

## Commands

- `eq-playground run` — Run evaluation
- `eq-playground validate` — Dry run, print rendered prompt
- `eq-playground download` — Fetch ETP dataset
- `eq-playground report [files...]` — Display past results

## Problem Sources

**From ETP data** (recommended): Use `--equations` and `--outcomes` flags after running `download`.

**From JSON/CSV**: Use `--problems` flag with a file containing:
```json
[{"id": "1_2", "equation1": "x = x", "equation2": "x = y", "answer": false}]
```

## Metrics

Raw Accuracy, Effective Accuracy, F1, Bias, Parse Rate, Cost per Correct, Avg Time, and full confusion matrix (TP/FP/FN/TN/Unparsed).
