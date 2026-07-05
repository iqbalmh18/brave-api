"""
01 — Quick Start

The simplest way to ask a question and get a full answer back.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("apa itu quantum computing?")

    print(f"Answer ({len(result.text)} chars):")
    print(result.text[:500])

    if result.infobox:
        print(f"\nInfobox: {result.infobox.title} — {result.infobox.subtitle}")

    print(f"\nWeb results : {len(result.web_results)}")
    print(f"Images      : {len(result.images)}")
    print(f"Videos      : {len(result.videos)}")
    print(f"Followups   : {len(result.followups)}")


asyncio.run(main())
