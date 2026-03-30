"""Configuration loading and merging."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RunConfig:
    model: str = "openrouter/openai/gpt-oss-120b"
    temperature: float = 0.0
    max_tokens: int = 4096
    concurrency: int = 5
    output_dir: str = "results"
    api_base: str | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> RunConfig:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def override(self, **kwargs) -> RunConfig:
        """Return a new config with non-None kwargs overriding current values."""
        updates = {k: v for k, v in kwargs.items() if v is not None}
        return RunConfig(**{**self.__dict__, **updates})


# Competition-allowed models as convenient aliases
MODEL_ALIASES = {
    "gpt-oss-120b": "openrouter/openai/gpt-oss-120b",
    "llama-70b": "openrouter/meta-llama/llama-3.3-70b-instruct",
    "gemini-flash-lite": "openrouter/google/gemini-3.1-flash-lite-preview",
    "grok-fast": "openrouter/x-ai/grok-4.1-fast",
}


def resolve_model(model: str) -> str:
    """Resolve a model alias to a full litellm model string."""
    return MODEL_ALIASES.get(model, model)
