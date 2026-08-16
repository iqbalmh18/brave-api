"""Search Brave's web, image, news, video, and Goggles verticals.

All methods return the same :class:`brave_api.SearchResult` envelope. Each
vertical populates its matching result list and supports ``offset`` pagination.
"""

import asyncio

from brave_api import BraveClient, SearchResult


def print_page(label: str, result: SearchResult) -> None:
    """Print the common pagination fields from a SearchResult."""
    print(f"{label}: type={result.search_type.value}, offset={result.offset}")
    print(f"  has_more={result.has_more}, urls={len(result.urls)}")


async def main() -> None:
    async with BraveClient() as client:
        all_results = await client.search("python asyncio")
        images = await client.search_images("python logo")
        news = await client.search_news("python release")
        videos = await client.search_videos("python asyncio tutorial")
        goggles = await client.search_goggles("privacy search")

        # Brave uses offset as a page number: 0 is the first page, 1 the next.
        news_page2 = await client.search_news("python release", offset=1)

    print_page("All", all_results)
    for item in all_results.web[:3]:
        print(f"  - {item.title or '(untitled)'}: {item.url}")

    print_page("Images", images)
    for item in images.images[:3]:
        print(f"  - {item.title or '(untitled)'}: {item.url}")

    print_page("News", news)
    for item in news.news[:3]:
        print(f"  - {item.title or '(untitled)'}: {item.url}")

    print_page("Videos", videos)
    for item in videos.videos[:3]:
        print(f"  - {item.title or '(untitled)'}: {item.url}")

    print_page("Goggles", goggles)
    for item in goggles.web[:3]:
        print(f"  - {item.title or '(untitled)'}: {item.url}")

    print(f"News page 2: offset={news_page2.offset}, results={len(news_page2.news)}")


if __name__ == "__main__":
    asyncio.run(main())
