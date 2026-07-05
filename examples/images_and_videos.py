"""
04 — Images and Videos

Extract image and video results from the AI answer.
Queries about visual topics (travel, nature, media) tend to yield more results.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("5 rekomendasi wisata alam di Indonesia")

    print(result.text[:300] if result.text else "(no text)")

    if result.images:
        print(f"\nImages ({len(result.images)}):")
        for i, img in enumerate(result.images, 1):
            print(f"\n  [{i}] {img.url}")
            if img.title:
                print(f"       Title     : {img.title}")
            if img.source:
                print(f"       Source    : {img.source}")
            if img.thumbnail:
                print(f"       Thumbnail : {img.thumbnail}")
            if img.width and img.height:
                print(f"       Size      : {img.width}x{img.height}")
    else:
        print("\n(no images — try a more visual query)")

    if result.has_videos:
        print(f"\nVideos ({len(result.videos)}):")
        for i, vid in enumerate(result.videos, 1):
            print(f"\n  [{i}] {vid.url}")
            if vid.title:
                print(f"       Title   : {vid.title}")
            if vid.channel:
                print(f"       Channel : {vid.channel}")
            if vid.duration:
                print(f"       Duration: {vid.duration}")
            if vid.thumbnail:
                print(f"       Thumb   : {vid.thumbnail}")
    else:
        print("\n(no videos)")


asyncio.run(main())
