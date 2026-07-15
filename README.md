# Brave API

<img src="./brave-api.svg" alt="Brave API banner" />

<p align="center">
An async Python client for <a href="https://search.brave.com">Brave Search</a>, providing streaming AI answers and structured web search in a single, typed interface — with a built-in Model Context Protocol (MCP) server.
</p>

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Ask](#ask)
- [Search](#search)
- [Client Configuration](#client-configuration)
- [Proxy Support](#proxy-support)
- [Conversation](#conversation)
- [Streaming Events](#streaming-events)
- [StreamResult](#streamresult)
- [Error Handling](#error-handling)
- [MCP Server](#mcp-server)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [License](#license)

---

## Features

**Ask (AI)**

- `client.ask()` — blocking call, returns a complete `StreamResult` with text, infobox, images, videos, web results, and followups
- `client.ask_stream()` — async generator that yields `StreamEvent` objects in real time
- Multi-turn conversation support via `conversation_id` and `symmetric_key`
- Multimodal input: attach images alongside questions (vision)
- Automatic query language detection, with manual override
- Automatic `run_tool` execution for web search, image fetch, and other tool calls

**Search (Web)**

- `client.search()` — scrape structured web and news results with pagination
- `client.suggest()` — autocomplete suggestions with entity detection

**MCP Server**

- Exposes `ask`, `search`, and `suggest` as MCP tools, ready to drop into Claude Desktop, Claude Code, Cursor, or any MCP-compatible client
- Supports both **stdio** (local clients) and **HTTP/SSE** (remote or multi-client deployments) transports
- Configured entirely through environment variables — no code changes required
- Shares the same typed client and error hierarchy as the library

**General**

- Async-native, built on `curl_cffi` with browser fingerprinting (no API key required)
- Full Pydantic models for runtime validation and type safety
- Structured exception hierarchy for predictable error handling
- Configurable language, country, safesearch, geolocation, timeouts, and retries
- Optional round-robin proxy pool with automatic direct-connection fallback

---

## Architecture

```mermaid
graph TD
    A[Your Application] -->|imports| B[BraveClient]
    C[MCP Client<br/>Claude Desktop / Claude Code / other] -->|stdio| D[Brave API MCP Server]
    G[OpenAI-compatible Client<br/>or remote agent] -->|HTTP / SSE| D
    D -->|ask / search / suggest| B
    B --> E[HTTPClient<br/>curl_cffi]
    E --> F[Brave Search / Brave AI]

    style B fill:#2b2b2b,stroke:#888,color:#fff
    style D fill:#2b2b2b,stroke:#888,color:#fff
    style F fill:#1a1a1a,stroke:#888,color:#fff
```

The library can be used directly in Python code, or indirectly through the MCP server, which wraps the same `BraveClient` and exposes it as tools for LLM-based agents.

---

## Requirements

- Python 3.11+
- Dependencies: `curl-cffi`, `pydantic`, `pillow`
- Optional (MCP server): `fastmcp`

---

## Installation

```bash
uv pip install brave-api-python
```

From source:

```bash
git clone https://github.com/iqbalmh18/brave-api
cd brave-api
uv pip install -e ".[dev]"
```

With MCP server support:

```bash
uv pip install "brave-api-python[mcp]"
```

---

## Quick Start

```python
import asyncio
from brave_api import BraveClient

async def main():
    async with BraveClient() as client:
        # AI answer
        result = await client.ask("what is quantum computing?")
        print(result.text)

        # Web search
        search = await client.search("python asyncio tutorial")
        for item in search.web:
            print(item.title, item.url)

asyncio.run(main())
```

---

## Ask

### ask() — blocking, full result

```python
async with BraveClient() as client:
    result = await client.ask("mount bromo indonesia")

print(result.text)           # AI answer text (markdown)

if result.infobox:
    print(result.infobox.title)      # "Mount Bromo"
    print(result.infobox.subtitle)   # "Active volcano in East Java"
    print(result.infobox.url)        # Wikipedia URL
    print(result.infobox.image_url)  # entity image

for img in result.images:
    print(img.url, img.thumbnail)

for vid in result.videos:
    print(vid.title, vid.url)

for web in result.web_results:
    print(web.title, web.url)

for q in result.followups:
    print(q)
```

With an image (vision/multimodal):

```python
from pathlib import Path

result = await client.ask("what is in this image?", image=Path("photo.jpg"))
```

### ask_stream() — real-time streaming

```python
async for event in client.ask_stream("what is Space X?"):
    if event.type is StreamEventType.TEXT_DELTA:
        print(event.delta, end="", flush=True)
    elif event.type is StreamEventType.TEXT_STOP:
        print()
    elif event.type is StreamEventType.FOLLOWUPS:
        for q in event.payload.get("followups", []):
            print(f"-> {q}")
```

### Comparison

| Method | Mode | Returns | Best for |
|---|---|---|---|
| `client.ask()` | Blocking | `StreamResult` | Full result at once (infobox, images, etc.) |
| `client.ask_stream()` | Streaming | `AsyncGenerator[StreamEvent]` | Typewriter output |
| `conversation()` + `collect()` | Blocking | `StreamResult` | Multi-turn, image input, full control |
| `conversation()` + `stream_events()` | Streaming | `AsyncGenerator[StreamEvent]` | Streaming + multi-turn |

---

## Search

### search() — web and news results

```python
async with BraveClient() as client:
    result = await client.search("python asyncio tutorial")

print(result.query)          # original query
print(len(result.web))       # number of web results
print(len(result.news))      # number of news results

for item in result.web:
    print(item.title)
    print(item.url)
    print(item.description)
    print(item.age)          # "2 days ago", etc.

for item in result.news:
    print(item.title, item.source, item.age)

# All unique URLs in a flat list
for url in result.urls:
    print(url)
```

Pagination:

```python
# Page 1 (default)
page1 = await client.search("rust programming", offset=0)

# Page 2
page2 = await client.search("rust programming", offset=1)
```

Disable spellcheck for exact keyword matching:

```python
result = await client.search("pyton tutorial", spellcheck=False)
```

### suggest() — autocomplete

```python
suggestions = await client.suggest("elon")
for s in suggestions:
    print(s.text, s.entity_type, s.is_entity)
    if s.thumbnail:
        print(s.thumbnail)
```

---

## Client Configuration

`ClientConfig` is a frozen Pydantic model. All fields have safe defaults.

```python
from brave_api import BraveClient, ClientConfig

config = ClientConfig(
    # Language and region
    language="id",                   # Response language: "id", "en", etc.
    ui_lang="id-id",                 # UI language: "id-id", "en-us", etc.
    country="id",                    # ISO 3166-1 country code
    geoloc="-6.200x106.816",         # lat x lng (Jakarta)

    # Search
    safesearch="moderate",           # "off", "moderate", or "strict"
    units_of_measurement="metric",   # "metric" or "imperial"

    # Mode
    enable_research=False,           # True = deep research mode

    # HTTP
    request_timeout_seconds=60.0,
    max_retries=3,
    retry_backoff_seconds=1.5,

    # Optional proxy pool
    proxy_list=[
        "http://user:password@proxy-1.example:8080",
        "socks5://proxy-2.example:1080",
    ],

    # Browser fingerprinting
    impersonate="chrome136",
    extra_headers={"X-Custom": "value"},
)

async with BraveClient(config) as client:
    ...
```

---

## Proxy Support

Pass proxy URLs through `ClientConfig(proxy_list=...)` to rotate proxy usage across requests. The pool is shared by Ask, Search, Suggest, and streaming requests.

```python
from brave_api import BraveClient, ClientConfig

config = ClientConfig(
    proxy_list=[
        "http://user:password@proxy-1.example:8080",
        "http://proxy-2.example:8080",
        "socks5://proxy-3.example:1080",
    ],
)

async with BraveClient(config) as client:
    result = await client.search("python asyncio tutorial")
```

Supported proxy schemes are `http`, `https`, `socks4`, `socks4a`, `socks5`, and `socks5h`. Proxy URLs are normalized and duplicate entries are removed when the configuration is created.

The client selects an active proxy using round-robin order for each request. A proxy that fails before a response or stream data is received is disabled for the lifetime of that client. The next active proxy is tried automatically; if none remain, the request continues with `curl_cffi` configured for a direct connection (`proxies=None`). HTTP responses from Brave, including `429` and `5xx`, do not disable a proxy.

Enable transport logs to see the selected proxy and fallback behavior. Proxy credentials are never included in these log messages.

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
```

See [`examples/proxy-usage.py`](examples/proxy-usage.py) for a runnable example that reads comma-separated proxy URLs from `BRAVE_PROXY_LIST`.

---

## Conversation

```python
async with BraveClient() as client:
    # New conversation
    conv = await client.conversation("explain how DNS works")
    result = await conv.collect()

    # Continue the same conversation
    conv2 = await client.conversation(
        "what is DNSSEC?",
        conversation_id=conv.id,
        symmetric_key=conv.symmetric_key,
    )
    result2 = await conv2.collect()
```

Key `conversation()` parameters:

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Question or prompt (required) |
| `conversation_id` | `str \| None` | Continue an existing conversation |
| `symmetric_key` | `str \| None` | Required when `conversation_id` is set |
| `image` | `bytes \| str \| Path \| None` | Image for multimodal input |
| `language` | `str \| None` | Override response language |
| `query_type` | `str` | See `QueryType` enum |
| `auto_tools` | `bool` | Auto-execute tool calls (default: `True`) |
| `context` | `str \| None` | Article/passage context |
| `quote` | `str \| None` | Highlighted text span |

---

## Streaming Events

```python
async for event in conv.stream_events():
    if event.type is StreamEventType.TEXT_DELTA:
        print(event.delta, end="", flush=True)
    elif event.type is StreamEventType.TEXT_STOP:
        print()
    elif event.type is StreamEventType.ERROR:
        print(f"Error: {event.error_message}")
```

Key event types:

```
TEXT_DELTA / TEXT_STOP                    response text tokens
THINKING_DELTA / THINKING_STOP            chain-of-thought reasoning
TOOL_USE                                  server requests a tool call
AUGMENT_WITH_TOOL_USE                     run_tool result (web results, images, etc.)
AUGMENT_WITH_WEB / NEWS / IMAGES / VIDEOS enrichment data
AUGMENT_WITH_INFOBOX                      entity knowledge card
FOLLOWUPS                                 suggested follow-up questions
ERROR                                     server error event
CHALLENGE                                 CAPTCHA required
```

The sequence below shows how these events flow during a single `ask()` call:

```mermaid
sequenceDiagram
    participant App
    participant Client as BraveClient
    participant Brave as Brave AI

    App->>Client: ask(query)
    Client->>Brave: POST /api/tap/v1/new
    Brave-->>Client: SSE stream

    loop until stream ends
        Brave-->>Client: TEXT_DELTA / THINKING_DELTA
        Brave-->>Client: AUGMENT_WITH_WEB / IMAGES / INFOBOX
    end

    Brave-->>Client: FOLLOWUPS
    Client-->>App: StreamResult
```

---

## StreamResult

```python
result = await conv.collect()

result.text            # str - full AI answer (markdown)
result.thinking         # str - chain-of-thought reasoning (if any)
result.urls             # list[str] - unique URLs found
result.images           # list[ImageResult]
result.videos           # list[VideoResult]
result.web_results      # list[WebResult]
result.infobox          # Infobox | None
result.followups        # list[str]
result.citations        # list[dict] - raw tool result payloads
result.inline_entities  # list[dict]
result.raw_events       # list[StreamEvent] - every event for debugging
result.state            # StreamState enum
result.is_complete      # bool
result.has_images       # bool
result.has_videos       # bool
result.has_infobox      # bool
result.has_tool_calls   # bool
```

---

## Error Handling

All exceptions inherit from `BraveAPIError`.

```
BraveAPIError
├── TransportError          network error, timeout, connection reset
├── HTTPStatusError         non-2xx HTTP response (.status_code, .response_text)
├── TokenExtractionError    could not parse auth token from server HTML
├── ConversationError       /api/tap/v1/new did not return a conversation id
├── StreamAbortedError      server sent an error event mid-stream
├── ChallengeRequiredError  server sent a CAPTCHA challenge
└── InvalidResponseError    response was not valid JSON or unexpected shape
```

```python
from brave_api.exceptions import (
    BraveAPIError, ChallengeRequiredError, HTTPStatusError,
    StreamAbortedError, TransportError,
)

try:
    async with BraveClient() as client:
        result = await client.ask("what is rust?")
except ChallengeRequiredError:
    print("CAPTCHA required")
except HTTPStatusError as e:
    print(f"HTTP {e.status_code}: {e.response_text[:200]}")
except TransportError as e:
    print(f"Network error: {e}")
except StreamAbortedError as e:
    print(f"Stream aborted: {e}")
except BraveAPIError as e:
    print(f"Error: {e}")
```

Retry strategy: HTTP 429 and 5xx responses are retried with exponential backoff (`backoff_seconds * 2^attempt`).

The MCP server reuses this same hierarchy: any `BraveAPIError` raised by the client is caught and surfaced to the calling MCP client as a `ToolError`, so agents receive a clean, descriptive message instead of a raw stack trace.

---

## MCP Server

<img src="./brave-api-mcp.svg" alt="Brave API MCP banner" />

Brave API ships with a [Model Context Protocol](https://modelcontextprotocol.io) server built on [FastMCP](https://gofastmcp.com), exposing the client's core capabilities as tools for any MCP-compatible agent (Claude Desktop, Claude Code, Cursor, etc.).

### Tools

| Tool | Description | Read-only |
|---|---|---|
| `ask` | Ask Brave AI a question and receive a complete AI-generated answer with citations, source URLs, images, videos, and follow-up suggestions | Yes |
| `search` | Search Brave and return structured web and news results (raw SERP, no AI answer) | Yes |
| `suggest` | Fetch autocomplete suggestions for a partial query, including rich entity suggestions with thumbnails | Yes |

### Running the server

**stdio** (default — for local clients like Claude Desktop, Claude Code, Cursor):

```bash
python -m brave_api.mcp.server
# or via the CLI entry-point
brave-api-mcp
```

The server communicates over stdio and is meant to be launched by an MCP client, not run standalone in a terminal for interactive use.

**HTTP** (for remote or multi-client deployments, OpenAI-compatible clients):

```bash
brave-api-mcp --http
# bind to a specific host/port
brave-api-mcp --http --host 0.0.0.0 --port 8000
```

Full CLI reference:

```
usage: brave-api-mcp [-h] [--http] [--host HOST] [--port PORT]
                     [--log-level {debug,info,warning,error,critical}]

options:
  --http              Run with HTTP/SSE transport instead of stdio.
  --host HOST         Host address to bind to (HTTP transport only). [default: 127.0.0.1]
  --port PORT         Port to bind to (HTTP transport only). [default: 8000]
  --log-level LEVEL   Logging level. [default: warning]
```

### Configuring an MCP client

**Claude Desktop / Claude Code** (`claude_desktop_config.json` or `~/.claude/claude_code_config.json`):

```json
{
  "mcpServers": {
    "brave-api": {
      "command": "python",
      "args": ["-m", "brave_api.mcp.server"],
      "env": {
        "BRAVE_COUNTRY": "id",
        "BRAVE_LANGUAGE": "id",
        "BRAVE_SAFESEARCH": "moderate"
      }
    }
  }
}
```

Or via the Claude Code CLI:

```bash
claude mcp add brave-api python -- -m brave_api.mcp.server
```

**OpenAI-compatible clients / remote deployments** — start the server in HTTP mode and point the client at the endpoint:

```bash
brave-api-mcp --http --host 0.0.0.0 --port 8000
```

The server exposes a standard MCP-over-HTTP (Streamable HTTP / SSE) endpoint at `http://<host>:<port>/mcp`. Any client that supports the MCP HTTP transport can connect to it directly.

### Environment variables

All server behavior is controlled through environment variables — no code changes required.

| Variable | Default | Description |
|---|---|---|
| `BRAVE_BASE_URL` | `https://search.brave.com` | Base URL for the Brave endpoints |
| `BRAVE_GEOLOC` | library default | Geolocation as `lat x lng` |
| `BRAVE_COUNTRY` | library default | ISO 3166-1 country code |
| `BRAVE_LANGUAGE` | library default | Response language (BCP-47) |
| `BRAVE_UI_LANG` | library default | UI language, e.g. `en-us` |
| `BRAVE_SAFESEARCH` | library default | `off`, `moderate`, or `strict` |
| `BRAVE_ENABLE_RESEARCH` | `false` | `true`/`false`/`1`/`0`/`yes`/`no` — enables deep research mode |
| `BRAVE_REQUEST_TIMEOUT` | library default | Request timeout in seconds |
| `BRAVE_MAX_RETRIES` | library default | Maximum retry attempts on transient failures |
| `BRAVE_MAX_CONCURRENT` | library default | Maximum concurrent requests |

Invalid numeric or boolean values fall back to their defaults, with a warning logged rather than raising an error at startup.

### Error surface

Every tool call is wrapped so that any `BraveAPIError` raised by the underlying client is converted into an MCP `ToolError` with the original message, keeping error handling consistent between direct library use and MCP-based use.

---

## Examples

| File | Description |
|---|---|
| `examples/quick_start.py` | Simplest usage - ask and print |
| `examples/stream_events.py` | Real-time token streaming |
| `examples/web_results_and_urls.py` | Web results, thumbnails, URLs |
| `examples/images_and_videos.py` | Image and video results |
| `examples/multi_turn_conversation.py` | Multi-turn + answer regeneration |
| `examples/client_config.py` | All ClientConfig options |
| `examples/language_override.py` | Auto-detect vs explicit language |
| `examples/multimodal_image_input.py` | Vision - attach image to query |
| `examples/context_and_quote.py` | Context and quote parameters |
| `examples/auto_tools_control.py` | auto_tools=True vs False |
| `examples/exception_handling.py` | All exception types + stream state |
| `examples/inline_entities_and_citations.py` | Inline entities and tool citations |
| `examples/context_manager_vs_manual.py` | Client lifecycle patterns |
| `examples/raw_events_inspection.py` | Inspect every raw event |
| `examples/thinking_mode.py` | Chain-of-thought reasoning |
| `examples/interactive_chat.py` | Terminal REPL chat |
| `examples/ask_method.py` | ask() and ask_stream() demos |
| `examples/search_method.py` | search() and suggest() |
| `examples/proxy-usage.py` | Proxy pool rotation, fallback, and transport logging |

---

## License

This project is licensed under the terms of the license found in the [LICENSE](https://github.com/iqbalmh18/brave-api/blob/main/LICENSE) file.
