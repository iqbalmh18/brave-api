"""
11 — Exception Handling

All exceptions inherit from BraveAPIError.
This example catches each exception type and shows how to inspect
stream state after a completed (or failed) collect() call.
"""

import asyncio

from brave_api import BraveClient, ClientConfig
from brave_api.exceptions import (
    BraveAPIError,
    ChallengeRequiredError,
    ConversationError,
    HTTPStatusError,
    StreamAbortedError,
    TokenExtractionError,
    TransportError,
)


async def safe_ask(client: BraveClient, query: str) -> str | None:
    """Run a query and handle every possible error type."""
    try:
        result = await client.ask(query)
        return result.text

    except ChallengeRequiredError:
        # Brave detected a bot and sent a CAPTCHA challenge
        print("[ERROR] CAPTCHA required — try a different IP or wait.")
        return None

    except HTTPStatusError as e:
        print(f"[ERROR] HTTP {e.status_code}: {e}")
        return None

    except TransportError as e:
        # Network error, connection reset, timeout, etc.
        print(f"[ERROR] Transport: {e}")
        return None

    except TokenExtractionError as e:
        # Server SSR format changed — token could not be parsed
        print(f"[ERROR] Token extraction failed: {e}")
        return None

    except ConversationError as e:
        # /api/tap/v1/new did not return a valid conversation id
        print(f"[ERROR] Could not open conversation: {e}")
        return None

    except StreamAbortedError as e:
        # Server sent an error event mid-stream
        print(f"[ERROR] Stream aborted: {e}")
        return None

    except BraveAPIError as e:
        # Catch-all for any other library error
        print(f"[ERROR] BraveAPI: {e}")
        return None


async def main() -> None:
    # Normal usage with error handling
    config = ClientConfig(request_timeout_seconds=20.0, max_retries=2, retry_backoff_seconds=1.0)
    async with BraveClient(config) as client:
        text = await safe_ask(client, "apa itu asyncio python?")
        if text:
            print("=== Answer ===")
            print(text[:400])

    # Inspect stream state from a successful collect()
    async with BraveClient() as client:
        conv = await client.conversation("cara install docker di ubuntu")
        result = await conv.collect()

        print(f"\n=== Stream state: {result.state} ===")
        print(f"is_complete  : {result.is_complete}")
        print(f"has_images   : {result.has_images}")
        print(f"has_videos   : {result.has_videos}")
        print(f"has_tools    : {result.has_tool_calls}")

        # Event type breakdown — useful for debugging
        breakdown: dict[str, int] = {}
        for event in result.raw_events:
            breakdown[event.raw_type] = breakdown.get(event.raw_type, 0) + 1

        print("\nEvent breakdown:")
        for t, n in sorted(breakdown.items()):
            print(f"  {t}: {n}x")


asyncio.run(main())
