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
    SuggestItem,
    TokenModel,
    ToolUseEvent,
    VideoResult,
    WebResult,
)
from ._internal.types import (
    ConversationResponseDict,
    QueryType,
    StreamEvent,
    StreamEventType,
    StreamResult,
    StreamState,
    TokenDict,
    ToolName,
    ToolUseEventDict,
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
    "ConversationResponseDict",
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
    "TokenDict",
    "TokenExtractionError",
    "TokenModel",
    "ToolName",
    "ToolUseEvent",
    "ToolUseEventDict",
    "TransportError",
    "VideoResult",
    "WebResult",
    "generate_symmetric_key",
    "is_valid_symmetric_key",
    "iter_events",
    "parse_line",
]
