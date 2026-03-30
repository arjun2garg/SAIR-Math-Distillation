"""LLM API wrapper using litellm."""

from __future__ import annotations

import time
from dataclasses import dataclass

import litellm

from .config import RunConfig

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost: float
    latency_s: float


async def call_llm(prompt: str, config: RunConfig) -> LLMResponse:
    """Call an LLM via litellm and return the response with metadata."""
    start = time.monotonic()

    kwargs: dict = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base

    response = await litellm.acompletion(**kwargs)
    elapsed = time.monotonic() - start

    usage = response.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
    text = response.choices[0].message.content or ""

    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:
        cost = 0.0

    return LLMResponse(
        text=text,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cost=cost,
        latency_s=elapsed,
    )
