"""Worker wrapper tests.

Each worker node must return either its findings or an error in state. It must
never raise. The agent and the LLM calls are replaced by fakes.
"""

import pytest
from langchain_core.messages import HumanMessage

import retail_support.analysis_worker as analysis_module
import retail_support.support_worker as support_module
from retail_support.prompt_store import call_metadata, load_prompt
from retail_support.state import AnalysisFindings, SupportFindings

WORKERS = [
    pytest.param(
        support_module.support_worker,
        support_module,
        "support",
        SupportFindings(summary="the answer", status="resolved"),
        id="support",
    ),
    pytest.param(
        analysis_module.analysis_worker,
        analysis_module,
        "analysis",
        AnalysisFindings(summary="the answer", status="analyzed"),
        id="analysis",
    ),
]


def patch_worker(monkeypatch, module, run_agent, to_findings):
    """Replace everything in a worker module that would call a model."""
    monkeypatch.setattr(module, "create_agent", lambda **kwargs: "agent")
    monkeypatch.setattr(module.ModelProvider, "get", lambda role: "model")
    monkeypatch.setattr(module, "run_agent", run_agent)
    monkeypatch.setattr(module, "to_findings", to_findings)


def state_for(name):
    return {
        "messages": [HumanMessage("the whole question")],
        "plan": {name: "my part"},
    }


@pytest.mark.parametrize("worker, module, name, findings", WORKERS)
async def test_worker_returns_findings(monkeypatch, worker, module, name, findings):
    seen = {}

    async def run_agent(agent, messages, metadata):
        seen["question"] = messages[-1].content
        seen["metadata"] = metadata
        return "the answer"

    async def to_findings(role, schema, status_guide, answer):
        seen["role"] = role
        seen["guide"] = status_guide
        seen["answer"] = answer
        return findings

    patch_worker(monkeypatch, module, run_agent, to_findings)

    result = await worker(state_for(name))

    assert result == {f"{name}_findings": findings, "step_count": 1}
    assert seen == {
        "question": "my part",
        "metadata": call_metadata(name, load_prompt(f"{name}_system")),
        "role": name,
        "guide": load_prompt(f"{name}_status_guide"),
        "answer": "the answer",
    }


@pytest.mark.parametrize("worker, module, name, findings", WORKERS)
async def test_agent_failure_becomes_an_error(
    monkeypatch, worker, module, name, findings
):
    async def run_agent(agent, messages, metadata):
        raise RuntimeError("boom")

    async def to_findings(role, schema, status_guide, answer):
        return findings

    patch_worker(monkeypatch, module, run_agent, to_findings)

    result = await worker(state_for(name))

    assert result == {"errors": ["RuntimeError: boom"], "step_count": 1}


@pytest.mark.parametrize("worker, module, name, findings", WORKERS)
async def test_formatting_failure_becomes_an_error(
    monkeypatch, worker, module, name, findings
):
    async def run_agent(agent, messages, metadata):
        return "the answer"

    async def to_findings(role, schema, status_guide, answer):
        raise ValueError("bad json")

    patch_worker(monkeypatch, module, run_agent, to_findings)

    result = await worker(state_for(name))

    assert result == {"errors": ["ValueError: bad json"], "step_count": 1}
