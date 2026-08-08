"""Quickstart: ask a question and print the answer.

This is the minimal end-to-end example: create a client, ask a question,
and inspect the structured result.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("what is quantum computing?")

    print(result.text)
    print()
    print(f"Sources: {len(result.urls)} unique URLs")
    print(f"Follow-up questions: {len(result.followups)}")


if __name__ == "__main__":
    asyncio.run(main())
