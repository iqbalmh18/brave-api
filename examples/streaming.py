"""Stream events in real time.

Demonstrates ``Conversation.stream_events()``: text deltas arrive one token
at a time (typewriter output), ``thinking_*`` events carry the model's
chain-of-thought, and ``tool_use`` events are auto-executed when
``auto_tools=True`` (the default).
"""

import asyncio

from brave_api import BraveClient, StreamEventType


async def main() -> None:
    async with BraveClient() as client:
        conversation = await client.conversation("what is quantum computing?")

        async for event in conversation.stream_events():
            if event.type is StreamEventType.TEXT_DELTA:
                print(event.delta, end="", flush=True)
            elif event.type is StreamEventType.THINKING_DELTA:
                print(f"\n[thinking] {event.delta}", end="", flush=True)
            elif event.type is StreamEventType.TEXT_STOP:
                print()
            elif event.type is StreamEventType.ERROR:
                print(f"\n[error] {event.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
