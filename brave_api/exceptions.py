"""Exception hierarchy for brave_api.

Every error raised by the library derives from :class:`BraveAPIError`, so
callers can catch one base type and still distinguish failure classes.

Layout::

    BraveAPIError
    ├── TransportError          network failure, timeout, connection reset
    ├── HTTPStatusError         non-2xx response (.status_code, .response_text)
    ├── ResponseParseError      response was not valid JSON or had an unexpected shape
    ├── TokenExtractionError    could not extract the auth token from server HTML
    ├── ConversationError       /api/tap/v1/new did not return a conversation id
    ├── StreamAbortedError      server sent an error event mid-stream
    └── ChallengeRequiredError  server sent a CAPTCHA challenge
"""

from __future__ import annotations


class BraveAPIError(Exception):
    """Base class for every exception raised by brave_api."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TransportError(BraveAPIError):
    """A network-level failure: connection refused, reset, timeout, DNS, TLS."""


class HTTPStatusError(BraveAPIError):
    """The server responded with a non-2xx status."""

    status_code: int

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_text: str = "",
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.response_text = response_text


class ResponseParseError(BraveAPIError):
    """The response body was not valid JSON or had an unexpected shape."""


class TokenExtractionError(BraveAPIError):
    """The auth token ``{q, nonce, sig}`` could not be found in the payload."""


class ConversationError(BraveAPIError):
    """The conversation endpoint did not return a usable conversation id."""


class StreamAbortedError(BraveAPIError):
    """The server sent an error event while the stream was being consumed."""


class ChallengeRequiredError(BraveAPIError):
    """The server raised a CAPTCHA challenge that must be solved manually."""


__all__ = [
    "BraveAPIError",
    "ChallengeRequiredError",
    "ConversationError",
    "HTTPStatusError",
    "ResponseParseError",
    "StreamAbortedError",
    "TokenExtractionError",
    "TransportError",
]
