"""Multi-turn conversations: resume, follow up, and regenerate.

A conversation is identified by its ``(id, symmetric_key)`` pair. Pass both
back to continue the same conversation, and use
``QueryType.REGENERATE_ANSWER`` to request a fresh draft of the last answer.
"""

import asyncio

from brave_api import BraveClient, QueryType


async def main() -> None:
    async with BraveClient() as client:
        turn1 = await client.conversation("what is rust ownership?")
        result1 = await turn1.collect()
        print(f"Turn 1: {result1.text[:200]}\n")
        print(f"Conversation id: {turn1.id}")

        # Continue in the same conversation
        turn2 = await client.conversation(
            "how does the borrow checker work?",
            conversation_id=turn1.id,
            symmetric_key=turn1.symmetric_key,
        )
        result2 = await turn2.collect()
        print(f"\nTurn 2 (follow-up): {result2.text[:200]}")

        # Regenerate the last answer
        turn3 = await client.conversation(
            "how does the borrow checker work?",
            conversation_id=turn1.id,
            symmetric_key=turn1.symmetric_key,
            query_type=QueryType.REGENERATE_ANSWER,
        )
        result3 = await turn3.collect()
        print(f"\nTurn 3 (regenerated): {result3.text[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
