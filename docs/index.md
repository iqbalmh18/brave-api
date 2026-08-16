# brave-api-python

Async, typed Python client for Brave Search and Brave Ask, with a built-in
Model Context Protocol (MCP) server.

## Features

- Blocking and streaming AI answers
- Multimodal and multi-turn conversations
- Structured web, images, news, videos, and Brave Goggles search
- Typed immutable Pydantic models
- Retry, proxy rotation, and consistent exceptions
- MCP tools for local and HTTP deployments

## Quick install

```bash
uv add brave-api-python
```

## Minimal usage

```python
import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        answer = await client.ask("What is quantum computing?")
        print(answer.text)

        result = await client.search("Python asyncio tutorial")
        for item in result.web[:3]:
            print(item.title, item.url)


asyncio.run(main())
```

See the guides for complete usage and the API Reference for every public
class, method, model, enum, and exception.
