"""Build a closed-form + lookup cheatsheet for a weak LLM.

Insight (measured on training, 5000 problems):
  - Three closed-form 2-element-magma checks (left projection, right
    projection, constant) catch 78.4% of FALSE pairs with ZERO false
    positives on TRUE pairs.
  - The checks reduce to "read the leftmost variable letter, read the
    rightmost letter, decide is-bare-variable-vs-product" — all pure
    pattern recognition, no counting, no arithmetic.
  - The remaining 22% (672 pairs) have a flat Eq1 distribution; a small
    residual lookup table catches some additional recall.

Strategy
--------
Layer 1: trivial TRUE rules (T1 reflex, T2 renaming, T3 safe singleton)
Layer 2: three closed-form FALSE checks (left proj, right proj, const)
Layer 3: residual exact-pair lookup table mined from training-set FALSE
         pairs that survive Layer 2
Layer 4: default to TRUE (since Layer 2 has zero FP on TRUE pairs).

Reads only training data + magma bank metadata. Validation slices are
never touched.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EQUATIONS_PATH = DATA / "equations.txt"
TRAINING_PATH = DATA / "training" / "problems.json"
OUTPUT_PATH = ROOT / "cheatsheets" / "bank_lookup_v3.txt"

OP = "◇"
RESIDUAL_ENTRIES = 27

# ---------------------------------------------------------------------------
# Closed-form predicates (must match the cheatsheet text exactly)
# ---------------------------------------------------------------------------


def lhs_rhs(eq: str) -> tuple[str, str]:
    a, b = eq.split("=")
    return a.strip(), b.strip()


def first_letter(s: str) -> str | None:
    for c in s:
        if c.isalpha():
            return c
    return None


def last_letter(s: str) -> str | None:
    for c in reversed(s):
        if c.isalpha():
            return c
    return None


def is_bare_var(s: str) -> bool:
    s = s.strip()
    return len(s) == 1 and s.isalpha()


def left_proj_holds(eq: str) -> bool:
    L, R = lhs_rhs(eq)
    return first_letter(L) == first_letter(R)


def right_proj_holds(eq: str) -> bool:
    L, R = lhs_rhs(eq)
    return last_letter(L) == last_letter(R)


def const_holds(eq: str) -> bool:
    """In a constant magma a◇b=c, every product evaluates to c, every bare
    variable evaluates to its assignment. Equation holds iff both sides
    are bare and identical, OR both sides are non-bare products."""
    L, R = lhs_rhs(eq)
    bL, bR = is_bare_var(L), is_bare_var(R)
    if bL and bR:
        return L == R
    if (not bL) and (not bR):
        return True
    return False


def closed_form_caught(e1: str, e2: str) -> str | None:
    if left_proj_holds(e1) and not left_proj_holds(e2):
        return "L1"
    if right_proj_holds(e1) and not right_proj_holds(e2):
        return "L2"
    if const_holds(e1) and not const_holds(e2):
        return "L3"
    return None


# ---------------------------------------------------------------------------
# Variable canonicalization
# ---------------------------------------------------------------------------


def canonicalize(eq: str) -> str:
    seen: dict[str, str] = {}
    out: list[str] = []
    i = 0
    letters = ["x", "y", "z", "w", "u", "t", "s", "r"]
    while i < len(eq):
        c = eq[i]
        if c.isalpha():
            j = i
            while j < len(eq) and eq[j].isalpha():
                j += 1
            name = eq[i:j]
            if name not in seen:
                idx = len(seen)
                seen[name] = letters[idx] if idx < len(letters) else f"v{idx}"
            out.append(seen[name])
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("Loading...")
    equations = EQUATIONS_PATH.read_text().splitlines()
    training = json.loads(TRAINING_PATH.read_text())

    # Sanity: closed-form precision on training
    true_pairs = []
    false_pairs = []
    for p in training:
        e1 = equations[p["eq1_id"] - 1]
        e2 = equations[p["eq2_id"] - 1]
        if p["answer"]:
            true_pairs.append((e1, e2))
        else:
            false_pairs.append((e1, e2))

    fp_on_true = sum(1 for e1, e2 in true_pairs if closed_form_caught(e1, e2))
    caught_false = sum(1 for e1, e2 in false_pairs if closed_form_caught(e1, e2))
    print(
        f"Training stats: {len(true_pairs)} TRUE / {len(false_pairs)} FALSE; "
        f"closed-form FP on TRUE = {fp_on_true}, caught FALSE = {caught_false} "
        f"({caught_false / len(false_pairs):.1%})"
    )
    assert fp_on_true == 0, "Closed forms must be sound"

    # Residual: FALSE pairs not caught by closed forms.
    uncaught = [(e1, e2) for e1, e2 in false_pairs if not closed_form_caught(e1, e2)]
    print(f"Uncaught FALSE (residual lookup target): {len(uncaught)}")

    # Cluster residual by canonical Eq1; for each, list canonical Eq2s.
    by_eq1: dict[str, list[str]] = defaultdict(list)
    for e1, e2 in uncaught:
        c1 = canonicalize(e1)
        c2 = canonicalize(e2)
        if c2 not in by_eq1[c1]:
            by_eq1[c1].append(c2)

    # Sort by total Eq2 count (coverage).
    ranked = sorted(by_eq1.items(), key=lambda kv: -len(kv[1]))
    selected = ranked[:RESIDUAL_ENTRIES]
    covered = sum(len(v) for _, v in selected)
    print(
        f"Selected {len(selected)} residual entries covering {covered} "
        f"distinct (Eq1, Eq2) skeletons"
    )

    # ----- Compose cheatsheet -----
    out: list[str] = []
    out.append(
        f"Decide whether Eq1 implies Eq2 over all magmas (set + binary op {OP}).\n"
        "Do NOT assume associativity, commutativity, or any algebraic law.\n"
        "\n"
        f"Eq1: {{{{ equation1 }}}}\n"
        f"Eq2: {{{{ equation2 }}}}\n"
        "\n"
        "Apply rules in order. First match wins.\n"
        "\n"
        "Definitions:\n"
        "  leftmost(s)  = first variable letter in s, reading left to right\n"
        "  rightmost(s) = last variable letter in s\n"
        "  bare(s)      = TRUE iff s is a single variable letter (no ops)\n"
        "  parity(s,v)  = number of times variable v appears in s, mod 2\n"
        f"  left-spine(s)  = walk root → left child → left child …; record the\n"
        f"                   leftmost variable letter and the number of {OP} nodes\n"
        "                   passed through\n"
        "  right-spine(s) = same on the right\n"
        "\n"
        f"L1. leftmost(Eq1.L) = leftmost(Eq1.R) AND leftmost(Eq2.L) ≠ leftmost(Eq2.R)\n"
        "    → FALSE.\n"
        "\n"
        f"L2. rightmost(Eq1.L) = rightmost(Eq1.R) AND rightmost(Eq2.L) ≠ rightmost(Eq2.R)\n"
        "    → FALSE.\n"
        "\n"
        "L3. Let cf(eq) = (both sides non-bare) OR (both sides the same single\n"
        "    variable letter). cf(Eq1) AND NOT cf(Eq2) → FALSE.\n"
        "\n"
        "T1. Eq2's two sides are identical (e.g. 'x = x') → TRUE.\n"
        "\n"
        "T2. Eq1 and Eq2 are the same equation up to renaming variables → TRUE.\n"
        "    Check: rename the first variable seen to 'x', the next new one\n"
        "    to 'y', then 'z','w'. If both renormalize to the same string, fire.\n"
        "\n"
        "T3. Eq1's LHS is a single variable letter L AND L does NOT occur\n"
        "    anywhere in Eq1's RHS → TRUE.\n"
        f"    OK examples: 'x = y', 'x = y {OP} z', 'x = (y {OP} z) {OP} (w {OP} u)'.\n"
        "    DO NOT fire T3 if L appears in RHS. Unsafe patterns:\n"
        f"        x = x {OP} y           x = (x {OP} y) {OP} z\n"
        f"        x = y {OP} (z {OP} x)     x = (y {OP} z) {OP} (w {OP} x)\n"
        f"        x = x {OP} (y {OP} z)     x = (y {OP} (x {OP} z)) {OP} y\n"
        "\n"
        "R-LOOKUP. Normalize Eq1 (rename first var seen to 'x', next 'y', then\n"
        "    'z','w','u'). Normalize Eq2 the SAME way INDEPENDENTLY (Eq2 also\n"
        "    starts naming from 'x'). If normalized Eq1 matches an entry's\n"
        "    'Eq1:' line below AND normalized Eq2 matches one of its 'Eq2\n"
        "    forms:' lines → FALSE.\n"
        "\n"
    )

    for k, (skel_e1, skel_e2_list) in enumerate(selected, 1):
        out.append(f"R{k}.\n")
        out.append(f"  Eq1: {skel_e1}\n")
        out.append("  Eq2 forms (any of these → FALSE):\n")
        for s in skel_e2_list:
            out.append(f"    {s}\n")
        out.append("\n")

    out.append(
        "D8. Eq1's RHS is a pure left-spine (every ◇ nests in its left child)\n"
        "    of depth n. Eq2's RHS is also a pure left-spine, of depth m.\n"
        "    n does not divide m → FALSE.\n"
        "\n"
        "D10. Eq1's LHS is a product or deeper expression (not a single\n"
        "     variable) AND Eq2's LHS is a single variable letter → FALSE.\n"
        "\n"
        f"M1. PARITY (witness magma a {OP} b = a + b mod 2). For each variable v\n"
        "    in Eq1, parity(Eq1.L, v) = parity(Eq1.R, v). For some variable w\n"
        "    in Eq2, parity(Eq2.L, w) ≠ parity(Eq2.R, w). → FALSE.\n"
        "\n"
        f"M2. LEFT CYCLE (witness magma a {OP} b = a + 1 mod 3). Compute\n"
        "    left-spine of each side: leftmost variable letter + (number of\n"
        f"    {OP} nodes on the left spine) mod 3.\n"
        "    Eq1 holds iff left-spine(Eq1.L) and left-spine(Eq1.R) have the\n"
        "    same letter AND the same count mod 3.\n"
        "    IF left-spine(Eq1.L) = left-spine(Eq1.R) (mod 3)\n"
        "    AND left-spine(Eq2.L) ≠ left-spine(Eq2.R) (mod 3) → FALSE.\n"
        "\n"
        f"M3. RIGHT CYCLE (witness magma a {OP} b = b + 1 mod 3). Mirror of M2\n"
        "    using right-spine.\n"
        "\n"
        "M4. SPIKE-ZERO (witness magma on {0,1,2}: 0◇1 = 2, every other\n"
        "    product = 0). Almost every term evaluates to 0; a term is\n"
        "    nonzero only when it contains the literal subterm (a ◇ b)\n"
        "    where the LLM can verify a = 0 and b = 1.\n"
        "    IF Eq1's two sides both reduce to 0 in this magma (no spike\n"
        "    triggers on either side under any assignment),\n"
        "    AND Eq2 has a subterm shape that triggers the spike on one\n"
        "    side but not the other → FALSE.\n"
        "\n"
        "M5. CONSERVATIVE 3-ELT SEARCH. Build a 3×3 table M on {0,1,2} with\n"
        "    M[i,i] free for i ∈ {0,1,2} and the off-diagonal cell M[i,j]\n"
        "    constrained to {i, j}. Try assignments of Eq1's variables to\n"
        "    {0,1,2}; whenever Eq1 forces a single unknown cell to a value,\n"
        "    write it in. Propagate. If a complete table is obtained where\n"
        "    Eq1 holds for ALL assignments AND Eq2 fails for SOME assignment\n"
        "    → FALSE. If a branch contradicts itself, try a different seed.\n"
        "\n"
        "D9. Eq1's LHS is a single variable letter AND Eq1 has 4 or more\n"
        "    distinct variables total → TRUE.\n"
        "\n"
        "D5. Eq1's RHS has the shape (A ◇ z) where z is a variable that\n"
        "    appears NOWHERE else in the whole equation, AND leftmost(A)\n"
        "    ≠ Eq1.LHS variable → TRUE.\n"
        "\n"
        "D5b. Eq1's RHS has the shape (z ◇ A) where z appears nowhere else\n"
        "    in the equation, AND rightmost(A) ≠ Eq1.LHS variable → TRUE.\n"
        "\n"
        "DEFAULT. If nothing above fires → TRUE.\n"
        "\n"
        "═══ Output — use EXACTLY these lines, no markdown ═══\n"
        "VERDICT: TRUE\n"
        "or\n"
        "VERDICT: FALSE\n"
        "RULE: <L1|L2|L3|T1|T2|T3|R<k>|D8|D10|M1|M2|M3|M4|M5|D9|D5|D5b|DEFAULT>\n"
    )

    OUTPUT_PATH.write_text("".join(out))
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(
        f"\nWrote {OUTPUT_PATH} ({size_kb:.1f} KB, {len(selected)} residual entries)"
    )

    # Estimate ceiling on training (assuming the LLM executes the rules
    # perfectly).
    correct = 0
    for e1, e2 in true_pairs:
        # T1
        cL2, cR2 = lhs_rhs(e2)
        if cL2 == cR2:
            correct += 1
            continue
        # T2
        if canonicalize(e1) == canonicalize(e2):
            correct += 1
            continue
        # T3
        L1, R1 = lhs_rhs(e1)
        if is_bare_var(L1) and L1 not in R1:
            correct += 1
            continue
        # Otherwise default TRUE
        correct += 1
    for e1, e2 in false_pairs:
        cL2, cR2 = lhs_rhs(e2)
        if cL2 == cR2:
            continue  # T1 wrongly fires
        if canonicalize(e1) == canonicalize(e2):
            continue
        L1, R1 = lhs_rhs(e1)
        if is_bare_var(L1) and L1 not in R1:
            continue
        if closed_form_caught(e1, e2):
            correct += 1
            continue
        # Residual lookup
        c1 = canonicalize(e1)
        c2 = canonicalize(e2)
        if c1 in dict(selected) and c2 in dict(selected)[c1]:
            correct += 1
            continue
        # Default TRUE → wrong on FALSE
    total = len(true_pairs) + len(false_pairs)
    print(f"Estimated training accuracy ceiling (perfect execution): {correct}/{total} = {correct/total:.4f}")


if __name__ == "__main__":
    main()
