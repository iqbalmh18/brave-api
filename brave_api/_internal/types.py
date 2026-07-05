from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from pydantic import BaseModel, Field

from .models import ImageResult, Infobox, TokenModel, ToolUseEvent, VideoResult, WebResult


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


class StreamEvent(BaseModel):
    type: StreamEventType = Field(description="Tipe event yang sudah di-parse")
    raw_type: str = Field(description="Tipe event asli dari server")
    payload: dict[str, Any] = Field(default_factory=dict, description="Payload JSON lengkap dari server")

    model_config = {"frozen": True}

    @property
    def delta(self) -> str:
        return str(self.payload.get("delta", ""))

    @property
    def text(self) -> str:
        return str(self.payload.get("text", ""))

    @property
    def tool_id(self) -> str | None:
        return self.payload.get("id")

    @property
    def tool_name(self) -> str | None:
        return self.payload.get("name")

    @property
    def tool_arguments(self) -> dict[str, Any]:
        return dict(self.payload.get("arguments", {}))

    @property
    def error_message(self) -> str | None:
        if self.type is StreamEventType.ERROR:
            msg = (
                self.payload.get("message")
                or self.payload.get("error")
                or self.payload.get("detail")
                or self.payload.get("reason")
                or self.payload.get("description")
            )
            if msg:
                return str(msg)
            # Fallback: dump the whole payload so it's never silently empty
            return repr(self.payload)
        return None


class StreamResult(BaseModel):
    text: str = Field(default="", description="Text respons lengkap dari AI")
    thinking: str = Field(default="", description="Proses thinking model jika ada")
    urls: list[str] = Field(default_factory=list, description="URL web yang relevan")
    images: list[ImageResult] = Field(default_factory=list, description="Gambar yang relevan dengan metadata")
    videos: list[VideoResult] = Field(default_factory=list, description="Video yang relevan dengan metadata")
    web_results: list[WebResult] = Field(default_factory=list, description="Hasil pencarian web dengan metadata")
    infobox: Infobox | None = Field(default=None, description="Entity card (panel Wikipedia/knowledge) jika ada")
    followups: list[str] = Field(default_factory=list, description="Saran pertanyaan lanjutan dari server")
    citations: list[dict[str, Any]] = Field(default_factory=list, description="Sitasi dari sumber")
    inline_entities: list[dict[str, Any]] = Field(default_factory=list, description="Entitas inline dari respons")
    tool_uses: list[dict[str, Any]] = Field(default_factory=list, description="Tool yang digunakan selama percakapan")
    raw_events: list[StreamEvent] = Field(default_factory=list, description="Semua event mentah untuk debugging")
    state: StreamState = Field(default=StreamState.INACTIVE, description="Status stream terakhir")

    @property
    def is_complete(self) -> bool:
        return self.state is StreamState.COMPLETE

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_uses)

    @property
    def has_images(self) -> bool:
        return bool(self.images)

    @property
    def has_videos(self) -> bool:
        return bool(self.videos)

    @property
    def has_infobox(self) -> bool:
        return self.infobox is not None


@runtime_checkable
class SupportsRawStream(Protocol):
    def __aiter__(self) -> AsyncIterator[bytes | str]: ...
    async def __anext__(self) -> bytes | str: ...


TokenDict = dict[str, str]
ConversationResponseDict = dict[str, str]
ToolUseEventDict = dict[str, Any]

__all__ = [
    "ConversationResponseDict",
    "ImageResult",
    "Infobox",
    "QueryType",
    "StreamEvent",
    "StreamEventType",
    "StreamResult",
    "StreamState",
    "SupportsRawStream",
    "TokenDict",
    "TokenModel",
    "ToolName",
    "ToolUseEvent",
    "ToolUseEventDict",
    "VideoResult",
    "WebResult",
]
