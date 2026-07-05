"""
13 — Context Manager vs Manual Lifecycle

Four patterns for managing client and conversation lifetimes:
  1. async with BraveClient   — simplest, safest
  2. manual client lifecycle  — reuse one client across many queries
  3. Conversation as context manager
  4. retrieving the share link from a conversation
"""

import asyncio

from brave_api import BraveClient
from brave_api.conversation import Conversation


async def pattern_context_manager() -> None:
    """Pattern 1: async with — recommended for most use cases."""
    print("=== Pattern 1: async with BraveClient ===")
    async with BraveClient() as client:
        result = await client.ask("apa itu docker?")
        print(result.text[:200])


async def pattern_manual_client() -> None:
    """Pattern 2: manual open/close — useful when reusing one client."""
    print("\n=== Pattern 2: manual client lifecycle ===")
    client = BraveClient()
    try:
        await client._http.__aenter__()
        await client._prime()

        r1 = await client.ask("python vs go performance")
        print(f"Query 1: {r1.text[:150]}...")

        r2 = await client.ask("rust vs cpp safety")
        print(f"Query 2: {r2.text[:150]}...")
    finally:
        await client.close()


async def pattern_conversation_context() -> None:
    """Pattern 3: Conversation as context manager."""
    print("\n=== Pattern 3: Conversation context manager ===")
    async with BraveClient() as client:
        async with Conversation(client, "apa itu kubernetes?") as conv:
            print(f"Conv ID : {conv.id}")
            result = await conv.collect()
            print(result.text[:200])
        # After __aexit__, id is cleared
        print(f"is_open after exit: {conv.is_open}")


async def pattern_share_link() -> None:
    """Pattern 4: retrieve the conversation share link."""
    print("\n=== Pattern 4: Share Link ===")
    async with BraveClient() as client:
        conv = await client.conversation("manfaat belajar bahasa pemrograman")
        result = await conv.collect()
        print(f"Answer  : {result.text[:150]}...")
        print(f"Conv ID : {conv.id}")
        if conv.share_link:
            print(f"Share   : {conv.share_link}")
        if conv.open_modal_link:
            print(f"Modal   : {conv.open_modal_link}")


async def main() -> None:
    await pattern_context_manager()
    await pattern_manual_client()
    await pattern_conversation_context()
    await pattern_share_link()


asyncio.run(main())
