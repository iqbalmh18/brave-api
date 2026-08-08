"""Explore every part of a collected :class:`StreamResult`.

An AI answer comes with web results, images, videos, a knowledge panel
(infobox), and follow-up questions. This example prints each section.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("what is quantum computing?")

    print(f"Answer ({len(result.text)} characters):\n")
    print(result.text[:500])

    if result.infobox:
        subtitle = result.infobox.subtitle or ""
        print(f"\nInfobox: {result.infobox.title} — {subtitle}")

    print(f"\nWeb results: {len(result.web_results)}")
    for item in result.web_results[:3]:
        print(f"- {item.title}: {item.url}")

    print(f"\nImages: {len(result.images)}")
    for image in result.images[:3]:
        print(f"- {image.url}")

    print(f"\nVideos: {len(result.videos)}")
    for video in result.videos[:3]:
        print(f"- {video.title}: {video.url}")

    print(f"\nFollow-up questions: {len(result.followups)}")
    for question in result.followups:
        print(f"- {question}")


if __name__ == "__main__":
    asyncio.run(main())
