import pytest
from langchain_core.messages import AIMessage, HumanMessage

from retail_support import agent_runner
from retail_support.agent_runner import run_agent, to_findings, worker_messages
from retail_support.config import WORKER_ATTEMPTS
from retail_support.state import SupportFindings

# --- run_agent: the agent's tool loop, with retry -------------------------


class FakeAgent:
    """Fails `failures` times, then answers with `answer`."""

    def __init__(self, failures: int, answer: str = "ok"):
        self.failures = failures
        self.answer = answer
        self.calls = 0

    async def ainvoke(self, payload, config=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("model glitch")
        return {"messages": [AIMessage(content=self.answer)]}


async def test_run_agent_retries_after_one_failure():
    agent = FakeAgent(failures=1)
    assert await run_agent(agent, []) == "ok"
    assert agent.calls == 2


async def test_run_agent_gives_up_after_all_attempts():
    agent = FakeAgent(failures=99)
    with pytest.raises(RuntimeError):
        await run_agent(agent, [])
    assert agent.calls == WORKER_ATTEMPTS


async def test_run_agent_rejects_empty_answer():
    agent = FakeAgent(failures=0, answer="")
    with pytest.raises(ValueError):
        await run_agent(agent, [])
    assert agent.calls == WORKER_ATTEMPTS


# --- to_findings: text answer -> findings, strict JSON, no LLM ------------


class FakeStructured:
    def __init__(self, schema):
        self.schema = schema
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return self.schema(summary="from fake", status="not_found")


class FakeModel:
    def __init__(self):
        self.method = None
        self.structured = None

    def with_structured_output(self, schema, method=None):
        self.method = method
        self.structured = FakeStructured(schema)
        return self.structured


async def test_to_findings_uses_strict_json(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(agent_runner.ModelProvider, "get", lambda role: model)

    findings = await to_findings(
        "support", SupportFindings, "GUIDE", "Plan X not found."
    )

    assert findings == SupportFindings(summary="from fake", status="not_found")
    assert model.method == "json_schema"
    assert "GUIDE" in model.structured.messages[0].content
    assert model.structured.messages[1].content == "Plan X not found."


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