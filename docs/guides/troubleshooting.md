# Troubleshooting and reliability

## Check the connection first

Use `health_check()` for a lightweight connectivity check. It returns `False`
instead of raising an exception, so it is useful for readiness endpoints:

```python
async with BraveClient() as client:
    if not await client.health_check():
        raise RuntimeError("Brave Search is not reachable")
```

This only proves that the configured base URL responded. It does not guarantee
that a particular Ask or Search operation will succeed.

## Understand the lifecycle

The recommended pattern is an async context manager:

```python
async with BraveClient() as client:
    result = await client.search("Python")
```

For applications that own a longer lifecycle, call `open()` once and `close()`
when shutting down:

```python
client = BraveClient()
await client.open()
try:
    result = await client.ask("What is Python?")
finally:
    await client.close()
```

Do not create a new client for every item in a loop. Reuse one client so its
HTTP session, connection limits, retry policy, and proxy pool can work as
intended. `client.is_open` reports the current session state.

## Errors and retries

The library retries eligible transient failures up to `max_retries` times with
exponential backoff. It does not make every error safe to retry. Catch the
most specific exception your application can handle:

```python
from brave_api import (
    BraveAPIError,
    HTTPStatusError,
    ResponseParseError,
    TransportError,
)

try:
    async with BraveClient() as client:
        result = await client.search("Python")
except HTTPStatusError as error:
    print(error.status_code, error)
except (TransportError, ResponseParseError) as error:
    print(f"Temporary or upstream format problem: {error}")
except BraveAPIError as error:
    print(f"Other Brave API problem: {error}")
```

`ChallengeRequiredError` generally means the upstream requested a browser
challenge. `ConversationError` and `StreamAbortedError` indicate a failed
conversation or interrupted stream. Avoid logging credentials, proxy passwords,
raw cookies, or complete raw event payloads in production.

## Common causes

| Symptom | What to check |
|---|---|
| `ModuleNotFoundError` | Install in the same environment used by `uv run`. |
| Timeout | Increase `timeout` or set `stream_timeout`; check network/proxy. |
| HTTP 403 or challenge | Verify upstream availability and request identity; retrying alone may not help. |
| Empty result list | Check the correct vertical field and inspect `has_results`. |
| Wrong language | Set both `language` and `ui_lang` explicitly. |
| Proxy failure | Validate the scheme and host; supported schemes include HTTP(S), SOCKS4, and SOCKS5. |
| MCP tool error | Run with `--log-level info` and validate environment variables. |

## Live service boundary

Unit tests use fake transports and fixtures. They validate parsing, lifecycle,
retry, and model behavior without depending on the live service. A successful
test run therefore does not guarantee that Brave's current upstream response,
rate limits, or challenge policy will remain unchanged.
