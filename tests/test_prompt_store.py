"""Prompts live in versioned files and are loaded by name (Piece 4, step 1)."""

import dataclasses

import pytest

from retail_support import agent_runner, analysis_worker, supervisor, support_worker
from retail_support.prompt_store import ACTIVE_VERSIONS, Prompt, load_prompt


@pytest.mark.parametrize("name", sorted(ACTIVE_VERSIONS))
def test_every_active_prompt_loads(name):
    prompt = load_prompt(name)

    assert prompt == Prompt(name=name, version=ACTIVE_VERSIONS[name], text=prompt.text)
    assert prompt.text.strip()


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
    assert supervisor.ROUTING_SYSTEM_PROMPT == load_prompt("routing_system").text
    assert support_worker.SUPPORT_SYSTEM_PROMPT == load_prompt("support_system").text
    assert (
        support_worker.SUPPORT_STATUS_GUIDE
        == load_prompt("support_status_guide").text
    )
    assert (
        analysis_worker.ANALYSIS_SYSTEM_PROMPT == load_prompt("analysis_system").text
    )
    assert (
        analysis_worker.ANALYSIS_STATUS_GUIDE
        == load_prompt("analysis_status_guide").text
    )
    assert agent_runner.FORMAT_PROMPT == load_prompt("format_findings").text
