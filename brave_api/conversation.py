"""Multi-turn conversation against the Brave AI endpoint.

``Conversation`` is a "friend" class of :class:`BraveClient`: it legitimately
calls the client's private streaming helpers. Pyright's protected-access rule
is disabled for this module because the cross-class coupling is intentional
and contained.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ._internal.accumulator import StreamAccumulator
from ._internal.constants import (
    IMAGE_MAX_DIMENSION,
    IMAGE_QUALITY,
    THUMBNAIL_MAX_DIMENSION,
    THUMBNAIL_QUALITY,
)
from ._internal.image import to_jpeg
from ._internal.language import detect_query_language
from ._internal.sse import iter_events
from .enums import QueryType, StreamEventType
from .exceptions import ChallengeRequiredError, ConversationError, StreamAbortedError
from .models import ConversationResponse, StreamEvent, StreamResult

if TYPE_CHECKING:
    from .client import BraveClient

logger = logging.getLogger("brave_api.conversation")

ImageInput = bytes | str | Path


class Conversation:
    """A single (possibly multi-turn) conversation with Brave AI.

    Use :meth:`BraveClient.conversation` to create or resume one; this class
    is not meant to be constructed directly.
    """

    __slots__ = (
        "_auto_tools",
        "_client",
        "_context",
        "_id",
        "_image",
        "_language_override",
        "_open_modal_link",
        "_query",
        "_query_type",
        "_quote",
        "_share_link",
        "_symmetric_key",
        "_thumbnail",
    )

    def __init__(
        self,
        client: BraveClient,
        query: str,
        *,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
    ) -> None:
        self._client: BraveClient = client
        self._query: str = query
        self._query_type: QueryType = query_type
        self._quote: str | None = quote
        self._context: str | None = context
        self._auto_tools: bool = auto_tools
        self._id: str | None = None
        self._symmetric_key: str | None = None
        self._share_link: str | None = None
        self._open_modal_link: str | None = None
        self._image: tuple[bytes, str, str] | None = None
        self._thumbnail: tuple[bytes, str, str] | None = None
        self._language_override: tuple[str, str | None] | None = None

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def symmetric_key(self) -> str | None:
        return self._symmetric_key

    @property
    def share_link(self) -> str | None:
        return self._share_link

    @property
    def open_modal_link(self) -> str | None:
        return self._open_modal_link

    @property
    def is_open(self) -> bool:
        return self._id is not None and self._symmetric_key is not None

    @property
    def auto_tools(self) -> bool:
        return self._auto_tools

    @property
    def has_image(self) -> bool:
        return self._image is not None

    def resume(self, conversation_id: str, symmetric_key: str) -> None:
        """Continue an existing conversation from a previous session."""
        if not conversation_id or not symmetric_key:
            raise ValueError("conversation_id and symmetric_key must be non-empty")
        self._id = conversation_id
        self._symmetric_key = symmetric_key

    async def open(self) -> str:
        """Open the conversation and return its id. Idempotent."""
        if self.is_open and self._id is not None:
            return self._id

        token = await self._client._fetch_token(self._query)
        response: ConversationResponse = await self._client._open_conversation(token=token)
        self._id = response.id
        self._symmetric_key = response.symmetric_key
        self._share_link = response.bo_callback_share_link
        self._open_modal_link = response.bo_callback_open_modal
        if self._symmetric_key is None:
            raise ConversationError("Open conversation response did not include a symmetric key")
        return self._id

    async def reset(self) -> None:
        """Clear the conversation state so it can be reopened or garbage collected."""
        self._id = None
        self._symmetric_key = None
        self._share_link = None
        self._open_modal_link = None
        self._image = None
        self._thumbnail = None
        self._language_override = None

    async def __aenter__(self) -> Conversation:
        await self.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.reset()

    async def attach_image(self, image: ImageInput) -> None:
        """Attach an image to the next request.

        Args:
            image: Raw image bytes, or a local file path given as ``str`` or
                :class:`pathlib.Path`.

        The image is re-encoded to JPEG (max 1000 px, quality 92) before
        upload, with a matching thumbnail (max 256 px) attached for faster
        previews.
        """
        if isinstance(image, (str, Path)):
            data = Path(image).read_bytes()
        else:
            data = image

        jpeg = await to_jpeg(data, max_dimension=IMAGE_MAX_DIMENSION, quality=IMAGE_QUALITY)
        image_data = jpeg if jpeg is not None else data
        self._image = (image_data, "image.jpg", "image/jpeg")

        thumbnail = await to_jpeg(
            image_data, max_dimension=THUMBNAIL_MAX_DIMENSION, quality=THUMBNAIL_QUALITY
        )
        if thumbnail is not None:
            self._thumbnail = (thumbnail, "thumbnail.jpg", "image/jpeg")

    def set_language(self, language: str, ui_lang: str | None = None) -> None:
        """Override the response language for this conversation.

        When *ui_lang* is omitted, the client-level ``ui_lang`` config value is
        used instead of guessing one from the language code.
        """
        self._language_override = (language, ui_lang)

    async def stream_events(self) -> AsyncGenerator[StreamEvent, None]:
        """Yield :class:`StreamEvent` objects in real time.

        When :attr:`auto_tools` is enabled, ``tool_use`` events are executed
        automatically and an ``augment_with_tool_use`` enrichment event is
        yielded in their place.
        """
        if not self.is_open:
            await self.open()
        conversation_id = self._id
        symmetric_key = self._symmetric_key
        if conversation_id is None or symmetric_key is None:
            raise ConversationError("Conversation could not be opened")

        language, ui_lang = self._resolve_stream_overrides()
        raw_source = self._stream_source(
            conversation_id=conversation_id,
            symmetric_key=symmetric_key,
            language=language,
            ui_lang=ui_lang,
        )
        source = iter_events(raw_source)
        try:
            async for event in source:
                if event.type is StreamEventType.CHALLENGE:
                    raise ChallengeRequiredError("Server raised a challenge event")

                tool_use = self._extract_tool_use(event)
                if self._auto_tools and tool_use is not None:
                    try:
                        enrichment = await self._client._run_tool(tool_use, symmetric_key)
                    except Exception as exc:
                        logger.warning(
                            "tool_use %s failed: %s",
                            tool_use.get("name"),
                            exc,
                        )
                    else:
                        yield StreamEvent(
                            type=StreamEventType.AUGMENT_WITH_TOOL_USE,
                            raw_type="augment_with_tool_use",
                            payload=enrichment,
                        )
                        continue
                yield event
        finally:
            await source.aclose()

    def _stream_source(
        self,
        *,
        conversation_id: str,
        symmetric_key: str,
        language: str,
        ui_lang: str | None,
    ) -> AsyncIterator[str | bytes]:
        if self._image is None:
            return self._client._stream_raw(
                conversation_id=conversation_id,
                query=self._query,
                symmetric_key=symmetric_key,
                query_type=self._query_type,
                quote=self._quote,
                context=self._context,
                enable_inline_entities=True,
                language=language,
                ui_lang=ui_lang,
            )
        image_bytes, filename, mime = self._image
        thumbnail_bytes, thumbnail_filename, thumbnail_mime = self._thumbnail or (
            None,
            "thumbnail.jpg",
            "image/jpeg",
        )
        return self._client._stream_raw_multimodal(
            conversation_id=conversation_id,
            query=self._query,
            symmetric_key=symmetric_key,
            image_bytes=image_bytes,
            image_filename=filename,
            image_mime=mime,
            thumbnail_bytes=thumbnail_bytes,
            thumbnail_filename=thumbnail_filename,
            thumbnail_mime=thumbnail_mime,
            query_type=self._query_type,
            quote=self._quote,
            context=self._context,
            enable_inline_entities=True,
            language=language,
            ui_lang=ui_lang,
        )

    async def collect(self, *, store_raw_events: bool = True) -> StreamResult:
        """Consume the whole stream and return the accumulated result."""
        accumulator = StreamAccumulator(store_raw_events=store_raw_events)
        events = self.stream_events()
        try:
            async for event in events:
                accumulator.feed(event)
                if event.type is StreamEventType.ERROR:
                    raise StreamAbortedError(event.error_message or "Stream raised an error event")
        except Exception:
            accumulator.mark_failed()
            raise
        finally:
            await events.aclose()
        return accumulator.finalize()

    def _resolve_stream_overrides(self) -> tuple[str, str | None]:
        if self._language_override is not None:
            return self._language_override
        return detect_query_language(self._query)

    @staticmethod
    def _extract_tool_use(event: StreamEvent) -> dict[str, object] | None:
        payload = event.payload
        candidate = payload.get("tool_use")
        if isinstance(candidate, dict):
            typed = cast(dict[str, Any], candidate)
            if typed.get("signed_params") is not None:
                return typed
        signed = payload.get("signed_params")
        if event.type is StreamEventType.TOOL_USE and signed is not None:
            return payload
        return None


__all__ = ["Conversation"]
