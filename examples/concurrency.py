"""Run multiple queries concurrently with a single client.

The client enforces a configurable concurrency limit (``max_concurrent``,
default 5), so ``asyncio.gather`` is safe to use with one shared client.
"""

import asyncio
import time

from brave_api import BraveClient

QUERIES = [
    "what is numpy?",
    "what is pandas?",
    "what is matplotlib?",
    "what is scikit-learn?",
]


async def main() -> None:
    started = time.perf_counter()
    async with BraveClient() as client:
        results = await asyncio.gather(*(client.ask(query) for query in QUERIES))
    elapsed = time.perf_counter() - started

    for query, result in zip(QUERIES, results, strict=True):
        print(f"  {query}: {len(result.text)} chars, {len(result.urls)} sources")
    print(f"\n{len(QUERIES)} queries in {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
