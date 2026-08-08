"""Handle every error the library can raise.

All exceptions inherit from :class:`BraveAPIError`. This example shows how
to distinguish transport, HTTP, parsing, and stream-level failures and how
to inspect a failed stream result.
"""

import asyncio

from brave_api import BraveClient
from brave_api.exceptions import (
    BraveAPIError,
    ChallengeRequiredError,
    HTTPStatusError,
    StreamAbortedError,
    TransportError,
)


async def ask_safely(client: BraveClient, query: str) -> str | None:
    """Ask a question and translate every failure into a message."""
    try:
        result = await client.ask(query)
        return result.text
    except ChallengeRequiredError:
        print("[error] CAPTCHA challenge — try a different IP or wait.")
    except HTTPStatusError as exc:
        print(f"[error] HTTP {exc.status_code}: {exc}")
    except TransportError as exc:
        print(f"[error] network failure: {exc}")
    except StreamAbortedError as exc:
        print(f"[error] stream aborted: {exc}")
    except BraveAPIError as exc:
        print(f"[error] {exc}")
    return None


async def main() -> None:
    async with BraveClient() as client:
        text = await ask_safely(client, "what is quantum computing?")
        if text:
            print(text[:300])


if __name__ == "__main__":
    asyncio.run(main())
