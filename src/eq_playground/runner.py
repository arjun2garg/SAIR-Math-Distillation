"""Async evaluation orchestrator."""

from __future__ import annotations

import asyncio
import traceback

from tqdm import tqdm

from .cheatsheet import render
from .config import RunConfig
from .llm import call_llm
from .metrics import ProblemResult
from .parser import parse_answer
from .problems import Problem


async def evaluate_one(
    problem: Problem,
    template: str,
    config: RunConfig,
    semaphore: asyncio.Semaphore,
) -> ProblemResult:
    """Evaluate a single problem."""
    prompt = render(template, problem.equation1, problem.equation2)

    async with semaphore:
        try:
            response = await call_llm(prompt, config)
        except Exception as e:
            return ProblemResult(
                problem_id=problem.id,
                equation1=problem.equation1,
                equation2=problem.equation2,
                gold_answer=problem.answer,
                predicted_answer=None,
                correct=False if problem.answer is not None else None,
                parse_method="error",
                raw_response=f"ERROR: {e}\n{traceback.format_exc()}",
            )

    parsed = parse_answer(response.text)
    if problem.answer is None:
        correct = None
    else:
        correct = parsed.answer is not None and parsed.answer == problem.answer

    return ProblemResult(
        problem_id=problem.id,
        equation1=problem.equation1,
        equation2=problem.equation2,
        gold_answer=problem.answer,
        predicted_answer=parsed.answer,
        correct=correct,
        parse_method=parsed.method,
        raw_response=response.text,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        cost_usd=response.cost,
        latency_s=response.latency_s,
    )


async def run_evaluation(
    config: RunConfig,
    problems: list[Problem],
    template: str,
    verbose: bool = False,
) -> list[ProblemResult]:
    """Run the full evaluation loop with concurrent API calls."""
    semaphore = asyncio.Semaphore(config.concurrency)

    tasks = [
        evaluate_one(problem, template, config, semaphore)
        for problem in problems
    ]

    results: list[ProblemResult] = []
    with tqdm(total=len(tasks), desc="Evaluating", unit="problem") as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            pbar.update(1)

            if verbose:
                if result.correct is None:
                    status = "UNKNOWN"
                elif result.correct:
                    status = "CORRECT"
                elif result.predicted_answer is None:
                    status = "UNPARSED"
                else:
                    status = "WRONG"
                gold_str = "hidden" if result.gold_answer is None else str(result.gold_answer)
                tqdm.write(
                    f"  [{result.problem_id}] gold={gold_str} "
                    f"pred={result.predicted_answer} -> {status}"
                )

    # Sort results by problem ID for consistent output
    results.sort(key=lambda r: r.problem_id)
    return results
