"""Manage the client lifecycle explicitly.

``async with`` is the recommended pattern, but when you own the lifecycle
yourself (for example in a long-lived worker), ``open()``/``close()`` are
the building blocks. Both are idempotent.
"""

import asyncio

from brave_api import BraveClient


async def main() -> None:
    client = BraveClient()
    try:
        await client.open()
        result = await client.ask("python vs go performance")
        print(result.text[:300])
    finally:
        await client.close()

    print("client open after close:", client.is_open)


if __name__ == "__main__":
    asyncio.run(main())
