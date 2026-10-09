import pytest
from langchain_core.messages import AIMessage, HumanMessage

from retail_support import agent_runner
from retail_support.agent_runner import run_agent, to_findings, worker_messages
from retail_support.config import WORKER_ATTEMPTS, WORKER_RECURSION_LIMIT
from retail_support.prompt_store import Prompt, call_metadata, load_prompt
from retail_support.state import SupportFindings

# --- run_agent: the agent's tool loop, with retry -------------------------

METADATA = {"node": "support"}


class FakeAgent:
    """Fails `failures` times, then answers with `answer`."""

    def __init__(self, failures: int, answer: str = "ok"):
        self.failures = failures
        self.answer = answer
        self.calls = 0
        self.config = None

    async def ainvoke(self, payload, config=None):
        self.calls += 1
        self.config = config
        if self.calls <= self.failures:
            raise RuntimeError("model glitch")
        return {"messages": [AIMessage(content=self.answer)]}


async def test_run_agent_retries_after_one_failure():
    agent = FakeAgent(failures=1)
    assert await run_agent(agent, [], METADATA) == "ok"
    assert agent.calls == 2


async def test_run_agent_sends_the_metadata_with_the_step_limit():
    agent = FakeAgent(failures=0)
    await run_agent(agent, [], METADATA)
    assert agent.config == {
        "recursion_limit": WORKER_RECURSION_LIMIT,
        "metadata": METADATA,
    }


async def test_run_agent_gives_up_after_all_attempts():
    agent = FakeAgent(failures=99)
    with pytest.raises(RuntimeError):
        await run_agent(agent, [], METADATA)
    assert agent.calls == WORKER_ATTEMPTS


async def test_run_agent_rejects_empty_answer():
    agent = FakeAgent(failures=0, answer="")
    with pytest.raises(ValueError):
        await run_agent(agent, [], METADATA)
    assert agent.calls == WORKER_ATTEMPTS


# --- to_findings: text answer -> findings, strict JSON, no LLM ------------


class FakeStructured:
    def __init__(self, schema):
        self.schema = schema
        self.messages = None
        self.config = None

    async def ainvoke(self, messages, config=None):
        self.messages = messages
        self.config = config
        return self.schema(summary="from fake", status="not_found")


class FakeModel:
    def __init__(self):
        self.method = None
        self.structured = None

    def with_structured_output(self, schema, method=None):
        self.method = method
        self.structured = FakeStructured(schema)
        return self.structured


GUIDE = Prompt(name="support_status_guide", version="v9", text="GUIDE")


async def test_to_findings_uses_strict_json(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(agent_runner.ModelProvider, "get", lambda role: model)

    findings = await to_findings(
        "support", SupportFindings, GUIDE, "Plan X not found."
    )

    assert findings == SupportFindings(summary="from fake", status="not_found")
    assert model.method == "json_schema"
    assert "GUIDE" in model.structured.messages[0].content
    assert model.structured.messages[1].content == "Plan X not found."


async def test_to_findings_names_both_of_its_prompts(monkeypatch):
    # The formatting call is built from two prompt files, so it names both.
    model = FakeModel()
    monkeypatch.setattr(agent_runner.ModelProvider, "get", lambda role: model)

    await to_findings("support", SupportFindings, GUIDE, "Plan X not found.")

    format_prompt = load_prompt("format_findings")
    assert model.structured.messages[0].content == format_prompt.text + "GUIDE"
    assert model.structured.config == {
        "metadata": call_metadata("support", format_prompt, GUIDE)
    }


def test_worker_messages_replaces_last_message():
    state = {
        "messages": [
            HumanMessage("old question"),
            AIMessage("old answer"),
            HumanMessage("part A? part B?"),
        ],
        "plan": {"support": "part A?"},
    }
    messages = worker_messages(state, "support")
    assert [m.content for m in messages] == ["old question", "old answer", "part A?"]