import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from retail_support import db, pricing_lookups


@asynccontextmanager
async def server_lifespan(server: MCPServer) -> AsyncIterator[dict]:
    db.use_database_url(os.environ["MCP_DATABASE_URL"])
    yield {}

mcp = MCPServer("retail-pricing", lifespan=server_lifespan)

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

mcp.tool(annotations=READ_ONLY)(pricing_lookups.get_plan_status)
mcp.tool(annotations=READ_ONLY)(pricing_lookups.get_missing_materials)
mcp.tool(annotations=READ_ONLY)(pricing_lookups.get_downstream_status)
mcp.tool(annotations=READ_ONLY)(pricing_lookups.get_material_rejection_reason)
