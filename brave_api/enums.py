"""Public enums used across the brave_api surface."""

from __future__ import annotations

from enum import StrEnum


class QueryType(StrEnum):
    """How the Brave AI endpoint should treat the query."""

    REGULAR = "regular"
    REGENERATE_ANSWER = "regenerate_answer"
    ANSWER_WITH_AI_FOLLOW_UP = "answer_with_ai_follow_up"
    CONTEXTUAL_SEARCH = "contextual_search"


class StreamEventType(StrEnum):
    """Every event type the Brave AI stream can emit."""

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
    """Lifecycle state of an accumulated stream."""

    INACTIVE = "inactive"
    STREAMING = "streaming"
    COMPLETE = "complete"
    FAILED = "failed"


__all__ = ["QueryType", "StreamEventType", "StreamState"]
