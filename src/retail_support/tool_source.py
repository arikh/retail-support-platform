import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from retail_support.config import DEFAULT_SUPPORT_TOOL_SOURCE, SUPPORT_TOOL_SOURCES
from retail_support.support_tools import (
    get_downstream_status,
    get_material_rejection_reason,
    get_missing_materials,
    get_plan_status,
    search_policy,
)

MCP_SERVERS = {
    "mcpServers": {
        "retail-pricing": {
            "command": "uv",
            "args": ["run", "mcp", "run", "src/retail_support/mcp_server.py"],
        }
    }
}

IN_PROCESS_TOOLS = [
    get_downstream_status,
    get_material_rejection_reason,
    get_missing_materials,
    get_plan_status,
]

# The policy search is always in-process. The MCP server offers the four
# lookups only (ADR-0014), so on the MCP path the search is added here.
POLICY_TOOLS = [search_policy]


def support_tool_source() -> str:
    source = os.environ.get("SUPPORT_TOOL_SOURCE", DEFAULT_SUPPORT_TOOL_SOURCE)
    if source not in SUPPORT_TOOL_SOURCES:
        raise ValueError(f"unknown SUPPORT_TOOL_SOURCE: {source!r}")
    return source

@asynccontextmanager
async def support_tools() -> AsyncIterator[list]:
    if support_tool_source() == "mcp":
        from langchain.mcp import MCPAdapter
        async with MCPAdapter(MCP_SERVERS) as adapter:
            yield list(await adapter.list_tools()) + POLICY_TOOLS
    else:
        yield IN_PROCESS_TOOLS + POLICY_TOOLS
    