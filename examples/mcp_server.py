"""
20 — MCP Server

Run the Brave API as an MCP server so AI clients (Claude Desktop, Cursor,
VS Code, ChatGPT, etc.) can call ask / search / suggest as tools.

Install the optional dependency first:
    pip install "brave-api[mcp]"

Run (STDIO — default for local clients):
    python examples/mcp_server.py

Run (HTTP — for remote or multi-client deployments):
    python examples/mcp_server.py --http

Or use the built-in CLI entry-point:
    brave-api-mcp
"""

from __future__ import annotations

import asyncio

from brave_api import ClientConfig
from brave_api.mcp.server import create_server


async def demo_ask() -> None:
    from fastmcp.client import Client

    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "ask",
            {"query": "apa itu Model Context Protocol?"},
        )

    data = result.data
    print("=" * 60)
    print("DEMO 1: ask tool")
    print("=" * 60)
    print(f"\nAnswer ({len(data['text'])} chars):")
    print(data["text"][:400] + ("..." if len(data["text"]) > 400 else ""))

    if data.get("infobox"):
        print(f"\nInfobox : {data['infobox']['title']} — {data['infobox']['subtitle']}")

    print(f"\nImages  : {len(data['images'])}")
    print(f"Videos  : {len(data['videos'])}")
    print(f"Sources : {len(data['web_results'])}")
    print(f"Followups: {len(data['followups'])}")
    for q in data["followups"]:
        print(f"  → {q}")


async def demo_search() -> None:
    from fastmcp.client import Client

    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search",
            {"query": "python asyncio tutorial", "offset": 0},
        )

    data = result.data
    print("\n" + "=" * 60)
    print("DEMO 2: search tool")
    print("=" * 60)
    print(f"\nWeb   : {len(data['web'])} results")
    for i, item in enumerate(data["web"][:3], 1):
        print(f"  [{i}] {item['title']}")
        print(f"       {item['url']}")

    print(f"\nNews  : {len(data['news'])} results")
    for i, item in enumerate(data["news"][:3], 1):
        print(f"  [{i}] {item['title']} — {item['source']}")


async def demo_suggest() -> None:
    from fastmcp.client import Client

    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "suggest",
            {"query": "python", "rich": True},
        )

    data = result.data
    print("\n" + "=" * 60)
    print("DEMO 3: suggest tool")
    print("=" * 60)
    print(f"\nSuggestions for {data['query']!r}:")
    for s in data["suggestions"][:6]:
        entity = f" [{s['entity_type']}]" if s["entity_type"] else ""
        print(f"  - {s['text']}{entity}")


async def demo_custom_config() -> None:
    from fastmcp.client import Client

    config = ClientConfig(country="id", language="id", ui_lang="id-id")
    mcp = create_server(config=config)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "ask",
            {"query": "apa itu kecerdasan buatan?"},
        )

    print("\n" + "=" * 60)
    print("DEMO 4: custom config (Indonesian locale)")
    print("=" * 60)
    print(result.data["text"][:300])


async def main() -> None:
    await demo_ask()
    await demo_search()
    await demo_suggest()
    await demo_custom_config()


if __name__ == "__main__":
    asyncio.run(main())
