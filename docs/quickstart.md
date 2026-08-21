# Quickstart

Run the examples from a Python file. Because client methods are asynchronous,
define `main` with `async def` and call it with `asyncio.run`.

## Ask

```python
import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("Explain DNSSEC")
    print(result.text)


asyncio.run(main())
```

## Search

```python
async with BraveClient() as client:
    result = await client.search("Python asyncio tutorial")

for item in result.web[:5]:
print(item.title, item.url)
```

All public client calls are async. Use `async with BraveClient()` to manage the
HTTP session safely.

`ask()` returns a `StreamResult`; `search()` returns a `SearchResult`. Both are
Pydantic models: use dot notation for fields and `.model_dump()` for a dict.
