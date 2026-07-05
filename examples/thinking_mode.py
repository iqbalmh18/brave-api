"""
16 — Thinking Mode

On complex reasoning queries the model emits THINKING_DELTA events
before the final TEXT_DELTA answer. This example streams both
in real time and prints a summary at the end.
"""

import asyncio

from brave_api import BraveClient, StreamEventType

# A math/logic problem that typically triggers chain-of-thought reasoning
QUERY = (
    "Jika sebuah kereta berangkat dari Jakarta pukul 08:00 dengan "
    "kecepatan 120 km/jam, dan kereta lain berangkat dari Surabaya "
    "pukul 09:00 dengan kecepatan 90 km/jam, jarak Jakarta-Surabaya "
    "800 km, di mana dan kapan keduanya bertemu?"
)


async def main() -> None:
    async with BraveClient() as client:
        conv = await client.conversation(QUERY, language="id", ui_lang="id-id")

        print("=== Streaming with thinking ===\n")
        thinking_parts: list[str] = []
        text_parts: list[str] = []

        async for event in conv.stream_events():
            if event.type is StreamEventType.THINKING_START:
                print("[THINKING START]")

            elif event.type is StreamEventType.THINKING_DELTA:
                thinking_parts.append(event.delta)
                print(f"  {event.delta}", end="", flush=True)

            elif event.type is StreamEventType.THINKING_STOP:
                print("\n[THINKING STOP]")

            elif event.type is StreamEventType.TEXT_DELTA:
                text_parts.append(event.delta)
                print(event.delta, end="", flush=True)

            elif event.type is StreamEventType.TEXT_STOP:
                print()

    full_thinking = "".join(thinking_parts)
    full_text = "".join(text_parts)

    print("\n=== Summary ===")
    print(f"Thinking ({len(full_thinking)} chars):")
    print(full_thinking[:400] if full_thinking else "  (no thinking emitted)")

    print(f"\nAnswer ({len(full_text)} chars):")
    print(full_text[:400])


asyncio.run(main())
