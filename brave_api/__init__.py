from __future__ import annotations

from ._crypto.keys import generate_symmetric_key, is_valid_symmetric_key
from ._internal.config import ClientConfig
from ._internal.constants import VERSION
from ._internal.models import (
    ConversationResponse,
    ImageResult,
    Infobox,
    SearchNewsResult,
    SearchResult,
    SearchWebResult,
    SignedParams,
    StreamEvent,
    StreamResult,
    SuggestItem,
    TokenModel,
    ToolUseEvent,
    VideoResult,
    WebResult,
)
from ._internal.types import (
    QueryType,
    StreamEventType,
    StreamState,
    ToolName,
)
from ._streaming.parser import iter_events, parse_line
from .client import BraveClient
from .conversation import Conversation
from .exceptions import (
    BraveAPIError,
    ChallengeRequiredError,
    ConversationError,
    HTTPStatusError,
    InvalidResponseError,
    StreamAbortedError,
    TokenExtractionError,
    TransportError,
)

__all__ = [
    "VERSION",
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
    "InvalidResponseError",
    "QueryType",
    "SearchNewsResult",
    "SearchResult",
    "SearchWebResult",
    "SignedParams",
    "StreamAbortedError",
    "StreamEvent",
    "StreamEventType",
    "StreamResult",
    "StreamState",
    "SuggestItem",
    "TokenExtractionError",
    "TokenModel",
    "ToolName",
    "ToolUseEvent",
    "TransportError",
    "VideoResult",
    "WebResult",
    "generate_symmetric_key",
    "is_valid_symmetric_key",
    "iter_events",
    "parse_line",
]
