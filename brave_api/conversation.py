from __future__ import annotations

import asyncio
import json
import logging
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from ._internal.constants import (
    IMAGE_MAX_DIMENSION,
    IMAGE_QUALITY,
    THUMBNAIL_MAX_DIMENSION,
    THUMBNAIL_QUALITY,
)
from ._internal.models import StreamEvent
from ._internal.types import (
    QueryType,
    StreamEventType,
)
from ._streaming.parser import iter_events
from ._streaming.result import StreamAccumulator
from .exceptions import (
    ChallengeRequiredError,
    StreamAbortedError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from ._internal.models import ConversationResponse, StreamResult
    from .client import BraveClient

logger = logging.getLogger("brave_api.conversation")

_STOPWORDS_EN: frozenset[str] | None = None
_STOPWORDS_ID: frozenset[str] | None = None


def _get_stopwords_en() -> frozenset[str]:
    global _STOPWORDS_EN
    if _STOPWORDS_EN is None:
        data = json.loads(
            Path(__file__).parent.joinpath("_data/stopwords-en.json").read_text(
                encoding="utf-8"
            )
        )
        _STOPWORDS_EN = frozenset(data)
    return _STOPWORDS_EN


def _get_stopwords_id() -> frozenset[str]:
    global _STOPWORDS_ID
    if _STOPWORDS_ID is None:
        data = json.loads(
            Path(__file__).parent.joinpath("_data/stopwords-id.json").read_text(
                encoding="utf-8"
            )
        )
        _STOPWORDS_ID = frozenset(data)
    return _STOPWORDS_ID


def _detect_query_language(query: str) -> tuple[str, str]:
    tokens = [
        token.strip(".,!?()[]{}\"':;/\\")
        for token in query.lower().split()
        if token.strip()
    ]

    if not tokens:
        return "en", "en-us"

    stopwords_en = _get_stopwords_en()
    stopwords_id = _get_stopwords_id()

    id_score = 0
    en_score = 0

    for token in tokens:
        if token in stopwords_id:
            id_score += 1

        if token in stopwords_en:
            en_score += 1

    if id_score > en_score:
        return "id", "id-id"
    return "en", "en-us"


def _convert_to_jpeg_sync(image_bytes: bytes, max_dimension: int, quality: int) -> bytes | None:
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > max_dimension:
                if w >= h:
                    new_w = max_dimension
                    new_h = int(h * max_dimension / w)
                else:
                    new_h = max_dimension
                    new_w = int(w * max_dimension / h)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, "JPEG", quality=quality)
            return buffer.getvalue()
    except Exception as e:
        logger.warning("Failed to convert image to JPEG: %s", e)
        return None


async def _to_jpeg(image_bytes: bytes, max_dimension: int, quality: int) -> bytes | None:
    return await asyncio.to_thread(_convert_to_jpeg_sync, image_bytes, max_dimension, quality)


class Conversation:
    __slots__ = (
        "_auto_tools",
        "_bo_open_modal",
        "_bo_share_link",
        "_client",
        "_context",
        "_id",
        "_image",
        "_language_override",
        "_query",
        "_query_type",
        "_quote",
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
        self._bo_share_link: str | None = None
        self._bo_open_modal: str | None = None
        self._image: tuple[bytes, str, str] | None = None
        self._thumbnail: tuple[bytes, str, str] | None = None
        self._language_override: tuple[str, str] | None = None

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def symmetric_key(self) -> str | None:
        return self._symmetric_key

    @property
    def share_link(self) -> str | None:
        return self._bo_share_link

    @property
    def open_modal_link(self) -> str | None:
        return self._bo_open_modal

    @property
    def is_open(self) -> bool:
        return self._id is not None

    @property
    def auto_tools(self) -> bool:
        return self._auto_tools

    @property
    def has_image(self) -> bool:
        return self._image is not None

    async def attach_image(
        self,
        image: bytes | str | Path,
        *,
        filename: str = "image.jpg",
        mime: str = "image/jpeg",
    ) -> None:
        if isinstance(image, (str, Path)):
            data = Path(image).read_bytes()
            suffix = Path(image).suffix.lower()
            if not filename or filename == "image.jpg":
                filename = Path(image).name
            if mime == "image/jpeg" and suffix in {".png", ".webp", ".gif"}:
                mime = {
                    ".png": "image/png",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                }.get(suffix, mime)
        else:
            data = image
        
        jpeg_data = await _to_jpeg(data, max_dimension=IMAGE_MAX_DIMENSION, quality=IMAGE_QUALITY)
        if jpeg_data is None:
            jpeg_data = data
        self._image = (jpeg_data, "image.jpg", "image/jpeg")  # type: ignore[assignment]

        thumb_data = await _to_jpeg(data, max_dimension=THUMBNAIL_MAX_DIMENSION, quality=THUMBNAIL_QUALITY)
        if thumb_data:
            self._thumbnail = (thumb_data, "thumbnail.jpg", "image/jpeg")  # type: ignore[assignment]

    def set_language(self, language: str, ui_lang: str | None = None) -> None:
        self._language_override = (language, ui_lang or f"{language}-{language}")

    def _resolve_stream_overrides(self) -> tuple[str, str]:
        if self._language_override is not None:
            return self._language_override
        return _detect_query_language(self._query)

    async def open(self) -> str:
        if self._id is not None:
            return self._id
        
        token = await self._client.fetch_token(self._query)
        response: ConversationResponse = await self._client.open_conversation(token=token)
        self._id = response.id
        self._symmetric_key = response.symmetric_key
        self._bo_share_link = response.bo_callback_share_link
        self._bo_open_modal = response.bo_callback_open_modal
        return self._id

    async def close(self) -> None:
        self._id = None
        self._symmetric_key = None
        self._bo_share_link = None
        self._bo_open_modal = None
        self._image = None
        self._thumbnail = None

    async def __aenter__(self) -> Conversation:
        await self.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def stream_events(self) -> AsyncGenerator[StreamEvent, None]:
        if not self.is_open:
            await self.open()
        
        assert self._id is not None
        assert self._symmetric_key is not None
        
        language, ui_lang = self._resolve_stream_overrides()
        raw_source = self._stream_source(language=language, ui_lang=ui_lang)
        source_gen = iter_events(raw_source)  # type: ignore[arg-type]
        try:
            async for event in source_gen:
                if event.type is StreamEventType.CHALLENGE:
                    raise ChallengeRequiredError("Raised challenge event from server")
                
                tool_use = self._extract_tool_use(event)
                if self._auto_tools and tool_use is not None:
                    try:
                        enrichment = await self._client._run_tool(
                            tool_use,
                            self._symmetric_key,
                        )
                        yield StreamEvent(
                            type=StreamEventType.AUGMENT_WITH_TOOL_USE,
                            raw_type="augment_with_tool_use",
                            payload=enrichment,
                        )
                        continue
                    except Exception as exc:
                        logger.warning("tool_use %s failed: %s", tool_use.get("name"), exc)
                yield event
        finally:
            await source_gen.aclose()

    def _stream_source(
        self,
        *,
        language: str,
        ui_lang: str,
    ):
        if self._image is None:
            return self._client._stream_raw(
                conversation_id=self._id,  # type: ignore[arg-type]
                query=self._query,
                symmetric_key=self._symmetric_key,  # type: ignore[arg-type]
                query_type=self._query_type,
                quote=self._quote,
                context=self._context,
                enable_inline_entities=True,
                language=language,
                ui_lang=ui_lang,
            )
        image_bytes, filename, mime = self._image
        thumb_bytes, thumb_filename, thumb_mime = (
            self._thumbnail if self._thumbnail else (None, "thumbnail.jpg", "image/jpeg")
        )
        return self._client._stream_raw_multimodal(
            conversation_id=self._id,  # type: ignore[arg-type]
            query=self._query,
            symmetric_key=self._symmetric_key,  # type: ignore[arg-type]
            image_bytes=image_bytes,
            image_filename=filename,
            image_mime=mime,
            thumbnail_bytes=thumb_bytes,
            thumbnail_filename=thumb_filename,
            thumbnail_mime=thumb_mime,
            query_type=self._query_type,
            quote=self._quote,
            context=self._context,
            enable_inline_entities=True,
            language=language,
            ui_lang=ui_lang,
        )

    @staticmethod
    def _extract_tool_use(event: StreamEvent) -> dict[str, object] | None:
        payload = event.payload
        candidate = payload.get("tool_use")
        if isinstance(candidate, dict) and candidate.get("signed_params"):
            return candidate
        
        if event.type is StreamEventType.TOOL_USE and payload.get("signed_params"):
            return payload
        
        return None

    async def collect(self) -> StreamResult:
        accumulator = StreamAccumulator()
        events_gen = self.stream_events()
        try:
            async for event in events_gen:
                accumulator.feed(event)
                if event.type is StreamEventType.ERROR:
                    accumulator.mark_failed()
                    logger.error(
                        "Stream error event received. Raw payload: %s", event.payload
                    )
                    raise StreamAbortedError(
                        event.error_message or "Stream raised error event"
                    )
        except ChallengeRequiredError:
            accumulator.mark_failed()
            raise
        except StreamAbortedError:
            accumulator.mark_failed()
            raise
        except Exception:
            accumulator.mark_failed()
            raise
        finally:
            await events_gen.aclose()
        return accumulator.finalize()


__all__ = ["Conversation"]
