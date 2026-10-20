"""Summarise a pass^k routing run.

Reads the JSONL your run writes (one line per trial) and prints:
pass rate per trial, pass^k, pass@k, and the flaky cases.

Each line must have: case_id (str), trial (int), expected_workers (list),
planned_workers (list), passed (bool).

Usage:
    uv run python scripts/pass_k_report.py eval_runs/pass_k_2026-10-19.jsonl
"""

import json
import sys
from collections import defaultdict


def load_trials(path: str) -> dict[str, list[dict]]:
    """Group the trial lines by case_id."""
    by_case: dict[str, list[dict]] = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                by_case[row["case_id"]].append(row)
    return by_case


def summarise(by_case: dict[str, list[dict]]) -> None:
    trial_counts = {len(rows) for rows in by_case.values()}
    if len(trial_counts) != 1:
        print(f"WARNING: cases have different trial counts: {sorted(trial_counts)}")
    k = max(trial_counts)

    total_trials = sum(len(rows) for rows in by_case.values())
    total_passed = sum(r["passed"] for rows in by_case.values() for r in rows)
    n_cases = len(by_case)

    all_pass = [c for c, rows in by_case.items() if all(r["passed"] for r in rows)]
    any_pass = [c for c, rows in by_case.items() if any(r["passed"] for r in rows)]
    never = [c for c in by_case if c not in any_pass]
    flaky = [c for c in any_pass if c not in all_pass]

    print(f"Cases: {n_cases}   Trials per case: {k}   Total trials: {total_trials}")
    print(f"Pass rate per trial: {total_passed}/{total_trials} = {total_passed / total_trials:.0%}")
    print(f"pass^{k} (every trial passed):    {len(all_pass)}/{n_cases} = {len(all_pass) / n_cases:.0%}")
    print(f"pass@{k} (at least one passed):    {len(any_pass)}/{n_cases} = {len(any_pass) / n_cases:.0%}")
    print()

    print("Per case (only the cases that are not always right):")
    for case_id in sorted(flaky + never):
        rows = sorted(by_case[case_id], key=lambda r: r["trial"])
        passes = sum(r["passed"] for r in rows)
        label = "FLAKY" if passes else "ALWAYS WRONG"
        plans = [",".join(r["planned_workers"]) or "-" for r in rows]
        expected = ",".join(rows[0]["expected_workers"]) or "-"
        print(f"  {case_id}: {passes}/{k} {label:<12} expected [{expected}]  planned {plans}")
    if not flaky and not never:
        print("  none - every case passed every trial")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: pass_k_report.py <path to pass_k JSONL>")
    summarise(load_trials(sys.argv[1]))
