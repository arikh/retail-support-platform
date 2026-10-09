"""Prompts live in versioned files and are loaded by name (Piece 4, step 1)."""

import dataclasses
import re

import pytest

from retail_support import agent_runner, analysis_worker, supervisor, support_worker
from retail_support.prompt_store import (
    ACTIVE_VERSIONS,
    PROMPTS_DIR,
    Prompt,
    call_metadata,
    load_prompt,
)


@pytest.mark.parametrize("name", sorted(ACTIVE_VERSIONS))
def test_every_active_prompt_loads(name):
    prompt = load_prompt(name)

    assert prompt == Prompt(name=name, version=ACTIVE_VERSIONS[name], text=prompt.text)
    assert prompt.text.strip()


@pytest.mark.parametrize("name", sorted(ACTIVE_VERSIONS))
def test_every_earlier_version_is_kept(name):
    # Governance: a rollback needs the old file, and old log rows name it.
    live = ACTIVE_VERSIONS[name]
    assert re.fullmatch(r"v[1-9][0-9]*", live)

    for number in range(1, int(live[1:]) + 1):
        assert (PROMPTS_DIR / f"{name}.v{number}.txt").is_file()


def test_unknown_prompt_raises_and_names_it():
    with pytest.raises(ValueError, match="'no_such_prompt'"):
        load_prompt("no_such_prompt")


def test_a_loaded_prompt_cannot_be_changed():
    prompt = load_prompt("support_system")

    with pytest.raises(dataclasses.FrozenInstanceError):
        prompt.text = "something else"


def test_each_file_is_read_once():
    assert load_prompt("routing_system") is load_prompt("routing_system")


def test_format_prompt_keeps_its_trailing_newlines():
    # It is joined to a status guide; stripping would glue the two together.
    assert load_prompt("format_findings").text.endswith("\n\n")


def test_the_code_uses_the_loaded_prompts():
    # Each constant holds the whole Prompt (name, version, text), not only
    # the text, so a model call can say which prompt and version it used.
    assert supervisor.ROUTING_SYSTEM_PROMPT is load_prompt("routing_system")
    assert support_worker.SUPPORT_SYSTEM_PROMPT is load_prompt("support_system")
    assert support_worker.SUPPORT_STATUS_GUIDE is load_prompt(
        "support_status_guide"
    )
    assert analysis_worker.ANALYSIS_SYSTEM_PROMPT is load_prompt(
        "analysis_system"
    )
    assert analysis_worker.ANALYSIS_STATUS_GUIDE is load_prompt(
        "analysis_status_guide"
    )
    assert agent_runner.FORMAT_PROMPT is load_prompt("format_findings")


# --- call_metadata: what a model call says about itself ---------------------


def test_call_metadata_for_one_prompt():
    prompt = Prompt(name="support_system", version="v1", text="...")

    assert call_metadata("support", prompt) == {
        "node": "support",
        "prompts": {"support_system": "v1"},
    }


def test_call_metadata_keeps_each_prompt_with_its_own_version():
    # The formatting call uses two prompt files; both versions must show.
    first = Prompt(name="format_findings", version="v1", text="...")
    second = Prompt(name="support_status_guide", version="v2", text="...")

    assert call_metadata("support", first, second) == {
        "node": "support",
        "prompts": {"format_findings": "v1", "support_status_guide": "v2"},
    }
