"""
06 — Client Configuration

Demonstrates the various ClientConfig options: language, region,
safesearch, units, timeouts, research mode, and browser fingerprinting.
"""

import asyncio

from brave_api import BraveClient, ClientConfig


async def demo(label: str, config: ClientConfig, query: str) -> None:
    async with BraveClient(config) as client:
        result = await client.ask(query)
    print(f"\n{'=' * 60}")
    print(f"[{label}]")
    print(f"Query  : {query}")
    print(f"Answer : {result.text[:200]}...")
    print(f"Web    : {len(result.web_results)} results  |  Images: {len(result.images)}")


async def main() -> None:
    # Indonesian language + Jakarta geolocation
    await demo(
        "ID / Jakarta",
        ClientConfig(language="id", ui_lang="id-id", country="id", geoloc="-6.200x106.816"),
        "apa berita terbaru hari ini?",
    )

    # English with strict safe search
    await demo(
        "EN / Strict SafeSearch",
        ClientConfig(language="en", ui_lang="en-us", country="us", safesearch="strict"),
        "latest AI research papers",
    )

    # Imperial units + US location
    await demo(
        "US / Imperial Units",
        ClientConfig(language="en", country="us", ui_lang="en-us",
                     units_of_measurement="imperial", geoloc="40.712x-74.006"),
        "weather in New York today",
    )

    # Aggressive retry + short timeout
    await demo(
        "Fast Timeout / Aggressive Retry",
        ClientConfig(request_timeout_seconds=30.0, max_retries=5, retry_backoff_seconds=0.5),
        "python list comprehension tips",
    )

    # Deep Research mode
    await demo(
        "Deep Research",
        ClientConfig(enable_research=True, language="en"),
        "history of neural networks",
    )

    # Custom browser fingerprint
    await demo(
        "Firefox Fingerprint",
        ClientConfig(
            impersonate="firefox136",
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        ),
        "linux terminal productivity tips",
    )


asyncio.run(main())
