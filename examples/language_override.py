"""
07 — Language Override

The client auto-detects query language from stopword heuristics.
This example shows how to override it explicitly — via argument or
via conv.set_language() after the conversation object is created.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:

        # Auto-detect: Indonesian query → Indonesian response
        conv_auto = await client.conversation("jelaskan apa itu machine learning")
        result_auto = await conv_auto.collect()
        print("=== Auto-detect (ID) ===")
        print(result_auto.text[:300])

        # Force English response for the same Indonesian query
        conv_en = await client.conversation(
            "jelaskan apa itu machine learning",
            language="en",
            ui_lang="en-us",
        )
        result_en = await conv_en.collect()
        print("\n=== Override → English ===")
        print(result_en.text[:300])

        # English query but force Indonesian response via set_language()
        conv_obj = await client.conversation("what is machine learning")
        conv_obj.set_language("id", "id-id")
        result_id = await conv_obj.collect()
        print("\n=== English query + set_language('id') ===")
        print(result_id.text[:300])


asyncio.run(main())
