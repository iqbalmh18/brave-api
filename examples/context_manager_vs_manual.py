"""
14 — Concurrent Queries

Run multiple queries in parallel using asyncio.gather() and compare
the elapsed time against sequential execution.
"""

import asyncio
import time

from brave_api import BraveClient, StreamResult

QUERIES = [
    "apa itu numpy?",
    "apa itu pandas?",
    "apa itu matplotlib?",
    "apa itu scikit-learn?",
    "apa itu tensorflow?",
]


async def ask(client: BraveClient, query: str) -> StreamResult:
    """Run a single query and return the full result."""
    return await client.ask(query)


async def main() -> None:
    # Parallel execution
    t0 = time.perf_counter()
    async with BraveClient() as client:
        results = await asyncio.gather(
            *[ask(client, q) for q in QUERIES],
            return_exceptions=True,
        )
    elapsed_parallel = time.perf_counter() - t0

    print(f"=== Parallel ({elapsed_parallel:.1f}s for {len(QUERIES)} queries) ===")
    for query, item in zip(QUERIES, results, strict=True):
        if isinstance(item, BaseException):
            print(f"\n  Q: {query}")
            print(f"  ERROR: {item}")
        else:
            snippet = item.text[:100].replace("\n", " ")
            print(f"\n  Q: {query}")
            print(f"  A: {snippet}...")
            print(f"     web={len(item.web_results)} | images={len(item.images)}")

    # Sequential for comparison (only first 2 to keep it fast)
    t1 = time.perf_counter()
    async with BraveClient() as client:
        for q in QUERIES[:2]:
            await ask(client, q)
    elapsed_seq = time.perf_counter() - t1

    print("\n=== Timing comparison ===")
    print(f"  Parallel   ({len(QUERIES)} queries): {elapsed_parallel:.1f}s")
    print(f"  Sequential (2 queries) : {elapsed_seq:.1f}s")
    print(f"  Estimated sequential {len(QUERIES)} queries: ~{elapsed_seq / 2 * len(QUERIES):.1f}s")


asyncio.run(main())
