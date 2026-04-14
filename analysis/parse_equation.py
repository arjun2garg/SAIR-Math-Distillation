"""Equation parser and feature extraction for magma equational laws.

Parses equations like "x ◇ (y ◇ x) = x" into structured representations
and computes syntactic features used for implication prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


# ---------------------------------------------------------------------------
# Parse tree types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Var:
    name: str

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Op:
    left: Node
    right: Node

    def __repr__(self) -> str:
        return f"({self.left!r} ◇ {self.right!r})"


Node = Union[Var, Op]


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _tokenize(s: str) -> list[str]:
    """Tokenize an equation string into a list of tokens.

    Handles both ◇ and * as the binary operator, normalizing to 'OP'.
    """
    # Normalize operator symbols
    s = s.replace("◇", " OP ").replace("*", " OP ")
    s = s.replace("(", " ( ").replace(")", " ) ").replace("=", " = ")
    return [tok for tok in s.split() if tok]


# ---------------------------------------------------------------------------
# Recursive-descent parser
# ---------------------------------------------------------------------------

class _Parser:
    """Parse a token stream into an expression tree.

    Grammar (left-associative):
        expr  := atom (OP atom)*
        atom  := VAR | '(' expr ')'
    """

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected: str | None = None) -> str:
        tok = self.tokens[self.pos]
        if expected is not None and tok != expected:
            raise ValueError(
                f"Expected '{expected}', got '{tok}' at pos {self.pos} "
                f"in {self.tokens}"
            )
        self.pos += 1
        return tok

    def parse_expr(self) -> Node:
        node = self.parse_atom()
        while self.peek() == "OP":
            self.consume("OP")
            right = self.parse_atom()
            node = Op(node, right)
        return node

    def parse_atom(self) -> Node:
        tok = self.peek()
        if tok == "(":
            self.consume("(")
            node = self.parse_expr()
            self.consume(")")
            return node
        else:
            name = self.consume()
            return Var(name)


def parse_expr(s: str) -> Node:
    """Parse a single expression string into a tree."""
    tokens = _tokenize(s)
    p = _Parser(tokens)
    node = p.parse_expr()
    if p.pos != len(tokens):
        raise ValueError(f"Unexpected tokens after pos {p.pos}: {tokens[p.pos:]}")
    return node


# ---------------------------------------------------------------------------
# Tree utilities
# ---------------------------------------------------------------------------

def _collect_vars(node: Node) -> set[str]:
    if isinstance(node, Var):
        return {node.name}
    return _collect_vars(node.left) | _collect_vars(node.right)


def _count_ops(node: Node) -> int:
    if isinstance(node, Var):
        return 0
    return 1 + _count_ops(node.left) + _count_ops(node.right)


def _depth(node: Node) -> int:
    if isinstance(node, Var):
        return 0
    return 1 + max(_depth(node.left), _depth(node.right))


def _tree_shape(node: Node) -> str:
    """Shape string with variables replaced by '_'."""
    if isinstance(node, Var):
        return "_"
    return f"({_tree_shape(node.left)},{_tree_shape(node.right)})"


def _canonical_vars(node: Node) -> tuple[Node, dict[str, str]]:
    """Rename variables by order of first appearance (left-to-right DFS)."""
    mapping: dict[str, str] = {}
    counter = [0]
    var_names = "xyzwuv" + "abcdefghijklmnopqrst"

    def _collect_order(n: Node) -> None:
        if isinstance(n, Var):
            if n.name not in mapping:
                mapping[n.name] = var_names[counter[0]]
                counter[0] += 1
        else:
            _collect_order(n.left)
            _collect_order(n.right)

    def _rename(n: Node) -> Node:
        if isinstance(n, Var):
            return Var(mapping[n.name])
        return Op(_rename(n.left), _rename(n.right))

    _collect_order(node)
    return _rename(node), mapping


def canonical_form(lhs: Node, rhs: Node) -> str:
    """Canonical string representation of an equation (up to variable renaming).

    Variables are renamed by first appearance order scanning LHS then RHS.
    """
    mapping: dict[str, str] = {}
    counter = [0]
    var_names = "xyzwuv" + "abcdefghijklmnopqrst"

    def _collect_order(n: Node) -> None:
        if isinstance(n, Var):
            if n.name not in mapping:
                mapping[n.name] = var_names[counter[0]]
                counter[0] += 1
        else:
            _collect_order(n.left)
            _collect_order(n.right)

    def _rename(n: Node) -> Node:
        if isinstance(n, Var):
            return Var(mapping[n.name])
        return Op(_rename(n.left), _rename(n.right))

    _collect_order(lhs)
    _collect_order(rhs)
    return f"{_rename(lhs)!r} = {_rename(rhs)!r}"


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def parse_equation(raw: str) -> dict:
    """Parse an equation string and extract all structural features.

    Args:
        raw: An equation string like "x ◇ (y ◇ x) = x" or "x * (y * x) = x"

    Returns:
        Dictionary of features as specified in the experiment guide.
    """
    # Split on '=' — handle both ◇ and * notation
    # Need to be careful: split on ' = ' to avoid splitting inside expressions
    # But some equations might have '=' without spaces. Tokenize first.
    tokens = _tokenize(raw)

    # Find the '=' token
    eq_idx = tokens.index("=")
    lhs_tokens = tokens[:eq_idx]
    rhs_tokens = tokens[eq_idx + 1:]

    lhs_parser = _Parser(lhs_tokens)
    lhs = lhs_parser.parse_expr()
    if lhs_parser.pos != len(lhs_tokens):
        raise ValueError(f"LHS parse incomplete: {raw}")

    rhs_parser = _Parser(rhs_tokens)
    rhs = rhs_parser.parse_expr()
    if rhs_parser.pos != len(rhs_tokens):
        raise ValueError(f"RHS parse incomplete: {raw}")

    lhs_vars = _collect_vars(lhs)
    rhs_vars = _collect_vars(rhs)
    n_ops_lhs = _count_ops(lhs)
    n_ops_rhs = _count_ops(rhs)
    depth_lhs = _depth(lhs)
    depth_rhs = _depth(rhs)

    is_trivial = (isinstance(lhs, Var) and isinstance(rhs, Var)
                  and lhs.name == rhs.name)
    is_singleton = (isinstance(lhs, Var) and isinstance(rhs, Var)
                    and lhs.name != rhs.name)

    # Collapsing: a variable appears on only one side
    lhs_only = lhs_vars - rhs_vars
    rhs_only = rhs_vars - lhs_vars
    has_lhs_only_vars = len(lhs_only) > 0
    has_rhs_only_vars = len(rhs_only) > 0

    return {
        "raw": raw,
        "lhs": lhs,
        "rhs": rhs,
        "lhs_vars": lhs_vars,
        "rhs_vars": rhs_vars,
        "lhs_only_vars": lhs_only,
        "rhs_only_vars": rhs_only,
        "shared_vars": lhs_vars & rhs_vars,
        "n_ops_lhs": n_ops_lhs,
        "n_ops_rhs": n_ops_rhs,
        "depth_lhs": depth_lhs,
        "depth_rhs": depth_rhs,
        "total_ops": n_ops_lhs + n_ops_rhs,
        "n_vars": len(lhs_vars | rhs_vars),
        "is_trivial": is_trivial,
        "is_singleton": is_singleton,
        "lhs_is_var": isinstance(lhs, Var),
        "rhs_is_var": isinstance(rhs, Var),
        "has_lhs_only_vars": has_lhs_only_vars,
        "has_rhs_only_vars": has_rhs_only_vars,
        "lhs_shape": _tree_shape(lhs),
        "rhs_shape": _tree_shape(rhs),
        "canonical": canonical_form(lhs, rhs),
    }


# ---------------------------------------------------------------------------
# Batch parsing
# ---------------------------------------------------------------------------

def parse_all_equations(path: str) -> list[dict]:
    """Parse all equations from a file. Returns 0-indexed list (index i = equation i+1)."""
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    return [parse_equation(line) for line in lines]


# ---------------------------------------------------------------------------
# Main: self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/equations.txt"
    equations = parse_all_equations(path)
    n = len(equations)
    print(f"Parsed {n} equations successfully.")

    # Spot checks
    eq1 = equations[0]
    assert eq1["is_trivial"], f"Eq1 should be trivial: {eq1['raw']}"
    assert eq1["total_ops"] == 0

    eq2 = equations[1]
    assert eq2["is_singleton"], f"Eq2 should be singleton: {eq2['raw']}"

    eq3 = equations[2]
    assert eq3["n_ops_lhs"] == 0 and eq3["n_ops_rhs"] == 1, f"Eq3 ops wrong: {eq3}"
    assert not eq3["rhs_is_var"]

    # Count equations by total_ops
    from collections import Counter
    ops_dist = Counter(eq["total_ops"] for eq in equations)
    print("Equations by total_ops:")
    for k in sorted(ops_dist):
        print(f"  {k} ops: {ops_dist[k]}")

    # Count low-order (<=2 ops)
    low_order = sum(v for k, v in ops_dist.items() if k <= 2)
    print(f"Equations with ≤2 ops (landmarks): {low_order}")

    # Check some features
    print(f"\nEq1: {eq1['raw']} -> trivial={eq1['is_trivial']}, ops={eq1['total_ops']}")
    print(f"Eq2: {eq2['raw']} -> singleton={eq2['is_singleton']}, ops={eq2['total_ops']}")
    print(f"Eq3: {eq3['raw']} -> lhs_is_var={eq3['lhs_is_var']}, rhs_is_var={eq3['rhs_is_var']}, "
          f"ops_lhs={eq3['n_ops_lhs']}, ops_rhs={eq3['n_ops_rhs']}")

    # Check a later equation with ops on both sides
    eq43 = equations[42]  # x ◇ y = y ◇ x (commutativity)
    print(f"Eq43: {eq43['raw']} -> canonical={eq43['canonical']}, "
          f"n_vars={eq43['n_vars']}, total_ops={eq43['total_ops']}")

    # Check last equation
    eq_last = equations[-1]
    print(f"Eq{n}: {eq_last['raw']} -> n_vars={eq_last['n_vars']}, "
          f"total_ops={eq_last['total_ops']}, "
          f"has_lhs_only={eq_last['has_lhs_only_vars']}, "
          f"has_rhs_only={eq_last['has_rhs_only_vars']}")

    # Count collapsing equations
    collapsing = sum(1 for eq in equations if eq["has_lhs_only_vars"] or eq["has_rhs_only_vars"])
    print(f"\nEquations with variable mismatch (potential collapsing): {collapsing}")

    print("\nAll checks passed!")
