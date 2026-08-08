"""The public client facade."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from typing import TypeVar, cast
from urllib.parse import quote_plus

from ._internal.constants import (
    DATA_QUERY_PARAM_NAME,
    DATA_QUERY_PARAM_VALUE,
    PATH_DATA_JSON,
    PATH_NEW,
    PATH_PRIME,
    PATH_RUN_TOOL,
    PATH_SEARCH,
    PATH_STREAM,
    PATH_STREAM_MULTIMODAL,
    PATH_SUGGEST,
)
from ._internal.crypto import generate_symmetric_key
from ._internal.http import Transport
from ._internal.retry import is_http_retryable, retry_async
from ._internal.search_parser import parse_search_html, parse_suggest_json
from ._internal.token import find_token
from .config import ClientConfig
from .conversation import Conversation, ImageInput
from .enums import QueryType
from .exceptions import (
    ConversationError,
    HTTPStatusError,
    ResponseParseError,
    TransportError,
)
from .models import (
    ConversationResponse,
    SearchResult,
    StreamEvent,
    StreamResult,
    SuggestItem,
    SuggestResult,
    TokenModel,
)

T = TypeVar("T")

logger = logging.getLogger("brave_api.client")


class BraveClient:
    """Async client for the Brave Ask & Search API.

    Use it as an async context manager to guarantee the HTTP session is
    opened and primed::

        async with BraveClient() as client:
            result = await client.ask("what is quantum computing?")
    """

    def __init__(
        self,
        config: ClientConfig | None = None,
        *,
        transport: Transport | None = None,
    ) -> None:
        """Create a client.

        Args:
            config: Client configuration; defaults to :class:`ClientConfig`.
            transport: Optional custom transport. Intended for testing and
                advanced embedding scenarios; the default transport is created
                from *config*.
        """
        self._config = config or ClientConfig()
        self._transport = transport or Transport(self._config)
        self._primed = False
        self._prime_lock = asyncio.Lock()

    @property
    def config(self) -> ClientConfig:
        return self._config

    @property
    def is_open(self) -> bool:
        return self._transport.is_open

    async def open(self) -> None:
        """Open the HTTP session and prime it. Idempotent.

        Called automatically by ``async with``; use it directly for manual
        lifecycle management (paired with :meth:`close`).
        """
        try:
            await self._transport.open()
            await self._prime()
        except BaseException:
            await self._transport.close()
            raise

    async def __aenter__(self) -> BraveClient:
        await self.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP session. Idempotent."""
        await self._transport.close()

    async def health_check(self) -> bool:
        """Return True when the base URL responds successfully."""
        try:
            await self._transport.request("GET", self._config.base_url)
            return True
        except Exception:
            return False

    async def ask(
        self,
        query: str,
        *,
        image: ImageInput | None = None,
        language: str | None = None,
        ui_lang: str | None = None,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
        store_raw_events: bool = True,
    ) -> StreamResult:
        """Ask a question and return the fully accumulated :class:`StreamResult`."""
        conversation = await self.conversation(
            query,
            image=image,
            language=language,
            ui_lang=ui_lang,
            query_type=query_type,
            quote=quote,
            context=context,
            auto_tools=auto_tools,
        )
        return await conversation.collect(store_raw_events=store_raw_events)

    async def ask_stream(
        self,
        query: str,
        *,
        image: ImageInput | None = None,
        language: str | None = None,
        ui_lang: str | None = None,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream :class:`StreamEvent` objects for a question in real time."""
        conversation = await self.conversation(
            query,
            image=image,
            language=language,
            ui_lang=ui_lang,
            query_type=query_type,
            quote=quote,
            context=context,
            auto_tools=auto_tools,
        )
        async for event in conversation.stream_events():
            yield event

    async def search(
        self,
        query: str,
        *,
        offset: int = 0,
        spellcheck: bool = True,
        source: str = "web",
    ) -> SearchResult:
        """Search the Brave SERP and return structured :class:`SearchResult`."""
        url = f"{self._config.base_url}{PATH_SEARCH}"
        params: dict[str, str] = {"q": query, "source": source}
        if offset > 0:
            params["offset"] = str(offset)
        if not spellcheck:
            params["spellcheck"] = "0"
        headers = self._transport.build_headers(
            referer_suffix=PATH_PRIME,
            accept=("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            extra={
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "accept-encoding": "gzip, deflate",
            },
        )
        return await self._retry(
            lambda: self._do_search(url, params, headers, query, offset),
            "search",
        )

    async def suggest(
        self,
        query: str,
        *,
        rich: bool = True,
        source: str = "web",
    ) -> SuggestResult:
        """Fetch autocomplete suggestions for a partial query."""
        url = f"{self._config.base_url}{PATH_SUGGEST}"
        params = {
            "q": query,
            "rich": "true" if rich else "false",
            "source": source,
            "country": self._config.country,
        }
        headers = self._transport.build_headers(
            referer_suffix="/",
            accept="*/*",
            extra={
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
        )
        items = await self._retry(
            lambda: self._do_suggest(url, params, headers),
            "suggest",
        )
        return SuggestResult(query=query, suggestions=items)

    async def conversation(
        self,
        query: str,
        *,
        conversation_id: str | None = None,
        symmetric_key: str | None = None,
        image: ImageInput | None = None,
        language: str | None = None,
        ui_lang: str | None = None,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
    ) -> Conversation:
        """Create a new conversation or resume an existing one.

        Resuming requires *conversation_id* and *symmetric_key* together.
        """
        if (conversation_id is None) != (symmetric_key is None):
            raise ValueError("conversation_id and symmetric_key must be provided together")

        conversation = Conversation(
            self,
            query,
            query_type=query_type,
            quote=quote,
            context=context,
            auto_tools=auto_tools,
        )
        if conversation_id is not None and symmetric_key is not None:
            conversation.resume(conversation_id, symmetric_key)

        if image is not None:
            await conversation.attach_image(image)
        if language is not None:
            conversation.set_language(language, ui_lang)

        if not conversation.is_open:
            await conversation.open()
        return conversation

    async def _retry(self, operation: Callable[[], Awaitable[T]], operation_name: str) -> T:
        cfg = self._config
        return await retry_async(
            operation,
            operation_name=operation_name,
            max_attempts=cfg.max_retries,
            backoff_seconds=cfg.retry_backoff,
            jitter=cfg.retry_jitter,
            is_retryable=is_http_retryable,
        )

    async def _prime(self) -> None:
        if self._primed:
            return
        async with self._prime_lock:
            if self._primed:
                return
            try:
                await self._retry(self._do_prime, "prime")
            except HTTPStatusError:
                raise
            except Exception as exc:
                raise TransportError(f"Failed to prime session: {exc}") from exc
            self._primed = True

    async def _do_prime(self) -> None:
        await self._transport.request("GET", f"{self._config.base_url}{PATH_PRIME}")

    async def _fetch_token(self, query: str) -> TokenModel:
        url = f"{self._config.base_url}{PATH_DATA_JSON}"
        params = {"q": query, DATA_QUERY_PARAM_NAME: DATA_QUERY_PARAM_VALUE}
        headers = self._transport.build_headers(
            referer_suffix=f"{PATH_PRIME}?q={quote_plus(query)}",
            accept="*/*",
            extra={"sec-fetch-mode": "cors", "sec-fetch-site": "same-origin"},
        )
        return await self._retry(
            lambda: self._do_fetch_token(url, params, headers),
            "fetch_token",
        )

    async def _do_fetch_token(
        self, url: str, params: dict[str, str], headers: dict[str, str]
    ) -> TokenModel:
        payload = await self._transport.get_json(url, params=params, headers=headers)
        return find_token(payload)

    async def _open_conversation(
        self, token: TokenModel, symmetric_key: str | None = None
    ) -> ConversationResponse:
        key = symmetric_key or generate_symmetric_key()
        url = f"{self._config.base_url}{PATH_NEW}"
        params = self._new_params(token=token, symmetric_key=key)
        headers = self._transport.build_cors_headers(accept="application/json")
        return await self._retry(
            lambda: self._do_open_conversation(url, params, headers, key),
            "open_conversation",
        )

    async def _do_open_conversation(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        key: str,
    ) -> ConversationResponse:
        payload = await self._transport.get_json(url, params=params, headers=headers)
        conversation_id = payload.get("id")
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ConversationError(f"Response /new missing id: {payload!r}")
        return ConversationResponse(
            id=conversation_id,
            symmetric_key=key,
            bo_callback_share_link=payload.get("bo_callback_share_link"),
            bo_callback_open_modal=payload.get("bo_callback_open_modal"),
        )

    async def _stream_raw(
        self,
        *,
        conversation_id: str,
        query: str,
        symmetric_key: str,
        query_type: QueryType,
        quote: str | None,
        context: str | None,
        enable_inline_entities: bool,
        language: str,
        ui_lang: str | None,
    ) -> AsyncIterator[str | bytes]:
        url = f"{self._config.base_url}{PATH_STREAM}"
        params = self._stream_params(
            conversation_id=conversation_id,
            query=query,
            symmetric_key=symmetric_key,
            query_type=query_type,
            quote=quote,
            context=context,
            enable_inline_entities=enable_inline_entities,
            language=language,
            ui_lang=ui_lang,
        )
        headers = self._transport.build_cors_headers(accept="application/json")
        async for line in self._transport.stream(url, params=params, headers=headers):
            yield line

    async def _stream_raw_multimodal(
        self,
        *,
        conversation_id: str,
        query: str,
        symmetric_key: str,
        image_bytes: bytes,
        image_filename: str,
        image_mime: str,
        thumbnail_bytes: bytes | None,
        thumbnail_filename: str,
        thumbnail_mime: str,
        query_type: QueryType,
        quote: str | None,
        context: str | None,
        enable_inline_entities: bool,
        language: str,
        ui_lang: str | None,
    ) -> AsyncIterator[str | bytes]:
        url = f"{self._config.base_url}{PATH_STREAM_MULTIMODAL}"
        params = self._stream_params(
            conversation_id=conversation_id,
            query=query,
            symmetric_key=symmetric_key,
            query_type=query_type,
            quote=quote,
            context=context,
            enable_inline_entities=enable_inline_entities,
            language=language,
            ui_lang=ui_lang,
        )
        headers = self._transport.build_cors_headers(
            referer_suffix=(f"{PATH_PRIME}?q={quote_plus(query)}&conversation={conversation_id}"),
            accept="application/json",
        )
        headers["origin"] = self._config.base_url
        files: dict[str, tuple[str, bytes, str]] = {
            "image_file": (image_filename, image_bytes, image_mime)
        }
        if thumbnail_bytes is not None:
            files["thumbnail_file"] = (
                thumbnail_filename,
                thumbnail_bytes,
                thumbnail_mime,
            )
        async for line in self._transport.stream_multipart(
            url, params=params, headers=headers, files=files
        ):
            yield line

    async def _run_tool(
        self, tool_use_event: dict[str, object], symmetric_key: str
    ) -> dict[str, object]:
        url = f"{self._config.base_url}{PATH_RUN_TOOL}"
        params = {"symmetric_key": symmetric_key}
        headers = self._transport.build_cors_headers(accept="application/json")
        headers["content-type"] = "application/json"
        headers["origin"] = self._config.base_url
        return await self._retry(
            lambda: self._do_run_tool(url, params, headers, tool_use_event),
            "run_tool",
        )

    async def _do_run_tool(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        tool_use_event: dict[str, object],
    ) -> dict[str, object]:
        response = await self._transport.request(
            "POST", url, params=params, headers=headers, json=tool_use_event
        )
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise ResponseParseError(f"Response from run_tool is not JSON: {exc}") from exc
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, object], data[0])
        if isinstance(data, dict):
            return cast(dict[str, object], data)
        return {"raw": data}

    async def _do_search(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        query: str,
        offset: int,
    ) -> SearchResult:
        response = await self._transport.request("GET", url, params=params, headers=headers)
        return parse_search_html(response.text, query=query, offset=offset)

    async def _do_suggest(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> list[SuggestItem]:
        try:
            data = await self._transport.get_json(url, params=params, headers=headers)
        except ResponseParseError:
            response = await self._transport.request("GET", url, params=params, headers=headers)
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as exc:
                raise ResponseParseError(f"Suggest response is not valid JSON: {exc}") from exc
        return parse_suggest_json(data, query=str(params["q"]))

    def _new_params(self, token: TokenModel, symmetric_key: str) -> dict[str, str]:
        cfg = self._config
        return {
            "language": cfg.language,
            "country": cfg.country,
            "ui_lang": cfg.ui_lang,
            "safesearch": cfg.safesearch,
            "force_safesearch": "1" if cfg.force_safesearch else "0",
            "units_of_measurement": cfg.units_of_measurement,
            "use_location": "1" if cfg.use_location else "0",
            "geoloc": cfg.geoloc,
            "premium_cookie_name": cfg.premium_cookie_name,
            "symmetric_key": symmetric_key,
            "source": cfg.source,
            "enable_research": "true" if cfg.enable_research else "false",
            "q": token.q,
            "nonce": token.nonce,
            "sig": token.sig,
        }

    def _stream_params(
        self,
        *,
        conversation_id: str,
        query: str,
        symmetric_key: str,
        query_type: QueryType,
        quote: str | None,
        context: str | None,
        enable_inline_entities: bool,
        language: str,
        ui_lang: str | None,
    ) -> dict[str, str]:
        cfg = self._config
        params: dict[str, str] = {
            "language": language,
            "country": cfg.country,
            "ui_lang": ui_lang or cfg.ui_lang,
            "safesearch": cfg.safesearch,
            "force_safesearch": "1" if cfg.force_safesearch else "0",
            "units_of_measurement": cfg.units_of_measurement,
            "use_location": "1" if cfg.use_location else "0",
            "geoloc": cfg.geoloc,
            "premium_cookie_name": cfg.premium_cookie_name,
            "id": conversation_id,
            "query": query,
            "symmetric_key": symmetric_key,
            "enable_inline_entities": "true" if enable_inline_entities else "false",
        }
        if query_type is not QueryType.REGULAR:
            params["query_type"] = str(query_type)
        if quote:
            params["quote"] = quote
        if context:
            params["context"] = context
        return params


__all__ = ["BraveClient"]
