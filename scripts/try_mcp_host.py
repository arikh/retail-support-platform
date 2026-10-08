import asyncio
import time

from langchain.mcp import MCPAdapter

SERVERS = {
    "mcpServers": {
        "retail-pricing": {
            "command": "uv",
            "args": ["run", "mcp", "run", "src/retail_support/mcp_server.py"],
        }
    }
}

async def main() -> None:
    start_time_whole = time.perf_counter()
    async with MCPAdapter(SERVERS) as adapter:
        tools = await adapter.list_tools()
        print([t.name for t in tools])
        print(type(tools[0]))
        start_time = time.perf_counter()
        for tool in tools:
            if tool.name == "get_plan_status":
                result = await tool.ainvoke({"plan_name": "SUMMER_LATAM_V2"})
        print(result)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time:.6f} seconds")

    end_time_whole = time.perf_counter()
    execution_time_whole = end_time_whole - start_time_whole
    print(f"Full Execution time: {execution_time_whole:.6f} seconds")

asyncio.run(main())

