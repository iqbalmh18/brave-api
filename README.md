<img src="./brave-api.svg" alt="Brave API" />

<p align="center">
  <a href="https://pypi.org/project/brave-api-python/">
    <img src="https://img.shields.io/pypi/v/brave-api-python.svg?style=flat&labelColor=0d1117&color=fe7039" alt="PyPI version" />
  </a>
  <a href="https://pypi.org/project/brave-api-python/">
    <img src="https://img.shields.io/pypi/pyversions/brave-api-python.svg?style=flat&labelColor=0d1117&color=fe7039" alt="Python versions" />
  </a>
  <a href="https://github.com/iqbalmh18/brave-api/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/iqbalmh18/brave-api/ci.yml?style=flat&labelColor=0d1117&color=fe7039&label=CI" alt="CI" />
  </a>
  <a href="https://python-semantic-release.readthedocs.io/">
    <img src="https://img.shields.io/badge/semantic--release-enabled-fe7039?style=flat&labelColor=0d1117" alt="Semantic release" />
  </a>
  <a href="https://brave-api.readthedocs.io/">
    <img src="https://img.shields.io/readthedocs/brave-api.svg?style=flat&labelColor=0d1117&color=fe7039" alt="Documentation" />
  </a>
  <a href="https://github.com/iqbalmh18/brave-api/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/iqbalmh18/brave-api.svg?style=flat&labelColor=0d1117&color=fe7039" alt="License" />
  </a>
  <a href="https://github.com/iqbalmh18/brave-api">
    <img src="https://img.shields.io/badge/typing-typed-fe7039?style=flat&labelColor=0d1117" alt="Typed Python" />
  </a>
</p>

<p align="center">
An async Python client for <a href="https://search.brave.com">Brave Search</a>, providing streaming AI answers and structured web search in a single, typed interface - with a built-in Model Context Protocol (MCP) server.
</p>

---

## Features

- Async Brave Ask client with blocking and streaming responses
- Multi-turn conversations and multimodal image input
- Structured search for web, images, news, videos, and Brave Goggles
- Pagination, autocomplete suggestions, and typed Pydantic models
- Configurable language, region, safe search, timeout, retries, and proxies
- FastMCP server with stdio and HTTP transports

## Documentation

The complete documentation is available at
[brave-api.readthedocs.io](https://brave-api.readthedocs.io/).

It includes detailed guides, configuration, MCP setup, examples, error
handling, and the generated API reference.

## Installation

Requires Python 3.11+.

```bash
uv add brave-api-python
```

For MCP support:

```bash
uv add "brave-api-python[mcp]"
```

With pip:

```bash
pip install brave-api-python
```

From source:

```bash
git clone https://github.com/iqbalmh18/brave-api.git
cd brave-api
uv sync --group dev
```

## Quick start

### Ask

```python
import asyncio

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("What is quantum computing?")

    print(result.text)
    print(f"Sources: {len(result.urls)}")


asyncio.run(main())
```

### Search

```python
async with BraveClient() as client:
    result = await client.search("Python asyncio tutorial")

for item in result.web[:3]:
    print(item.title, item.url)
```

All public methods are asynchronous and should normally be used inside
`async with BraveClient()`.

## Search verticals

Every search method returns the same `SearchResult` response envelope:

```python
async with BraveClient() as client:
    web = await client.search("Python asyncio")
    images = await client.search_images("Python logo")
    news = await client.search_news("Python release")
    videos = await client.search_videos("Python tutorial")
    goggles = await client.search_goggles("privacy search")

print(web.web)
print(images.images)
print(news.news)
print(videos.videos)
print(goggles.web)
```

Pagination uses Brave's page-based `offset` value, where `0` is the first page:

```python
async with BraveClient() as client:
    first_page = await client.search_news("Python release", offset=0)
    second_page = await client.search_news("Python release", offset=1)
```

Use `spellcheck=False` for exact keyword matching. Use `client.suggest()` for
autocomplete suggestions.

## Streaming

```python
from brave_api import BraveClient, StreamEventType

async with BraveClient() as client:
    async for event in client.ask_stream("Explain WebAssembly"):
        if event.type is StreamEventType.TEXT_DELTA:
            print(event.delta, end="", flush=True)
```

## Configuration

```python
from brave_api import BraveClient, ClientConfig

config = ClientConfig(
    language="id",
    ui_lang="id-id",
    country="id",
    safesearch="moderate",
    timeout=60.0,
    max_retries=3,
    proxies=["http://user:password@proxy.example:8080"],
)

async with BraveClient(config) as client:
    result = await client.search("berita teknologi")
```

See the [configuration guide](https://brave-api.readthedocs.io/en/latest/guides/configuration/)
for all supported options.

## MCP server

Install the optional MCP dependency:

```bash
uv add "brave-api-python[mcp]"
```

Run locally over stdio:

```bash
brave-api-mcp
```

Or run an HTTP server:

```bash
brave-api-mcp --http --host 127.0.0.1 --port 8000
```

Available search tools include `search`, `search_images`, `search_news`,
`search_videos`, `search_goggles`, and `suggest`, in addition to `ask`.

## Examples

Runnable examples are available in [`examples/`](examples/):

- [`search_verticals.py`](examples/search_verticals.py) — all search verticals and pagination
- [`search_suggest.py`](examples/search_suggest.py) — web search and autocomplete
- [`streaming.py`](examples/streaming.py) — streaming events
- [`multimodal.py`](examples/multimodal.py) — image input
- [`configuration.py`](examples/configuration.py) — configuration and proxies

Run one with:

```bash
uv run python examples/search_verticals.py
```

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

For API details, error handling, conversations, and complete MCP configuration,
see the [full documentation](https://brave-api.readthedocs.io/).

## Star History

<a href="https://www.star-history.com/?repos=iqbalmh18%2Fbrave-api&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=iqbalmh18/brave-api&type=date&theme=dark&legend=top-left&sealed_token=ayDqZU850vGmWyV1GfE9kdb8uBFENPOtRixuvpOJ4E4UaJAtQ5XxwHAZM3SQD8REeNFlJuCL41ARHltPqzIW0HvNXSQKpN3sXNMxDj4xnE0jTpivrLPhjA" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=iqbalmh18/brave-api&type=date&legend=top-left&sealed_token=ayDqZU850vGmWyV1GfE9kdb8uBFENPOtRixuvpOJ4E4UaJAtQ5XxwHAZM3SQD8REeNFlJuCL41ARHltPqzIW0HvNXSQKpN3sXNMxDj4xnE0jTpivrLPhjA" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=iqbalmh18/brave-api&type=date&legend=top-left&sealed_token=ayDqZU850vGmWyV1GfE9kdb8uBFENPOtRixuvpOJ4E4UaJAtQ5XxwHAZM3SQD8REeNFlJuCL41ARHltPqzIW0HvNXSQKpN3sXNMxDj4xnE0jTpivrLPhjA" />
 </picture>
</a>

## License

MIT. See [LICENSE](LICENSE).
