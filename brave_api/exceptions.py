from __future__ import annotations


class BraveAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TransportError(BraveAPIError):
    pass


class HTTPStatusError(BraveAPIError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_text: str = "",
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.response_text = response_text


class TokenExtractionError(BraveAPIError):
    pass


class ConversationError(BraveAPIError):
    pass


class StreamAbortedError(BraveAPIError):
    pass


class ChallengeRequiredError(BraveAPIError):
    pass


class InvalidResponseError(BraveAPIError):
    pass


__all__ = [
    "BraveAPIError",
    "ChallengeRequiredError",
    "ConversationError",
    "HTTPStatusError",
    "InvalidResponseError",
    "StreamAbortedError",
    "TokenExtractionError",
    "TransportError",
]
