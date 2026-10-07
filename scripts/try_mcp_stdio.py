import asyncio

from mcp import Client, StdioServerParameters

server = StdioServerParameters(
    command="uv",
    args=["run", "mcp", "run", "src/retail_support/mcp_server.py"],
)

async def main() -> None:
    async with Client(server) as client:
        print(client.protocol_version)
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])
        result = await client.call_tool(
            "get_plan_status", {"plan_name": "SUMMER_LATAM_V2"}
        )

        print(result.content[0].text)

asyncio.run(main())