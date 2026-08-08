"""Accumulate a stream of :class:`StreamEvent` into a :class:`StreamResult`.

This module is the fully-typed application layer: it consumes
:class:`StreamEvent` objects through the :func:`brave_api._internal.events.parse_event`
boundary, which has already reduced arbitrary server payloads to typed
:class:`brave_api._internal.events.ParsedEvent` values. No untyped JSON ever
reaches this module, so pyright strict mode applies in full here.
"""

from __future__ import annotations

from typing import Any

from ..enums import StreamEventType, StreamState
from ..models import ImageResult, Infobox, StreamEvent, StreamResult, VideoResult, WebResult
from .events import Extracted, parse_event


class StreamAccumulator:
    """Consume events in arrival order and build the final :class:`StreamResult`.

    Not thread-safe by design; feed it from a single task.
    """

    def __init__(self, store_raw_events: bool = True) -> None:
        self._store_raw_events = store_raw_events
        self._text_parts: list[str] = []
        self._thinking_parts: list[str] = []
        self._tool_uses: list[dict[str, Any]] = []
        self._citations: list[dict[str, Any]] = []
        self._inline_entities: list[dict[str, Any]] = []
        self._inline_citations: list[dict[str, Any]] = []
        self._rag_content: list[dict[str, Any]] = []
        self._table_of_contents: list[dict[str, Any]] = []
        self._usage: dict[str, Any] = {}
        self._raw_events: list[StreamEvent] = []
        self._urls: list[str] = []
        self._images: list[ImageResult] = []
        self._videos: list[VideoResult] = []
        self._web_results: list[WebResult] = []
        self._infobox: Infobox | None = None
        self._followups: list[str] = []
        self._seen_urls: set[str] = set()
        self._seen_image_urls: set[str] = set()
        self._state = StreamState.INACTIVE

    @property
    def state(self) -> StreamState:
        return self._state

    def feed(self, event: StreamEvent) -> None:
        """Ingest a single event."""
        if self._store_raw_events:
            self._raw_events.append(event)
        self._state = StreamState.STREAMING

        parsed = parse_event(event)
        event_type = parsed.type

        if event_type is StreamEventType.TEXT_DELTA:
            self._text_parts.append(parsed.delta)
        elif event_type is StreamEventType.THINKING_DELTA:
            self._thinking_parts.append(parsed.delta)
        elif event_type is StreamEventType.TOOL_USE:
            if parsed.tool_use is not None:
                self._tool_uses.append(parsed.tool_use)
        elif event_type is StreamEventType.AUGMENT_WITH_TOOL_USE:
            if parsed.citation is not None:
                self._citations.append(parsed.citation)
            self._apply_extracted(parsed.extracted)
        elif event_type is StreamEventType.INLINE_ENTITY:
            if parsed.annotation is not None:
                self._inline_entities.append(parsed.annotation)
        elif event_type is StreamEventType.INLINE_CITATION:
            if parsed.annotation is not None:
                self._inline_citations.append(parsed.annotation)
        elif event_type is StreamEventType.AUGMENT_WITH_INLINE_CITATION:
            if parsed.annotation is not None:
                self._inline_citations.append(parsed.annotation)
        elif event_type is StreamEventType.INITIAL_RESPONSE:
            self._apply_extracted(parsed.extracted)
        elif event_type is StreamEventType.AUGMENT_WITH_INFOBOX:
            self._apply_extracted(parsed.extracted)
        elif event_type is StreamEventType.FOLLOWUPS:
            self._followups.extend(parsed.followups)
        elif event_type in {
            StreamEventType.AUGMENT_WITH_IMAGES,
            StreamEventType.AUGMENT_WITH_VIDEOS,
            StreamEventType.AUGMENT_WITH_WEB_SERP,
            StreamEventType.AUGMENT_WITH_WEB,
            StreamEventType.AUGMENT_WITH_NEWS,
            StreamEventType.AUGMENT_WITH_DISCUSSIONS,
            StreamEventType.AUGMENT_WITH_SHOPPING,
            StreamEventType.AUGMENT_WITH_LOCAL,
        }:
            self._apply_extracted(parsed.extracted)
        elif event_type is StreamEventType.RAG:
            self._rag_content.extend(parsed.rag)
        elif event_type is StreamEventType.TABLE_OF_CONTENT:
            self._table_of_contents.extend(parsed.toc)
        elif event_type is StreamEventType.USAGE:
            if parsed.usage is not None:
                self._usage = dict(parsed.usage)

    def _apply_extracted(self, extracted: Extracted) -> None:
        for web in extracted.web:
            self._add_unique_url(web.url)
            self._web_results.append(web)
            image_url = web.thumbnail_original or web.thumbnail
            if image_url and image_url not in self._seen_image_urls:
                self._seen_image_urls.add(image_url)
                self._images.append(
                    ImageResult(
                        url=image_url,
                        title=web.title,
                        thumbnail=web.thumbnail if web.thumbnail != image_url else None,
                        source=web.url,
                    )
                )

        for image in extracted.images:
            if image.url in self._seen_image_urls:
                continue
            self._seen_image_urls.add(image.url)
            self._images.append(image)
            self._add_unique_url(image.url)

        for video in extracted.videos:
            self._videos.append(video)
            self._add_unique_url(video.url)

        if extracted.infobox is not None and self._infobox is None:
            self._infobox = extracted.infobox

    def _add_unique_url(self, url: str) -> None:
        if url and url not in self._seen_urls:
            self._seen_urls.add(url)
            self._urls.append(url)

    def mark_failed(self) -> None:
        self._state = StreamState.FAILED

    def finalize(self) -> StreamResult:
        if self._state is not StreamState.FAILED:
            self._state = StreamState.COMPLETE
        return StreamResult(
            text="".join(self._text_parts),
            thinking="".join(self._thinking_parts),
            tool_uses=list(self._tool_uses),
            urls=list(self._urls),
            images=list(self._images),
            videos=list(self._videos),
            web_results=list(self._web_results),
            infobox=self._infobox,
            followups=list(self._followups),
            citations=list(self._citations),
            inline_entities=list(self._inline_entities),
            inline_citations=list(self._inline_citations),
            rag_content=list(self._rag_content),
            table_of_contents=list(self._table_of_contents),
            usage=self._usage,
            raw_events=list(self._raw_events),
            state=self._state,
        )


__all__ = ["StreamAccumulator"]
