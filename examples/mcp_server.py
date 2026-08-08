"""Embed the MCP server in your own application.

The server runs over stdio (Claude Desktop, Cursor, ...) or as a streamable
HTTP service. This example runs it in-process and calls its tools through
the FastMCP client.
"""

import asyncio

from fastmcp.client import Client

from brave_api.mcp.server import create_server


async def main() -> None:
    server = create_server()

    async with Client(server) as client:
        tools = await client.list_tools()
        print("registered tools:", ", ".join(sorted(tool.name for tool in tools)))

        result = await client.call_tool("search", {"query": "python asyncio", "offset": 0})
        print(f"search: {len(result.data['web'])} web results")

        result = await client.call_tool("suggest", {"query": "python"})
        print(f"suggest: {[item['text'] for item in result.data['suggestions']][:5]}")


if __name__ == "__main__":
    asyncio.run(main())
