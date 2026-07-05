"""
05 — Multi-Turn Conversation

Continue a conversation across multiple turns by passing the
conversation_id and symmetric_key from the previous turn.
Also demonstrates answer regeneration with QueryType.REGENERATE_ANSWER.
"""

import asyncio

from brave_api import BraveClient, QueryType


async def main() -> None:
    async with BraveClient() as client:

        # --- Turn 1: open a new conversation ---
        conv1 = await client.conversation("apa itu rust programming language?")
        result1 = await conv1.collect()

        print("=== Turn 1 ===")
        print(result1.text[:400])
        print(f"\nConversation ID : {conv1.id}")
        print(f"Symmetric Key   : {conv1.symmetric_key}")

        # Save identifiers for subsequent turns
        conv_id = conv1.id
        sym_key = conv1.symmetric_key

        await conv1.close()

        # --- Turn 2: follow-up in the same conversation ---
        conv2 = await client.conversation(
            "apa perbedaan ownership dengan borrow checker?",
            conversation_id=conv_id,
            symmetric_key=sym_key,
        )
        result2 = await conv2.collect()

        print("\n=== Turn 2 (follow-up) ===")
        print(result2.text[:400])

        # --- Turn 3: regenerate the last answer ---
        conv3 = await client.conversation(
            "apa perbedaan ownership dengan borrow checker?",
            conversation_id=conv_id,
            symmetric_key=sym_key,
            query_type=QueryType.REGENERATE_ANSWER,
        )
        result3 = await conv3.collect()

        print("\n=== Turn 3 (regenerate) ===")
        print(result3.text[:400])


asyncio.run(main())
