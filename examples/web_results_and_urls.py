"""
03 — Web Results and URLs

Access the structured web results, thumbnails, favicons, and unique
URL list that Brave attaches to every AI answer.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        conv = await client.conversation("python asyncio best practices 2026", language="en")
        result = await conv.collect()

    print(f"Answer ({len(result.text)} chars):")
    print(result.text[:300])

    print(f"\nWeb Results ({len(result.web_results)} pages):")
    for i, web in enumerate(result.web_results, 1):
        print(f"\n[{i}] {web.title or '(no title)'}")
        print(f"    URL         : {web.url}")
        if web.description:
            print(f"    Description : {web.description[:100]}")
        if web.favicon:
            print(f"    Favicon     : {web.favicon}")
        if web.thumbnail:
            print(f"    Thumbnail   : {web.thumbnail}")
        if web.thumbnail_original:
            print(f"    Original    : {web.thumbnail_original}")

    print(f"\nAll Unique URLs ({len(result.urls)}):")
    for url in result.urls:
        print(f"  {url}")

    print(f"\nImages / Thumbnails ({len(result.images)}):")
    for img in result.images[:5]:
        print(f"\n  URL    : {img.url}")
        if img.title:
            print(f"  Title  : {img.title}")
        if img.source:
            print(f"  Source : {img.source}")
        if img.thumbnail:
            print(f"  Thumb  : {img.thumbnail}")


asyncio.run(main())
