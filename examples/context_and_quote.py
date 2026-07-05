"""
09 — Context and Quote

Pass an article or passage as context so the AI answers about it.
The optional quote parameter highlights a specific span of text,
mimicking the browser's text-selection feature.
"""

import asyncio

from brave_api import BraveClient

ARTICLE_CONTEXT = """
Rust adalah bahasa pemrograman sistem yang dikembangkan oleh Mozilla Research.
Rust dirancang untuk memberikan keamanan memori tanpa garbage collector melalui
sistem ownership dan borrow checker. Rust pertama kali dirilis secara stabil
pada tahun 2015 dan sejak saat itu menjadi salah satu bahasa paling populer
di kalangan developer sistem.
"""

HIGHLIGHTED_QUOTE = "sistem ownership dan borrow checker"


async def main() -> None:
    async with BraveClient() as client:

        # Context only — AI answers relative to the article
        conv_ctx = await client.conversation(
            "apa keunggulan utama bahasa ini?",
            context=ARTICLE_CONTEXT,
        )
        result_ctx = await conv_ctx.collect()
        print("=== Query with context ===")
        print(result_ctx.text[:500])

        # Context + quote — focuses the answer on the highlighted span
        conv_quote = await client.conversation(
            "jelaskan lebih detail",
            context=ARTICLE_CONTEXT,
            quote=HIGHLIGHTED_QUOTE,
        )
        result_quote = await conv_quote.collect()
        print("\n=== Query with context + quote ===")
        print(f"Quote: '{HIGHLIGHTED_QUOTE}'")
        print(result_quote.text[:500])


asyncio.run(main())
