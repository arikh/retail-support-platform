"""The golden set file is well formed and points at things that exist.

No database and no model: these tests read evals/golden_set.json and the
policy files.
"""

from pathlib import Path

from retail_support.golden_set import load_cases, policy_cases
from retail_support.policy_corpus import load_passages
from retail_support.state import FINDINGS_FIELD

POLICIES = Path(__file__).parents[1] / "data" / "policies"
CASE_KEYS = {
    "id",
    "category",
    "question",
    "expected_workers",
    "expected_passages",
    "keywords",
    "note",
}


def test_there_are_twenty_cases_with_the_same_fields():
    cases = load_cases()

    assert len(cases) == 20
    assert all(set(case) == CASE_KEYS for case in cases)


def test_every_case_has_its_own_id_and_a_question():
    cases = load_cases()
    ids = [case["id"] for case in cases]

    assert len(set(ids)) == len(ids)
    assert all(case["question"].strip() for case in cases)


def test_an_expected_worker_is_a_worker_that_is_built():
    # FINDINGS_FIELD names the workers that exist today (support, analysis).
    for case in load_cases():
        assert set(case["expected_workers"]) <= set(FINDINGS_FIELD), case["id"]


def test_an_expected_passage_is_a_section_of_the_policy_files():
    # A typo in a heading would make every search "miss" that case.
    sections = {(p.source, p.heading) for p in load_passages(POLICIES)}

    for case in load_cases():
        for passage in case["expected_passages"]:
            key = (passage["source"], passage["heading"])
            assert key in sections, case["id"]


def test_the_policy_cases_are_the_ones_with_expected_passages():
    cases = load_cases()
    policy = policy_cases(cases)

    assert len(policy) == 9
    assert {case["category"] for case in policy} == {"policy"}
    # Every one of them is a question for the support worker.
    assert all(case["expected_workers"] == ["support"] for case in policy)


def test_the_set_covers_every_kind_of_plan():
    plans = {tuple(sorted(case["expected_workers"])) for case in load_cases()}

    assert plans == {(), ("support",), ("analysis",), ("analysis", "support")}
