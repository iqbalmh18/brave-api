"""
10 — Auto Tools Control

auto_tools=True (default): the client automatically calls run_tool for
every TOOL_USE event and yields enriched AUGMENT_WITH_TOOL_USE events.

auto_tools=False: raw TOOL_USE events are passed through unchanged,
letting you inspect or handle them manually.
"""

import asyncio

from brave_api import BraveClient, StreamEventType


async def main() -> None:
    query = "latest news about python programming language"

    # With auto_tools enabled — enriched results are collected automatically
    async with BraveClient() as client:
        result_with = await client.ask(query)

    print("=== auto_tools=True ===")
    print(f"Answer : {result_with.text[:200]}...")
    print(f"Web    : {len(result_with.web_results)} results")
    print(f"Images : {len(result_with.images)}")
    print(f"URLs   : {len(result_with.urls)}")
    print(f"Events : {len(result_with.raw_events)}")

    # With auto_tools disabled — see raw TOOL_USE events before enrichment
    async with BraveClient() as client:
        conv_raw = await client.conversation(query, auto_tools=False)

        tool_events = []
        text_parts = []

        async for event in conv_raw.stream_events():
            if event.type is StreamEventType.TEXT_DELTA:
                text_parts.append(event.delta)
            elif event.type is StreamEventType.TOOL_USE:
                tool_events.append(event)

    print("\n=== auto_tools=False ===")
    print(f"Partial answer : {''.join(text_parts)[:200]}...")
    print(f"Raw tool events: {len(tool_events)}")
    for te in tool_events:
        print(f"  tool={te.tool_name!r}  id={te.tool_id}")
        if te.tool_arguments:
            print(f"    args: {str(te.tool_arguments)[:100]}")


asyncio.run(main())
