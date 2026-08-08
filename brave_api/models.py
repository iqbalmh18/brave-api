"""Public response models.

Every public method returns one of these models (or an async generator of
:class:`StreamEvent`). All models are frozen, so returned results are safe to
share across tasks and cannot be mutated by accident.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

from .enums import StreamEventType, StreamState


class TokenModel(BaseModel):
    """Signed request token used to open a conversation."""

    q: str = Field(description="The query the token was minted for.")
    nonce: str = Field(description="Unique nonce for the request.")
    sig: str = Field(description="Signature validating the request.")

    model_config = {"frozen": True}


class ConversationResponse(BaseModel):
    """Result of opening a new conversation with the Brave AI endpoint."""

    id: str = Field(description="Unique conversation id.")
    symmetric_key: str | None = Field(
        default=None, description="Symmetric key required to continue the conversation."
    )
    bo_callback_share_link: str | None = Field(
        default=None, description="Share link returned by the server, if any."
    )
    bo_callback_open_modal: str | None = Field(
        default=None, description="Open-modal link returned by the server, if any."
    )

    model_config = {"frozen": True}


class WebResult(BaseModel):
    """A single web result, whether scraped from the SERP or streamed from Brave AI."""

    url: str = Field(description="Page URL.")
    title: str | None = Field(default=None, description="Page title.")
    description: str | None = Field(default=None, description="Snippet or description.")
    favicon: str | None = Field(default=None, description="Favicon URL.")
    thumbnail: str | None = Field(default=None, description="Thumbnail image URL.")
    thumbnail_original: str | None = Field(
        default=None, description="Original (unresized) thumbnail URL."
    )
    age: str | None = Field(default=None, description="Content age, e.g. '2 days ago'.")
    extra_snippets: list[str] = Field(
        default_factory=list[str], description="Additional snippets, if any."
    )
    source: str | None = Field(default=None, description="Source label, if any.")

    model_config = {"frozen": True}


class NewsResult(BaseModel):
    """A single news result from the Brave SERP."""

    url: str = Field(description="Article URL.")
    title: str | None = Field(default=None, description="Article headline.")
    description: str | None = Field(default=None, description="Article snippet.")
    age: str | None = Field(default=None, description="Publication age.")
    thumbnail: str | None = Field(default=None, description="Thumbnail URL.")
    source: str | None = Field(default=None, description="News outlet name.")

    model_config = {"frozen": True}


class ImageResult(BaseModel):
    """A single image result."""

    url: str = Field(description="Image URL.")
    title: str | None = Field(default=None, description="Image title.")
    thumbnail: str | None = Field(default=None, description="Thumbnail URL.")
    source: str | None = Field(default=None, description="Source site.")
    width: int | None = Field(default=None, description="Width in pixels, if known.")
    height: int | None = Field(default=None, description="Height in pixels, if known.")

    model_config = {"frozen": True}

    @field_validator("url", "thumbnail")
    @classmethod
    def _validate_http_url(cls, value: str | None) -> str | None:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class VideoResult(BaseModel):
    """A single video result."""

    url: str = Field(description="Video URL.")
    title: str | None = Field(default=None, description="Video title.")
    thumbnail: str | None = Field(default=None, description="Thumbnail URL.")
    duration: str | None = Field(default=None, description="Duration, e.g. '5:30'.")
    channel: str | None = Field(default=None, description="Channel or author name.")

    model_config = {"frozen": True}


class Infobox(BaseModel):
    """Entity knowledge card returned for the query, if any."""

    title: str | None = Field(default=None, description="Entity name.")
    subtitle: str | None = Field(default=None, description="Short entity description.")
    image_url: str | None = Field(default=None, description="Entity image URL.")
    url: str | None = Field(default=None, description="Primary source URL (e.g. Wikipedia).")
    description: str | None = Field(default=None, description="Long-form description.")
    attributes: dict[str, Any] = Field(
        default_factory=dict[str, Any], description="Additional entity attributes."
    )

    model_config = {"frozen": True}


class SuggestItem(BaseModel):
    """A single autocomplete suggestion."""

    text: str = Field(description="Suggestion text.")
    is_entity: bool = Field(default=False, description="Whether the suggestion is a named entity.")
    thumbnail: str | None = Field(default=None, description="Entity thumbnail URL, if any.")
    entity_type: str | None = Field(
        default=None, description="Entity type, e.g. 'Person' or 'Place'."
    )

    model_config = {"frozen": True}


class SearchResult(BaseModel):
    """Result of a single web search against the Brave SERP."""

    query: str = Field(description="The query that was searched.")
    web: list[WebResult] = Field(
        default_factory=list[WebResult], description="Organic web results."
    )
    news: list[NewsResult] = Field(default_factory=list[NewsResult], description="News results.")
    offset: int = Field(default=0, description="Pagination offset used for the request.")

    model_config = {"frozen": True}

    @property
    def has_results(self) -> bool:
        return bool(self.web or self.news)

    @property
    def urls(self) -> list[str]:
        """Every unique URL across web and news results, in order of appearance."""
        seen: set[str] = set()
        urls: list[str] = []
        for item in (*self.web, *self.news):
            if item.url not in seen:
                seen.add(item.url)
                urls.append(item.url)
        return urls


class SuggestResult(BaseModel):
    """Result of an autocomplete request."""

    query: str = Field(description="The partial query that was completed.")
    suggestions: list[SuggestItem] = Field(
        default_factory=list[SuggestItem], description="Matching suggestions."
    )

    model_config = {"frozen": True}


class StreamEvent(BaseModel):
    """A single event from the Brave AI streaming endpoint."""

    type: StreamEventType = Field(description="Parsed event type.")
    raw_type: str = Field(description="Raw event type string from the server.")
    payload: dict[str, Any] = Field(
        default_factory=dict[str, Any], description="Full event payload from the server."
    )

    model_config = {"frozen": True}

    @property
    def delta(self) -> str:
        return str(self.payload.get("delta", ""))

    @property
    def text(self) -> str:
        return str(self.payload.get("text", ""))

    @property
    def tool_id(self) -> str | None:
        """The tool-call id, for ``tool_use`` events."""
        value = self.payload.get("id")
        return value if isinstance(value, str) else None

    @property
    def tool_name(self) -> str | None:
        """The tool name, for ``tool_use`` events."""
        value = self.payload.get("name")
        return value if isinstance(value, str) else None

    @property
    def tool_arguments(self) -> dict[str, Any]:
        """The tool arguments, for ``tool_use`` events."""
        value = self.payload.get("arguments")
        return cast(dict[str, Any], value) if isinstance(value, dict) else {}

    @property
    def error_message(self) -> str | None:
        if self.type is not StreamEventType.ERROR:
            return None
        message = (
            self.payload.get("message")
            or self.payload.get("error")
            or self.payload.get("detail")
            or self.payload.get("reason")
            or self.payload.get("description")
        )
        if message:
            return str(message)
        return repr(self.payload)


class StreamResult(BaseModel):
    """Fully accumulated result of an ask/conversation request."""

    text: str = Field(default="", description="Full AI answer text (markdown).")
    thinking: str = Field(default="", description="Chain-of-thought reasoning, if any.")
    urls: list[str] = Field(default_factory=list[str], description="Relevant source URLs.")
    images: list[ImageResult] = Field(
        default_factory=list[ImageResult], description="Image results."
    )
    videos: list[VideoResult] = Field(
        default_factory=list[VideoResult], description="Video results."
    )
    web_results: list[WebResult] = Field(
        default_factory=list[WebResult], description="Web results referenced by the answer."
    )
    infobox: Infobox | None = Field(default=None, description="Entity knowledge card.")
    followups: list[str] = Field(
        default_factory=list[str], description="Suggested follow-up questions."
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]],
        description="Raw tool-result payloads used as citations.",
    )
    inline_entities: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]], description="Inline entities from the response."
    )
    inline_citations: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]], description="Inline citations from the response."
    )
    rag_content: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]], description="RAG content from the response."
    )
    table_of_contents: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]], description="Table-of-contents entries, if any."
    )
    usage: dict[str, Any] = Field(default_factory=dict[str, Any], description="Usage statistics.")
    tool_uses: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]], description="Tool calls made during the conversation."
    )
    raw_events: list[StreamEvent] = Field(
        default_factory=list[StreamEvent],
        exclude=True,
        description="Every raw event, for debugging. Excluded from serialization.",
    )
    state: StreamState = Field(default=StreamState.INACTIVE, description="Final stream state.")

    model_config = {"frozen": True}

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


__all__ = [
    "ConversationResponse",
    "ImageResult",
    "Infobox",
    "NewsResult",
    "SearchResult",
    "StreamEvent",
    "StreamResult",
    "SuggestItem",
    "SuggestResult",
    "TokenModel",
    "VideoResult",
    "WebResult",
]
