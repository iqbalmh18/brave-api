"""brave-api-python: async Python client for the Brave Ask & Search API.

Public surface:

- :class:`BraveClient` and :class:`ClientConfig` for all API access
- :class:`Conversation` for multi-turn streaming conversations
- typed result models (:class:`StreamResult`, :class:`SearchResult`,
  :class:`SuggestResult`, ...)
- enums (:class:`QueryType`, :class:`StreamEventType`, :class:`StreamState`)
- the full exception hierarchy rooted at :class:`BraveAPIError`

An MCP server built on FastMCP ships in :mod:`brave_api.mcp`.
"""

from __future__ import annotations

from ._internal.crypto import generate_symmetric_key, is_valid_symmetric_key
from ._version import __version__
from .client import BraveClient
from .config import ClientConfig
from .conversation import Conversation
from .enums import QueryType, StreamEventType, StreamState
from .exceptions import (
    BraveAPIError,
    ChallengeRequiredError,
    ConversationError,
    HTTPStatusError,
    ResponseParseError,
    StreamAbortedError,
    TokenExtractionError,
    TransportError,
)
from .models import (
    ConversationResponse,
    ImageResult,
    Infobox,
    NewsResult,
    SearchResult,
    StreamEvent,
    StreamResult,
    SuggestItem,
    SuggestResult,
    TokenModel,
    VideoResult,
    WebResult,
)

__all__ = [
    "__version__",
    "BraveAPIError",
    "BraveClient",
    "ChallengeRequiredError",
    "ClientConfig",
    "Conversation",
    "ConversationError",
    "ConversationResponse",
    "HTTPStatusError",
    "ImageResult",
    "Infobox",
    "NewsResult",
    "QueryType",
    "ResponseParseError",
    "SearchResult",
    "StreamAbortedError",
    "StreamEvent",
    "StreamEventType",
    "StreamResult",
    "StreamState",
    "SuggestItem",
    "SuggestResult",
    "TokenExtractionError",
    "TokenModel",
    "TransportError",
    "VideoResult",
    "WebResult",
    "generate_symmetric_key",
    "is_valid_symmetric_key",
]
