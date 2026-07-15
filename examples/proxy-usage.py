"""
Proxy Pool Usage

Set BRAVE_PROXY_LIST to comma-separated proxy URLs before running:

    BRAVE_PROXY_LIST='http://user:pass@proxy-1:8080,socks5://proxy-2:1080' \
        uv run python examples/proxy-usage.py

The client rotates active proxies per request. A proxy that fails to connect is
disabled, and the client continues directly when no active proxy remains.
"""

import asyncio
import logging
import os

from brave_api import BraveClient, ClientConfig


def load_proxy_list() -> list[str]:
    raw_proxies = os.environ.get("BRAVE_PROXY_LIST", "")
    return [proxy.strip() for proxy in raw_proxies.split(",") if proxy.strip()]


async def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    proxy_list = load_proxy_list()
    if proxy_list:
        print(f"Configured {len(proxy_list)} proxy/proxies.")
    else:
        print("BRAVE_PROXY_LIST is unset; using a direct connection.")

    config = ClientConfig(
        proxy_list=proxy_list,
        request_timeout_seconds=30.0,
    )
    for query in [
        "apa itu proxy",
        "apa itu proxy http dan https",
        "apa itu proxy socks4 dan socks5",
    ]:
        async with BraveClient(config) as client:
            result = await client.search(query=query)
            print(result)


asyncio.run(main())
