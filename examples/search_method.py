"""
19 — Search and Suggest

client.search()  — scrapes Brave Search HTML and returns structured
                   web and news results (no AI answer, no token needed).

client.suggest() — fetches autocomplete suggestions for a partial query,
                   including entity suggestions with thumbnails.
"""

import asyncio

from brave_api import BraveClient


async def demo_search() -> None:
    async with BraveClient() as client:
        print("=" * 60)
        print("DEMO: client.search()")
        print("=" * 60)

        # Basic search
        result = await client.search("python asyncio tutorial")

        print(f"\nQuery  : {result.query}")
        print(f"Web    : {len(result.web)} results")
        print(f"News   : {len(result.news)} results")

        if result.web:
            print("\nWeb Results:")
            for i, item in enumerate(result.web, 1):
                print(f"\n  [{i}] {item.title or '(no title)'}")
                print(f"       URL  : {item.url}")
                if item.description:
                    print(f"       Desc : {item.description[:100]}...")
                if item.age:
                    print(f"       Age  : {item.age}")

        if result.news:
            print("\nNews Results:")
            for i, item in enumerate(result.news, 1):
                print(f"\n  [{i}] {item.title or '(no title)'}")
                print(f"       URL    : {item.url}")
                print(f"       Source : {item.source}")
                print(f"       Age    : {item.age}")

        # All URLs in one flat list
        print(f"\nAll URLs ({len(result.urls)}):")
        for url in result.urls:
            print(f"  {url}")

        # Pagination — page 2
        print("\n" + "=" * 60)
        print("Pagination — page 2 (offset=1)")
        print("=" * 60)
        page2 = await client.search("python asyncio tutorial", offset=1)
        print(f"Page 2: {len(page2.web)} web results")
        for i, item in enumerate(page2.web, 1):
            print(f"\n  [{i}] {item.title or '(no title)'}")
            print(f"       URL  : {item.url}")
            if item.description:
                print(f"       Desc : {item.description[:100]}...")

        # Disable spellcheck — exact keyword matching
        print("\n" + "=" * 60)
        print("spellcheck=False — exact keyword")
        print("=" * 60)
        exact = await client.search("pyton tutorial", spellcheck=False)
        print(f"Results for 'pyton' (no correction): {len(exact.web)}")


async def demo_suggest() -> None:
    async with BraveClient() as client:
        print("\n" + "=" * 60)
        print("DEMO: client.suggest()")
        print("=" * 60)

        # Autocomplete as you type
        for partial in ["py", "pyth", "python"]:
            suggestions = await client.suggest(partial)
            print(f"\nSuggest {partial!r} → {len(suggestions)} items")
            for s in suggestions[:5]:
                entity_label = f" [{s.entity_type}]" if s.entity_type else ""
                entity_marker = " [entity]" if s.is_entity else ""
                print(f"  - {s.text}{entity_label}{entity_marker}")

        # Entity suggestions (people, places)
        print("\nEntity suggestions for 'elon musk':")
        suggestions = await client.suggest("elon musk")
        entities = [s for s in suggestions if s.is_entity]
        print(f"  {len(entities)} entity items")
        for s in entities[:3]:
            print(f"  - {s.text} ({s.entity_type})")
            if s.thumbnail:
                print(f"    thumbnail: {s.thumbnail[:60]}...")


async def main() -> None:
    await demo_search()
    await demo_suggest()


asyncio.run(main())
