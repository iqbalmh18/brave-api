from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class QueryType(StrEnum):
    REGULAR = "regular"
    REGENERATE_ANSWER = "regenerate_answer"
    ANSWER_WITH_AI_FOLLOW_UP = "answer_with_ai_follow_up"
    CONTEXTUAL_SEARCH = "contextual_search"


class StreamEventType(StrEnum):
    DEBUG_LABELS = "debug_labels"
    RAG = "rag"
    INLINE_ENTITIES = "inline_entities"
    TEXT_START = "text_start"
    TEXT_DELTA = "text_delta"
    TEXT_STOP = "text_stop"
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_STOP = "thinking_stop"
    RESEARCH_START = "research_start"
    RESEARCH = "research"
    RESEARCH_STOP = "research_stop"
    TOOL_USE = "tool_use"
    AUGMENT_WITH_TOOL_USE = "augment_with_tool_use"
    INLINE_ENTITY = "inline_entity"
    INLINE_CITATION = "inline_citation"
    AUGMENT_WITH_INLINE_CITATION = "augment_with_inline_citation"
    AUGMENT_WITH_INFOBOX = "augment_with_infobox"
    AUGMENT_WITH_WEB = "augment_with_web"
    AUGMENT_WITH_WEB_SERP = "augment_with_web_serp"
    AUGMENT_WITH_NEWS = "augment_with_news"
    AUGMENT_WITH_IMAGES = "augment_with_images"
    AUGMENT_WITH_VIDEOS = "augment_with_videos"
    AUGMENT_WITH_DISCUSSIONS = "augment_with_discussions"
    AUGMENT_WITH_SHOPPING = "augment_with_shopping"
    AUGMENT_WITH_LOCAL = "augment_with_local"
    INITIAL_RESPONSE = "initial_response"
    FOLLOWUPS = "followups"
    TABLE_OF_CONTENT = "table_of_content"
    USAGE = "usage"
    ERROR = "error"
    CHALLENGE = "challenge"


class StreamState(StrEnum):
    INACTIVE = "inactive"
    STREAMING = "streaming"
    COMPLETE = "complete"
    FAILED = "failed"


class ToolName(StrEnum):
    INFOBOX = "augment_with_infobox"
    WEB = "augment_with_web"
    WEB_SERP = "augment_with_web_serp"
    NEWS = "augment_with_news"
    IMAGES = "augment_with_images"
    VIDEOS = "augment_with_videos"
    DISCUSSIONS = "augment_with_discussions"
    SHOPPING = "augment_with_shopping"
    LOCAL = "augment_with_local"


@runtime_checkable
class SupportsRawStream(Protocol):
    def __aiter__(self) -> AsyncIterator[bytes | str]: ...
    async def __anext__(self) -> bytes | str: ...


__all__ = [
    "QueryType",
    "StreamEventType",
    "StreamState",
    "SupportsRawStream",
    "ToolName",
]
