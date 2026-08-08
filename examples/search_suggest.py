"""Search the web and fetch autocomplete suggestions.

``client.search()`` parses the Brave SERP (no AI answer) into structured
web and news results; ``client.suggest()`` returns typed autocomplete
suggestions, including rich entity suggestions.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.search("python asyncio tutorial")
        print(f"{len(result.web)} web results for {result.query!r}\n")
        for item in result.web[:5]:
            title = item.title or "(no title)"
            print(f"- {title}")
            print(f"  {item.url}")
            if item.description:
                print(f"  {item.description[:100]}")

        print("\nPagination: second page (offset=1)")
        page2 = await client.search("python asyncio tutorial", offset=1)
        print(f"{len(page2.web)} web results on page 2")

        print("\nAutocomplete for 'python':")
        suggestions = await client.suggest("python")
        for suggestion in suggestions.suggestions[:5]:
            label = (
                f" [{suggestion.entity_type}]"
                if suggestion.entity_type and suggestion.entity_type != "query"
                else ""
            )
            print(f"- {suggestion.text}{label}")


if __name__ == "__main__":
    asyncio.run(main())
