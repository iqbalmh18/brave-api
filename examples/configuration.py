"""Configure the client: language, region, safety, timeouts, and proxies.

:class:`ClientConfig` is a validated, frozen model. This example shows the
options that matter most, including proxy rotation from the
``BRAVE_PROXY_LIST`` environment variable.
"""

import asyncio
import os

from brave_api import BraveClient, ClientConfig


def proxies_from_env() -> list[str]:
    raw = os.getenv("BRAVE_PROXY_LIST", "")
    return [proxy.strip() for proxy in raw.split(",") if proxy.strip()]


async def main() -> None:
    config = ClientConfig(
        language="en",
        ui_lang="en-us",
        country="us",
        safesearch="strict",
        timeout=30.0,
        max_retries=3,
        retry_backoff=1.0,
        proxies=proxies_from_env(),
    )

    async with BraveClient(config) as client:
        result = await client.ask("latest AI research papers")

    print(f"Answer: {result.text[:200]}...")
    print(f"Proxies in rotation: {len(config.proxies)}")
    print(f"Max concurrent requests: {config.max_concurrent}")


if __name__ == "__main__":
    asyncio.run(main())
