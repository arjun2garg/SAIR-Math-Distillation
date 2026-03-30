"""Parse TRUE/FALSE answers from LLM responses."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParseResult:
    answer: bool | None  # None = unparsed
    method: str
    raw_match: str


# Pattern cascade — tried in order, first match wins
_PATTERNS = [
    ("answered_pattern", re.compile(r"Answered\s+(TRUE|FALSE)", re.IGNORECASE)),
    ("boxed_pattern", re.compile(r"\\boxed\{(TRUE|FALSE)\}", re.IGNORECASE)),
    ("standalone_pattern", re.compile(r"^\s*(TRUE|FALSE)\s*$", re.MULTILINE | re.IGNORECASE)),
]

# Fallback: last occurrence of TRUE/FALSE (excluding "TRUE OR" constructs)
_FALLBACK = re.compile(r"\b(TRUE|FALSE)\b", re.IGNORECASE)


def parse_answer(text: str) -> ParseResult:
    """Extract TRUE/FALSE from LLM output using a 4-pattern cascade."""
    for method_name, pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            value = match.group(1).upper()
            return ParseResult(
                answer=(value == "TRUE"),
                method=method_name,
                raw_match=match.group(0),
            )

    # Fallback: take the LAST occurrence
    matches = list(_FALLBACK.finditer(text))
    if matches:
        last = matches[-1]
        value = last.group(1).upper()
        return ParseResult(
            answer=(value == "TRUE"),
            method="fallback_last",
            raw_match=last.group(0),
        )

    return ParseResult(answer=None, method="none", raw_match="")
