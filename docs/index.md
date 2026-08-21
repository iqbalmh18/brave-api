# brave-api-python

<img src="../brave-api.svg" alt="Adaptive animated brave-api-python banner" />

`brave-api-python` is an asynchronous, typed Python client for Brave Search and
Brave Ask. It also provides an MCP server so AI applications can call Brave
search as tools.

## Features

- Complete (`ask`) or incremental (`ask_stream`) AI answers
- Multi-turn conversations and image input
- Structured web, image, news, video, and Brave Goggles results
- Typed Pydantic models that are immutable after creation
- Automatic retries, proxy rotation, timeouts, and consistent exceptions
- MCP over stdio or HTTP

## Quick install

```bash
uv add brave-api-python
```

The following example is enough to try both APIs:

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

All network operations are asynchronous. Use `async with` so the HTTP session
is opened and closed safely.

## Learning path

- [Installation](installation.md): install with `uv`, `pip`, or from source.
- [Quickstart](quickstart.md): the smallest runnable examples.
- [Ask API](guides/ask.md): streaming, images, and question options.
- [Search API](guides/search.md): verticals, pagination, and autocomplete.
- [Configuration](guides/configuration.md): language, retries, timeouts, and proxies.
- [Troubleshooting](guides/troubleshooting.md): lifecycle, errors, and reliability.
- [Conversations](guides/conversations.md): follow-up questions.
- [MCP server](guides/mcp.md): use the package from an MCP application.
- [API Reference](api.md): every public class, method, model, enum, and exception.
