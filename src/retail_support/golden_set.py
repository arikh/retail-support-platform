"""Loads the golden set: fixed questions with their expected outcome.

The file is data, written by a person who knows the domain. This module only
reads it. How a case is scored is in eval_metrics.py.
"""

import json
from pathlib import Path

GOLDEN_SET = Path(__file__).parents[2] / "evals" / "golden_set.json"


def load_cases(path: Path = GOLDEN_SET) -> list[dict]:
    """Every case of the golden set, in file order.

    Each case has id, category, question, expected_workers, expected_passages,
    keywords and note."""
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def policy_cases(cases: list[dict]) -> list[dict]:
    """The cases that name the passages a search must find."""
    return [case for case in cases if case["expected_passages"]]
