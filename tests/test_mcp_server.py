"""The MCP server, tested through an in-memory client (no subprocess, no port)."""

import pytest
from mcp import Client

from retail_support import db
from retail_support.mcp_server import mcp


@pytest.fixture(autouse=True)
def restore_database_url(monkeypatch):
    # The server's lifespan chooses the MCP database user for this process.
    # pytest puts the old value back after each test.
    monkeypatch.setattr(db, "_database_url", None)


async def test_client_gets_the_2026_protocol():
    async with Client(mcp, raise_exceptions=True) as client:
        assert client.protocol_version == "2026-07-28"

async def test_server_runs_as_the_read_only_role():
    async with Client(mcp, raise_exceptions=True):
        rows = await db.fetch_all("select current_user")
        assert rows == [{"current_user": "retail_mcp_ro"}]

async def test_lists_four_read_only_tools():
    async with Client(mcp, raise_exceptions=True) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert names == {
            "get_plan_status",
            "get_missing_materials",
            "get_downstream_status",
            "get_material_rejection_reason",
        }

        assert all(tool.annotations.read_only_hint for tool in tools.tools)

async def test_get_plan_status_returns_the_plan():
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "get_plan_status", {"plan_name": "SUMMER_LATAM_V2"}
        )

        assert not result.is_error
        assert "8/10" in result.content[0].text


async def test_bad_arguments_return_a_tool_error():
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "get_material_rejection_reason", {"material_id": {}}
        )

        assert result.is_error
        assert "material_id" in result.content[0].text