"""Load, validate, and render cheatsheet templates."""

from __future__ import annotations

import re
from pathlib import Path

MAX_CHEATSHEET_BYTES = 10240
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*equation[12]\s*\}\}")


def load_cheatsheet(path: Path) -> str:
    """Read cheatsheet file, validate size and placeholders."""
    raw = path.read_bytes()
    if len(raw) > MAX_CHEATSHEET_BYTES:
        raise ValueError(
            f"Cheatsheet is {len(raw)} bytes, exceeds {MAX_CHEATSHEET_BYTES} byte limit"
        )

    text = raw.decode("utf-8")

    if "{{ equation1 }}" not in text and "{{equation1}}" not in text:
        raise ValueError("Cheatsheet must contain {{ equation1 }} placeholder")
    if "{{ equation2 }}" not in text and "{{equation2}}" not in text:
        raise ValueError("Cheatsheet must contain {{ equation2 }} placeholder")

    return text


def render(template: str, equation1: str, equation2: str) -> str:
    """Substitute equation placeholders into the cheatsheet."""
    result = template
    result = re.sub(r"\{\{\s*equation1\s*\}\}", equation1, result)
    result = re.sub(r"\{\{\s*equation2\s*\}\}", equation2, result)
    return result


def cheatsheet_info(path: Path) -> dict:
    """Return metadata about a cheatsheet file."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    return {
        "path": str(path),
        "size_bytes": len(raw),
        "within_limit": len(raw) <= MAX_CHEATSHEET_BYTES,
        "has_eq1_placeholder": bool(re.search(r"\{\{\s*equation1\s*\}\}", text)),
        "has_eq2_placeholder": bool(re.search(r"\{\{\s*equation2\s*\}\}", text)),
    }
