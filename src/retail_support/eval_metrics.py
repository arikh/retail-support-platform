"""How one case of the golden set is scored.

Three small functions that say what "correct" means:
  is_hit        did a search return a passage the case expects?
  rate          what share of the cases passed?
  same_workers  did the supervisor plan the workers the case expects?

No database and no model here: values in, a verdict out.
"""


def is_hit(rows: list[dict], expected: list[dict], k: int) -> bool:
    """True when one of the expected passages is among the first k rows.

    rows is what a search returned, best first. expected is the case's
    expected_passages; any one of them is enough. A passage is itself by
    its source and its heading."""
    for passage in expected:  # each expected passage is a dict
        for row in rows[:k]:  # each of the first k rows is a dict
            same_source = row["source"] == passage["source"]
            same_heading = row["heading"] == passage["heading"]
            if same_source and same_heading:
                return True  # found one: that is a hit
    return False  # looked at everything, found none


def rate(results: list[bool]) -> float:
    """The share of True in the list, from 0.0 to 1.0.

    [True, False, True, True] gives 0.75. An empty list gives 0.0, so the
    division never fails."""
    if not results:
        return 0.0

    return results.count(True) / len(results)


def same_workers(planned: list[str], expected: list[str]) -> bool:
    """True when the supervisor planned exactly the expected workers.

    The order does not matter, so both lists are compared as sets. Two empty
    lists match: the case expects a refusal and the plan was empty."""
    return set(planned) == set(expected)
