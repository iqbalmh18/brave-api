# Brave API

<img src="./brave-api.svg" alt="Brave API banner" />

<p align="center">
An async Python client for <a href="https://search.brave.com">Brave Search</a>, providing streaming AI answers and structured web search in a single, typed interface.
</p>

<p align="center"><em>Not affiliated with or endorsed by Brave Software.</em></p>

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Ask](#ask)
- [Search](#search)
- [Client Configuration](#client-configuration)
- [Conversation](#conversation)
- [Streaming Events](#streaming-events)
- [StreamResult](#streamresult)
- [Error Handling](#error-handling)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [Star History](#star-history)
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

**General**

- Async-native, built on `curl_cffi` with browser fingerprinting (no API key required)
- Full Pydantic models for runtime validation and type safety
- Structured exception hierarchy for predictable error handling
- Configurable language, country, safesearch, geolocation, timeouts, and retries

---

## Requirements

- Python 3.11+
- Dependencies: `curl-cffi`, `pydantic`, `pillow`

---

## Installation

```bash
uv pip install git+https://github.com/iqbalmh18/brave-api.git
```

From source:

```bash
git clone https://github.com/iqbalmh18/brave-api
cd brave-api
uv pip install -e ".[dev]"
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

    # Browser fingerprinting
    impersonate="chrome136",
    extra_headers={"X-Custom": "value"},
)

async with BraveClient(config) as client:
    ...
```

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

---

## Project Structure

```
brave_api/
├── __init__.py                 # All public exports
├── client.py                   # BraveClient - main facade
├── conversation.py             # Conversation - single conversation turn
├── _crypto
│   └── keys.py                 # AES-256 symmetric key generation
├── exceptions.py               # Exception hierarchy
├── _internal
│   ├── config.py               # ClientConfig (Pydantic, frozen)
│   ├── constants.py            # Global constants
│   ├── models.py               # Data models (ImageResult, WebResult, etc.)
│   ├── token_extractor.py      # SSR token extractor
│   └── types.py                # Enums, Protocol
├── py.typed
├── _search
│   └── parser.py               # HTML parser for search() and suggest()
├── _streaming
│   ├── parser.py               # SSE line -> StreamEvent
│   └── result.py               # StreamAccumulator
└── _transport
    ├── http.py                 # HTTPClient (curl_cffi wrapper)
    └── retry.py                # Exponential backoff retry
```

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

---

## Star History

<a href="https://star-history.com/#iqbalmh18/brave-api&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=iqbalmh18/brave-api&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=iqbalmh18/brave-api&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=iqbalmh18/brave-api&type=Date" />
  </picture>
</a>

---

## License

This project is licensed under the terms of the license found in the [LICENSE](https://github.com/iqbalmh18/brave-api/blob/main/LICENSE) file.