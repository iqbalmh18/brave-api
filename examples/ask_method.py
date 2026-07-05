"""
18 — ask() and ask_stream()

Two convenience methods on BraveClient:
  ask()        — blocking, returns a complete StreamResult
  ask_stream() — async generator, yields StreamEvent objects in real time

Both are thin wrappers around conversation() + collect() / stream_events().
"""

import asyncio

from brave_api import BraveClient, StreamEventType


async def demo_ask() -> None:
    """ask() — wait for the full result before doing anything with it."""
    print("=" * 60)
    print("DEMO 1: ask() — full result at once")
    print("=" * 60)

    async with BraveClient() as client:
        result = await client.ask("Siapa itu Elon Musk")

    print(f"\nAnswer ({len(result.text)} chars):")
    print(result.text[:400] + ("..." if len(result.text) > 400 else ""))

    # Infobox — entity card like the Wikipedia panel in the browser
    print(f"\nInfobox: has_infobox={result.has_infobox}")
    if result.infobox:
        print(f"  Name     : {result.infobox.title}")
        print(f"  Subtitle : {result.infobox.subtitle}")
        print(f"  URL      : {result.infobox.url}")
        print(f"  Image    : {result.infobox.image_url}")
        long_desc = result.infobox.attributes.get("long_desc", "")
        if long_desc:
            print(f"  Desc     : {str(long_desc)[:150]}...")

    print(f"\nImages  : {len(result.images)}")
    for i, img in enumerate(result.images[:3], 1):
        print(f"  [{i}] {img.url[:75]}")

    print(f"\nVideos  : {len(result.videos)}")
    for i, vid in enumerate(result.videos[:3], 1):
        print(f"  [{i}] {(vid.title or vid.url)[:65]}")

    print(f"\nSources : {len(result.web_results)}")
    for i, w in enumerate(result.web_results[:3], 1):
        print(f"  [{i}] {w.title}")
        print(f"       {w.url[:65]}")

    print(f"\nFollowups: {len(result.followups)}")
    for q in result.followups:
        print(f"  → {q}")


async def demo_ask_stream() -> None:
    """ask_stream() — typewriter output, process events as they arrive."""
    print("\n" + "=" * 60)
    print("DEMO 2: ask_stream() — real-time streaming")
    print("=" * 60)
    print("\nAnswer (streaming):")

    tool_count = 0
    text_chars = 0

    async with BraveClient() as client:
        async for event in client.ask_stream("Apa itu Space X?"):
            if event.type is StreamEventType.TEXT_DELTA:
                print(event.delta, end="", flush=True)
                text_chars += len(event.delta)

            elif event.type is StreamEventType.TEXT_STOP:
                print()

            elif event.type is StreamEventType.AUGMENT_WITH_TOOL_USE:
                tool_count += 1
                query = event.payload.get("query", "")
                print(f"\n  [tool #{tool_count}: searching '{query}']", flush=True)

            elif event.type is StreamEventType.FOLLOWUPS:
                followups = event.payload.get("followups", [])
                if followups:
                    print("\nFollowups:")
                    for q in followups:
                        print(f"  → {q}")

    print(f"\nTotal: {text_chars} chars, {tool_count} tool calls")


async def main() -> None:
    await demo_ask()
    await demo_ask_stream()


asyncio.run(main())
