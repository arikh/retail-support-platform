import asyncio

from mcp import Client


async def main() -> None:
    async with Client("http://127.0.0.1:8000/mcp") as client:
        print(client.protocol_version)
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])
        result = await client.call_tool(
            "get_plan_status", {"plan_name": "SUMMER_LATAM_V2"}
        )

        print(result.content[0].text)

asyncio.run(main())