"""Aggregate per-cheatsheet results into a combined report.

Reads `analysis/results/<cheatsheet>/summary.json` for each cheatsheet
and writes:
  - analysis/RESULTS.md  (overall comparison)
  - analysis/results/COMPARISON.json  (raw aggregated stats)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "analysis" / "results"

SPLITS = ["normal", "hard", "hard1", "hard2", "hard3",
          "evaluation_normal", "evaluation_hard", "evaluation_extra_hard",
          "evaluation_order5", "full_etp"]


def main():
    cheatsheets = sorted([p.name for p in RES.iterdir() if p.is_dir()])
    if not cheatsheets:
        print("No results found.", file=sys.stderr)
        return 1

    # Per-cheatsheet × per-split matrix
    matrix = {}
    rule_breakdowns = {}
    for cs in cheatsheets:
        d = RES / cs
        per_split = {}
        rb = {}
        for split in SPLITS:
            jpath = d / f"{split}.json"
            if not jpath.exists():
                # Try summary.json
                continue
            with open(jpath) as f:
                s = json.load(f)
            n = s.get("n")
            nc = s.get("n_correct")
            if n and nc is not None:
                per_split[split] = {"n": n, "n_correct": nc, "accuracy": nc / n}
            rb[split] = s.get("by_rule", {})
        # If full_etp didn't exist, leave it out
        matrix[cs] = per_split
        rule_breakdowns[cs] = rb

    out_json = {"matrix": matrix, "rule_breakdowns": rule_breakdowns}
    with open(RES / "COMPARISON.json", "w") as f:
        json.dump(out_json, f, indent=2)
    print(f"wrote {RES/'COMPARISON.json'}")

    # Markdown
    md = []
    md.append("# Programmatic cheatsheet evaluation — combined results")
    md.append("")
    md.append(f"Cheatsheets evaluated: {', '.join(cheatsheets)}")
    md.append("")
    md.append("## Overall accuracy by split")
    md.append("")
    header = ["split"] + cheatsheets
    md.append("| " + " | ".join(header) + " |")
    md.append("|" + "|".join("---" for _ in header) + "|")
    for split in SPLITS:
        row = [split]
        for cs in cheatsheets:
            entry = matrix.get(cs, {}).get(split)
            if entry:
                row.append(f"{entry['accuracy']*100:.2f}%  ({entry['n_correct']}/{entry['n']})")
            else:
                row.append("—")
        md.append("| " + " | ".join(row) + " |")

    md.append("")
    md.append("## Per-cheatsheet, per-split rule breakdowns")
    md.append("")
    for cs in cheatsheets:
        md.append(f"### {cs}")
        md.append("")
        sumpath = RES / cs / "SUMMARY.md"
        if sumpath.exists():
            md.append(f"See `analysis/results/{cs}/SUMMARY.md` for full per-rule tables.")
        md.append("")

    auto_path = ROOT / "analysis" / "RESULTS_AUTO.md"
    with open(auto_path, "w") as f:
        f.write("\n".join(md))
    print(f"wrote {auto_path}  (RESULTS.md is the curated report; this is the auto-generated index)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
