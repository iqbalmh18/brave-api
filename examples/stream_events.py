"""
02 — Stream Events

Consume the raw SSE event stream token by token.
Useful for typewriter-style output or processing events as they arrive.
"""

import asyncio
from collections import Counter

from brave_api import BraveClient, StreamEventType


async def main() -> None:
    async with BraveClient() as client:
        conv = await client.conversation("jelaskan cara kerja transformer model", language="id")

        event_counts: Counter[str] = Counter()

        print("Response (streaming):")
        async for event in conv.stream_events():
            event_counts[event.raw_type] += 1

            if event.type is StreamEventType.TEXT_DELTA:
                print(event.delta, end="", flush=True)

            elif event.type is StreamEventType.THINKING_DELTA:
                # Thinking tokens are printed inline when the model reasons
                print(f"[thinking] {event.delta}", end="", flush=True)

            elif event.type is StreamEventType.TEXT_STOP:
                print("\n")

            elif event.type is StreamEventType.ERROR:
                print(f"[ERROR] {event.error_message}")

    print("Event breakdown:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}x")


asyncio.run(main())
