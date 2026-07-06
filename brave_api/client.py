from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar
from urllib.parse import quote_plus

from ._crypto.keys import generate_symmetric_key
from ._internal.config import ClientConfig
from ._internal.constants import (
    DATA_QUERY_PARAM_NAME,
    DATA_QUERY_PARAM_VALUE,
    PATH_DATA_JSON,
    PATH_HAS_CURRENT_STATE,
    PATH_NEW,
    PATH_PRIME,
    PATH_SEARCH,
    PATH_STREAM,
    PATH_STREAM_MULTIMODAL,
    PATH_SUGGEST,
)
from ._internal.models import (
    ConversationResponse,
    SearchResult,
    SuggestItem,
    TokenModel,
)
from ._internal.types import QueryType
from ._search.parser import parse_search_html, parse_suggest_json
from ._transport.http import HTTPClient
from ._transport.retry import is_http_retryable, retry_async
from ._internal.token_extractor import find_token
from .conversation import Conversation
from .exceptions import (
    ConversationError,
    HTTPStatusError,
    InvalidResponseError,
    TransportError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from ._internal.models import StreamEvent, StreamResult

T = TypeVar("T")

logger = logging.getLogger("brave_api.client")


class BraveClient:
    def __init__(self, config: ClientConfig | None = None) -> None:
        self._config: ClientConfig = config or ClientConfig()
        self._http: HTTPClient = HTTPClient(self._config)
        self._primed: bool = False
        self._prime_lock: asyncio.Lock | None = None

    async def _get_prime_lock(self) -> asyncio.Lock:
        if self._prime_lock is None:
            self._prime_lock = asyncio.Lock()
        return self._prime_lock

    @property
    def config(self) -> ClientConfig:
        return self._config

    async def __aenter__(self) -> BraveClient:
        await self._http.__aenter__()
        await self._prime()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.close()

    async def close(self) -> None:
        await self._http.close()

    async def health_check(self) -> bool:
        try:
            await self._http.request("GET", self._config.base_url)
            return True
        except Exception:
            return False

    async def _retry(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
    ) -> T:
        return await self._http._with_rate_limit(lambda: retry_async(
            operation,
            operation_name=operation_name,
            max_attempts=self._config.max_retries,
            backoff_seconds=self._config.retry_backoff_seconds,
            jitter_min=self._config.retry_jitter_min,
            jitter_max=self._config.retry_jitter_max,
            is_retryable=is_http_retryable,
        ))

    async def _prime(self) -> None:
        if self._primed:
            return
        lock = await self._get_prime_lock()
        async with lock:
            if self._primed:
                return
            url = f"{self._config.base_url}{PATH_PRIME}"
            try:
                await self._retry(lambda: self._do_prime(url), "prime")
            except HTTPStatusError:
                raise
            except Exception as exc:
                raise TransportError(f"Failed to get prime session: {exc}") from exc
            self._primed = True

    async def _do_prime(self, url: str) -> None:
        response = await self._http.request("GET", url)
        if response.status_code >= 400:
            raise TransportError(f"Prime failed: HTTP {response.status_code}")

    async def fetch_token(self, query: str) -> TokenModel:
        url = f"{self._config.base_url}{PATH_DATA_JSON}"
        params = {"q": query, DATA_QUERY_PARAM_NAME: DATA_QUERY_PARAM_VALUE}
        headers = self._http.build_headers(
            referer_suffix=f"{PATH_PRIME}?q={quote_plus(query)}",
            accept="*/*",
            extra={"sec-fetch-mode": "cors", "sec-fetch-site": "same-origin"},
        )
        return await self._retry(
            lambda: self._do_fetch_token(url, params, headers),
            "fetch_token",
        )

    async def _do_fetch_token(self, url: str, params: dict, headers: dict) -> TokenModel:
        payload = await self._http.get_json(url, params=params, headers=headers)
        return find_token(payload)

    async def open_conversation(
        self,
        token: TokenModel,
        symmetric_key: str | None = None,
    ) -> ConversationResponse:
        key = symmetric_key or generate_symmetric_key()
        url = f"{self._config.base_url}{PATH_NEW}"
        params = self._new_params(token=token, symmetric_key=key)
        headers = self._http.build_cors_headers(accept="application/json")
        return await self._retry(
            lambda: self._do_open_conversation(url, params, headers, key),
            "open_conversation",
        )

    async def _do_open_conversation(
        self, url: str, params: dict, headers: dict, key: str
    ) -> ConversationResponse:
        payload = await self._http.get_json(url, params=params, headers=headers)
        conversation_id = payload.get("id")
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ConversationError(f"Response /new missing id: {payload!r}")
        return ConversationResponse(
            id=conversation_id,
            symmetric_key=key,
            bo_callback_share_link=payload.get("bo_callback_share_link"),
            bo_callback_open_modal=payload.get("bo_callback_open_modal"),
        )

    async def refresh_conversation_data(
        self,
        *,
        query: str,
        conversation_id: str,
    ) -> dict[str, object]:
        url = f"{self._config.base_url}{PATH_DATA_JSON}"
        params = {
            "q": query,
            "conversation": conversation_id,
            DATA_QUERY_PARAM_NAME: DATA_QUERY_PARAM_VALUE,
        }
        headers = self._http.build_headers(
            referer_suffix=f"{PATH_PRIME}?q={quote_plus(query)}",
            accept="*/*",
        )
        return await self._http.get_json(url, params=params, headers=headers)

    async def _stream_raw(
        self,
        *,
        conversation_id: str,
        query: str,
        symmetric_key: str,
        query_type: str,
        quote: str | None,
        context: str | None,
        enable_inline_entities: bool,
        language: str | None = None,
        ui_lang: str | None = None,
    ) -> AsyncGenerator[str | bytes, None]:
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
        headers = self._http.build_cors_headers(accept="application/json")
        async for line in self._http.stream(url, params=params, headers=headers):
            yield line

    async def _stream_raw_multimodal(
        self,
        *,
        conversation_id: str,
        query: str,
        symmetric_key: str,
        image_bytes: bytes,
        image_filename: str = "image.jpg",
        image_mime: str = "image/jpeg",
        thumbnail_bytes: bytes | None = None,
        thumbnail_filename: str = "thumbnail.jpg",
        thumbnail_mime: str = "image/jpeg",
        query_type: str = "regular",
        quote: str | None = None,
        context: str | None = None,
        enable_inline_entities: bool = True,
        language: str | None = None,
        ui_lang: str | None = None,
    ) -> AsyncGenerator[str | bytes, None]:
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
        headers = self._http.build_cors_headers(
            referer_suffix=f"{PATH_PRIME}?q={quote_plus(query)}&conversation={conversation_id}",
            accept="application/json",
        )
        headers["origin"] = self._config.base_url
        files = {"image_file": (image_filename, image_bytes, image_mime)}
        if thumbnail_bytes is not None:
            files["thumbnail_file"] = (
                thumbnail_filename,
                thumbnail_bytes,
                thumbnail_mime,
            )
        async for line in self._http.stream_multipart(
            url, params=params, headers=headers, files=files
        ):
            yield line

    async def ask(
        self,
        query: str,
        *,
        image: bytes | str | Path | None = None,
        image_filename: str = "image.jpg",
        image_mime: str = "image/jpeg",
        language: str | None = None,
        ui_lang: str | None = None,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
    ) -> StreamResult:
        conv = await self.conversation(
            query,
            image=image,
            image_filename=image_filename,
            image_mime=image_mime,
            language=language,
            ui_lang=ui_lang,
            query_type=query_type,
            quote=quote,
            context=context,
            auto_tools=auto_tools,
        )
        return await conv.collect()

    async def ask_stream(
        self,
        query: str,
        *,
        image: bytes | str | Path | None = None,
        image_filename: str = "image.jpg",
        image_mime: str = "image/jpeg",
        language: str | None = None,
        ui_lang: str | None = None,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        conv = await self.conversation(
            query,
            image=image,
            image_filename=image_filename,
            image_mime=image_mime,
            language=language,
            ui_lang=ui_lang,
            query_type=query_type,
            quote=quote,
            context=context,
            auto_tools=auto_tools,
        )
        async for event in conv.stream_events():
            yield event

    async def search(
        self,
        query: str,
        *,
        offset: int = 0,
        spellcheck: bool = True,
        source: str = "web",
    ) -> SearchResult:
        url = f"{self._config.base_url}{PATH_SEARCH}"
        params: dict[str, str] = {"q": query, "source": source}
        if offset > 0:
            params["offset"] = str(offset)
        if not spellcheck:
            params["spellcheck"] = "0"
        headers = self._http.build_headers(
            referer_suffix=PATH_PRIME,
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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

    async def _do_search(
        self, url: str, params: dict, headers: dict, query: str, offset: int
    ) -> SearchResult:
        response = await self._http.request("GET", url, params=params, headers=headers)
        return parse_search_html(response.text, query=query, offset=offset)

    async def suggest(
        self,
        query: str,
        *,
        rich: bool = True,
        source: str = "web",
    ) -> list[SuggestItem]:
        url = f"{self._config.base_url}{PATH_SUGGEST}"
        params = {
            "q": query,
            "rich": "true" if rich else "false",
            "source": source,
            "country": self._config.country,
        }
        headers = self._http.build_headers(
            referer_suffix="/",
            accept="*/*",
            extra={
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
        )
        return await self._retry(
            lambda: self._do_suggest(url, params, headers, query),
            "suggest",
        )

    async def _do_suggest(
        self, url: str, params: dict, headers: dict, query: str
    ) -> list[SuggestItem]:
        try:
            data = await self._http.get_json(url, params=params, headers=headers)
        except InvalidResponseError:
            response = await self._http.request("GET", url, params=params, headers=headers)
            data = json.loads(response.text)
        return parse_suggest_json(data, query=query)

    async def _run_tool(
        self,
        tool_use_event: dict[str, object],
        symmetric_key: str,
    ) -> dict[str, object]:
        url = f"{self._config.base_url}/api/tap/v1/run_tool"
        params = {"symmetric_key": symmetric_key}
        headers = self._http.build_cors_headers(accept="application/json")
        headers["content-type"] = "application/json"
        headers["origin"] = self._config.base_url
        return await self._retry(
            lambda: self._do_run_tool(url, params, headers, tool_use_event),
            "run_tool",
        )

    async def _do_run_tool(
        self, url: str, params: dict, headers: dict, tool_use_event: dict
    ) -> dict[str, object]:
        response = await self._http.request(
            "POST", url, params=params, headers=headers, json_body=tool_use_event
        )
        try:
            data = response.json()
        except Exception as exc:
            raise TransportError(f"Response from run_tool is not JSON: {exc}") from exc
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            return data
        return {"raw": data}

    async def _has_current_state(self, conversation_ids: list[str]) -> dict[str, bool]:
        url = f"{self._config.base_url}{PATH_HAS_CURRENT_STATE}"
        headers = self._http.build_cors_headers(accept="application/json")
        headers["content-type"] = "application/json"
        headers["origin"] = self._config.base_url
        return await self._retry(
            lambda: self._do_has_current_state(url, headers, conversation_ids),
            "has_current_state",
        )

    async def _do_has_current_state(
        self, url: str, headers: dict, conversation_ids: list[str]
    ) -> dict[str, bool]:
        payload = await self._http.get_json(
            url, headers=headers, json_body={"ids": conversation_ids}
        )
        if not isinstance(payload, dict):
            return {}
        return {key: bool(value) for key, value in payload.items()}

    async def conversation(
        self,
        query: str,
        *,
        conversation_id: str | None = None,
        symmetric_key: str | None = None,
        image: bytes | str | Path | None = None,
        image_filename: str = "image.jpg",
        image_mime: str = "image/jpeg",
        language: str | None = None,
        ui_lang: str | None = None,
        query_type: QueryType = QueryType.REGULAR,
        quote: str | None = None,
        context: str | None = None,
        auto_tools: bool = True,
    ) -> Conversation:

        conversation_obj = Conversation(
            self,
            query,
            query_type=query_type,
            quote=quote,
            context=context,
            auto_tools=auto_tools,
        )

        if conversation_id and symmetric_key:
            conversation_obj._id = conversation_id
            conversation_obj._symmetric_key = symmetric_key

        if image is not None:
            await conversation_obj.attach_image(image, filename=image_filename, mime=image_mime)

        if language is not None:
            conversation_obj.set_language(language, ui_lang)

        if not conversation_obj.is_open:
            await conversation_obj.open()

        return conversation_obj

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
        query_type: str,
        quote: str | None,
        context: str | None,
        enable_inline_entities: bool,
        language: str | None = None,
        ui_lang: str | None = None,
    ) -> dict[str, str]:
        cfg = self._config
        params: dict[str, str] = {
            "language": language or cfg.language,
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
        if query_type and query_type is not QueryType.REGULAR:
            params["query_type"] = str(query_type)
        if quote:
            params["quote"] = quote
        if context:
            params["context"] = context
        return params


__all__ = ["BraveClient"]