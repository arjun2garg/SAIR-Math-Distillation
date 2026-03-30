"""CLI entry point for eq-playground."""

from __future__ import annotations

import asyncio
import io
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen

import click
from dotenv import load_dotenv

from .cheatsheet import cheatsheet_info, load_cheatsheet, render
from .config import RunConfig, resolve_model
from .datasets import (
    download_training,
    download_validation,
    load_training_problems,
    load_validation_problems,
)
from .metrics import compute_metrics
from .problems import (
    generate_problems_from_etp,
    load_equations,
    load_outcomes,
    load_problems,
    select_problems,
)
from .report import load_and_print_report, print_metrics, save_results
from .runner import run_evaluation

load_dotenv()

DATA_DIR = Path("data")

EQUATIONS_URL = (
    "https://raw.githubusercontent.com/teorth/equational_theories/main/data/equations.txt"
)
OUTCOMES_URL = (
    "https://raw.githubusercontent.com/teorth/equational_theories/main/data/"
    "2024-11-10-outcomes.json.zip"
)


def parse_indices(s: str) -> list[int]:
    """Parse index spec like '0-99,150,200-210' into a list of ints."""
    indices = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            indices.extend(range(int(start), int(end) + 1))
        else:
            indices.append(int(part))
    return indices


@click.group()
def main():
    """eq-playground: Local playground for the SAIR Equational Theories Challenge."""
    pass


@main.command()
@click.option("--cheatsheet", required=True, type=click.Path(exists=True), help="Path to cheatsheet file")
@click.option("--problems", "problems_path", type=click.Path(exists=True), help="Path to problems JSON/CSV")
@click.option("--equations", "equations_path", type=click.Path(exists=True), help="Path to equations.txt")
@click.option("--outcomes", "outcomes_path", type=click.Path(exists=True), help="Path to outcomes.json")
@click.option("--model", default=None, help="Model name or alias")
@click.option("--temperature", type=float, default=None)
@click.option("--max-tokens", type=int, default=None)
@click.option("--concurrency", type=int, default=None)
@click.option("--indices", default=None, help="Problem indices (e.g., 0-99,150)")
@click.option("--sample", type=int, default=None, help="Random sample N problems")
@click.option("--seed", type=int, default=None, help="RNG seed for sampling")
@click.option("--difficulty", default=None)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="YAML config file")
@click.option("--csv", "write_csv", is_flag=True, help="Also write CSV output")
@click.option("--output-dir", default=None)
@click.option("--verbose", is_flag=True)
@click.option("--problem-set", "problem_set", type=click.Choice(["training", "validation"]),
              default=None, help="Use pre-built training or validation set")
@click.option("--data-dir", "run_data_dir", default="data", help="Data directory for problem sets")
def run(
    cheatsheet, problems_path, equations_path, outcomes_path, model,
    temperature, max_tokens, concurrency, indices, sample, seed,
    difficulty, config_path, write_csv, output_dir, verbose,
    problem_set, run_data_dir,
):
    """Run evaluation: cheatsheet + problems + model -> results."""
    # Load config
    cfg_path = Path(config_path) if config_path else Path("config/default.yaml")
    if cfg_path.exists():
        cfg = RunConfig.from_yaml(cfg_path)
    else:
        cfg = RunConfig()

    if model:
        model = resolve_model(model)
    cfg = cfg.override(
        model=model, temperature=temperature, max_tokens=max_tokens,
        concurrency=concurrency, output_dir=output_dir,
    )

    # Load cheatsheet
    cs_path = Path(cheatsheet)
    template = load_cheatsheet(cs_path)
    click.echo(f"Cheatsheet: {cs_path} ({len(template.encode())} bytes)")

    # Load problems
    hide_answers = False
    if problem_set:
        if problems_path or equations_path or outcomes_path:
            raise click.UsageError(
                "--problem-set is mutually exclusive with --problems, --equations, --outcomes"
            )
        ddir = Path(run_data_dir)
        if problem_set == "training":
            problems = load_training_problems(ddir)
            click.echo(f"Loaded {len(problems)} training problems")
        else:
            problems = load_validation_problems(ddir)
            hide_answers = True
            click.echo(f"Loaded {len(problems)} validation problems (answers hidden in output)")
    elif problems_path:
        problems = load_problems(Path(problems_path))
    elif equations_path and outcomes_path:
        equations = load_equations(Path(equations_path))
        outcomes = load_outcomes(Path(outcomes_path))
        problems = generate_problems_from_etp(equations, outcomes)
        click.echo(f"Generated {len(problems)} problems from ETP data")
    else:
        raise click.UsageError(
            "Provide --problem-set, --problems (JSON/CSV), or both --equations and --outcomes"
        )

    # Filter/sample
    idx_list = parse_indices(indices) if indices else None
    problems = select_problems(problems, indices=idx_list, sample_n=sample,
                               difficulty=difficulty, seed=seed)
    click.echo(f"Running {len(problems)} problems with model {cfg.model}")

    # Run
    results = asyncio.run(run_evaluation(cfg, problems, template, verbose=verbose))

    # Metrics
    metrics = compute_metrics(results)
    print_metrics(metrics)

    # Save
    out_dir = Path(cfg.output_dir)
    json_path = save_results(
        results, metrics, cfg, str(cs_path), template, out_dir,
        write_csv=write_csv, hide_answers=hide_answers,
    )
    click.echo(f"Results saved to {json_path}")


@main.command()
@click.option("--cheatsheet", required=True, type=click.Path(exists=True))
@click.option("--problems", "problems_path", type=click.Path(exists=True), default=None)
@click.option("--equations", "equations_path", type=click.Path(exists=True), default=None)
@click.option("--outcomes", "outcomes_path", type=click.Path(exists=True), default=None)
@click.option("--index", type=int, default=0, help="Problem index to render")
@click.option("--problem-set", "problem_set", type=click.Choice(["training", "validation"]),
              default=None, help="Use pre-built training or validation set")
@click.option("--data-dir", "val_data_dir", default="data", help="Data directory for problem sets")
def validate(cheatsheet, problems_path, equations_path, outcomes_path, index,
             problem_set, val_data_dir):
    """Dry run: render a problem with the cheatsheet and print the prompt."""
    template = load_cheatsheet(Path(cheatsheet))
    info = cheatsheet_info(Path(cheatsheet))

    click.echo("Cheatsheet info:")
    for k, v in info.items():
        click.echo(f"  {k}: {v}")

    # Load problems
    hide_answer = False
    if problem_set:
        ddir = Path(val_data_dir)
        if problem_set == "training":
            problems = load_training_problems(ddir)
        else:
            problems = load_validation_problems(ddir)
            hide_answer = True
    elif problems_path:
        problems = load_problems(Path(problems_path))
    elif equations_path and outcomes_path:
        equations = load_equations(Path(equations_path))
        outcomes = load_outcomes(Path(outcomes_path))
        problems = generate_problems_from_etp(equations, outcomes)
    else:
        click.echo("\nNo problems provided. Showing template with placeholders.")
        click.echo("\n--- RENDERED PROMPT ---")
        click.echo(render(template, "<equation1>", "<equation2>"))
        return

    if index >= len(problems):
        raise click.UsageError(f"Index {index} out of range (0-{len(problems)-1})")

    p = problems[index]
    prompt = render(template, p.equation1, p.equation2)

    answer_str = "hidden" if hide_answer else str(p.answer)
    click.echo(f"\nProblem [{p.id}]: answer={answer_str}")
    click.echo(f"  Eq1: {p.equation1}")
    click.echo(f"  Eq2: {p.equation2}")
    click.echo("\n--- RENDERED PROMPT ---")
    click.echo(prompt)
    click.echo("--- END ---")


@main.command()
@click.option("--data-dir", default="data", help="Directory to save data files")
@click.option("--validation", is_flag=True, help="Download validation set from HuggingFace")
@click.option("--training", is_flag=True, help="Download training set (HF hard + ETP sample)")
@click.option("--sample", "train_sample", type=int, default=5000,
              help="Training set sample size (default: 5000)")
@click.option("--seed", "train_seed", type=int, default=42,
              help="Training set RNG seed (default: 42)")
def download(data_dir, validation, training, train_sample, train_seed):
    """Download datasets. By default downloads ETP data. Use flags for train/val sets."""
    out = Path(data_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not validation and not training:
        # Default: download ETP data
        _download_etp(out)
        return

    if validation:
        click.echo("Downloading validation set from HuggingFace...")
        manifest = download_validation(out)
        click.echo(f"  Configs: {manifest['configs']}")
        click.echo(f"  Total: {manifest['total_problems']} problems")
        click.echo(f"  Saved to {out / 'validation'}/")

    if training:
        click.echo("Downloading training set...")
        eq_path = out / "equations.txt"
        outcomes_path = out / "outcomes.json"
        if not eq_path.exists() or not outcomes_path.exists():
            click.echo("  ETP data not found, downloading first...")
            _download_etp(out)
        equations = load_equations(eq_path)
        outcomes = load_outcomes(outcomes_path)
        count = download_training(
            out, equations, outcomes,
            sample_n=train_sample, seed=train_seed,
        )
        click.echo(f"  Generated {count} training problems")
        click.echo(f"  Saved to {out / 'training' / 'problems.json'}")


def _download_etp(out: Path) -> None:
    """Download ETP equations and outcomes."""
    eq_path = out / "equations.txt"
    click.echo("Downloading equations.txt...")
    with urlopen(EQUATIONS_URL) as resp:
        eq_path.write_bytes(resp.read())
    click.echo(f"  Saved to {eq_path}")

    click.echo("Downloading outcomes.json.zip...")
    with urlopen(OUTCOMES_URL) as resp:
        zip_data = resp.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        if not json_files:
            raise click.ClickException("No JSON file found in outcomes zip")
        with zf.open(json_files[0]) as src:
            outcomes_path = out / "outcomes.json"
            outcomes_path.write_bytes(src.read())
    click.echo(f"  Saved to {outcomes_path}")

    lines = eq_path.read_text().strip().split("\n")
    click.echo(f"\nDownloaded {len(lines)} equations and outcomes matrix.")


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def report(paths):
    """Display metrics from saved result files."""
    if not paths:
        # List recent results
        results_dir = Path("results")
        if results_dir.exists():
            files = sorted(results_dir.glob("*.json"), reverse=True)[:10]
            if files:
                click.echo("Recent results:")
                for f in files:
                    click.echo(f"  {f}")
            else:
                click.echo("No result files found in results/")
        return

    for path in paths:
        load_and_print_report(Path(path))


if __name__ == "__main__":
    main()
