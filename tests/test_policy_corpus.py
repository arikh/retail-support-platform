"""The policy files are cut into passages, one per "## " section (Piece 2).

No database and no model: these tests read the files in data/policies.
"""

from pathlib import Path

import pytest

from retail_support.policy_corpus import Passage, load_passages, split_markdown

POLICIES = Path(__file__).parents[1] / "data" / "policies"


def test_the_three_files_give_sixteen_passages():
    passages = load_passages(POLICIES)

    per_file = {}
    for passage in passages:
        per_file[passage.source] = per_file.get(passage.source, 0) + 1

    assert per_file == {
        "general_faq.md": 7,
        "material_setup.md": 5,
        "pricing_rules.md": 4,
    }


def test_a_passage_holds_its_heading_and_its_text():
    passages = load_passages(POLICIES)
    pending = next(p for p in passages if "PENDING" in p.heading)

    assert pending.source == "general_faq.md"
    assert pending.heading == 'What does "PENDING" downstream status mean?'
    assert pending.content.startswith(
        'What does "PENDING" downstream status mean?\nPENDING means the price'
    )
    assert pending.content.endswith("escalate to the support team.")


def test_every_passage_has_its_own_name():
    # (source, heading) is the primary key of the table.
    passages = load_passages(POLICIES)
    names = [(passage.source, passage.heading) for passage in passages]

    assert len(set(names)) == len(names)


def test_the_file_title_is_left_out():
    text = "# The title\nSome words under the title.\n\n## First\nThe body.\n"

    assert split_markdown("a.md", text) == [
        Passage(source="a.md", heading="First", content="First\nThe body.")
    ]


def test_a_list_keeps_its_lines():
    text = "## Reasons\nThe reasons:\n\n1. One  \n2. Two\n"

    (passage,) = split_markdown("a.md", text)

    assert passage.content == "Reasons\nThe reasons:\n\n1. One\n2. Two"


def test_an_empty_section_is_refused():
    with pytest.raises(ValueError, match="empty section in a.md: 'Nothing here'"):
        split_markdown("a.md", "## Nothing here\n\n## Next\nSome text.\n")
