"""Where the support worker gets its tools: in-process (the default) or MCP.

The MCP test starts the real server as a child process over stdio, so it needs
the local Postgres, `uv` on the PATH, and the tests run from the repo root.
"""

import pytest

from retail_support.tool_source import support_tool_source, support_tools

SUPPORT_TOOL_NAMES = {
    "get_plan_status",
    "get_missing_materials",
    "get_downstream_status",
    "get_material_rejection_reason",
}


def test_default_is_in_process(monkeypatch):
    monkeypatch.delenv("SUPPORT_TOOL_SOURCE", raising=False)
    assert support_tool_source() == "in_process"


def test_mcp_can_be_chosen(monkeypatch):
    monkeypatch.setenv("SUPPORT_TOOL_SOURCE", "mcp")
    assert support_tool_source() == "mcp"


def test_unknown_source_raises_and_names_the_value(monkeypatch):
    monkeypatch.setenv("SUPPORT_TOOL_SOURCE", "mpc")
    with pytest.raises(ValueError, match="'mpc'"):
        support_tool_source()


async def test_in_process_gives_the_four_tools(monkeypatch):
    monkeypatch.delenv("SUPPORT_TOOL_SOURCE", raising=False)
    async with support_tools() as tools:
        assert {tool.name for tool in tools} == SUPPORT_TOOL_NAMES


@pytest.mark.filterwarnings("ignore:`langchain.mcp` is in beta")
async def test_mcp_gives_the_same_four_tools_and_they_work(monkeypatch):
    monkeypatch.setenv("SUPPORT_TOOL_SOURCE", "mcp")
    async with support_tools() as tools:
        assert {tool.name for tool in tools} == SUPPORT_TOOL_NAMES

        plan_status = next(t for t in tools if t.name == "get_plan_status")
        result = await plan_status.ainvoke({"plan_name": "SUMMER_LATAM_V2"})

    # An MCP tool returns content blocks, not a plain string.
    assert "8/10" in str(result)
