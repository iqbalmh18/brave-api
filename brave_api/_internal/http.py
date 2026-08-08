"""HTTP transport built on curl_cffi.

Responsibilities, and only these:

- manage the underlying :class:`curl_cffi.requests.AsyncSession` lifecycle
- translate every third-party exception into the :mod:`brave_api.exceptions`
  hierarchy (curl errors -> ``TransportError``, non-2xx -> ``HTTPStatusError``,
  bad JSON -> ``ResponseParseError``)
- enforce the per-client concurrency limit (one semaphore per attempt/stream)
- rotate through the :class:`ProxyPool` on transport-level failures only

Semantic failures (``HTTPStatusError``, ``ResponseParseError`` and friends) are
never treated as proxy failures, so non-idempotent requests are never replayed
through a different proxy because of a server-side or parsing problem.
"""

from __future__ import annotations

import asyncio
import json as json_module
import logging
from collections.abc import AsyncIterator, Awaitable
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from curl_cffi import CurlMime
from curl_cffi.requests import (
    AsyncSession,
    BrowserTypeLiteral,
    ProxySpec,
    RequestsError,
    Response,
)

from ..config import ClientConfig
from ..exceptions import HTTPStatusError, ResponseParseError, TransportError
from .constants import (
    ACCEPT_LANGUAGE,
    PRIORITY_HEADER,
    SEC_CH_UA,
    SEC_CH_UA_MOBILE,
    SEC_CH_UA_PLATFORM,
    SEC_FETCH_MODE_CORS,
    SEC_FETCH_SITE,
)
from .proxy import ProxyPool

Method = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
MultipartFiles = dict[str, tuple[str, bytes, str]]

logger = logging.getLogger("brave_api.transport")

_GENERATOR_QUIRK = "generator didn't stop after"


def _proxy_label(proxy: str | None) -> str:
    """Human-readable proxy label that never includes credentials."""
    if proxy is None:
        return "direct connection"
    parsed = urlsplit(proxy)
    host = parsed.hostname or "<invalid>"
    port = parsed.port or "<default>"
    return f"{parsed.scheme}://{host}:{port}"


def _proxy_spec(proxy: str | None) -> ProxySpec | None:
    if proxy is None:
        return None
    return {"http": proxy, "https": proxy}


def _session_request(
    session: AsyncSession[Response],
    method: Method,
    url: str,
    *,
    params: dict[str, Any] | None,
    headers: dict[str, str] | None,
    json_body: dict[str, Any] | None,
    timeout: float | None,
    proxies: ProxySpec | None,
) -> Awaitable[Response]:
    """Typed adapter over curl_cffi's untyped ``session.request``."""
    return session.request(  # pyright: ignore[reportUnknownMemberType]
        method,
        url,
        params=params,
        headers=headers,
        json=json_body,
        timeout=timeout,
        proxies=proxies,
    )


def _aiter_lines(response: Response) -> AsyncIterator[str]:
    """Typed adapter over curl_cffi's untyped ``aiter_lines``."""
    return response.aiter_lines()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


class Transport:
    """Async HTTP client with proxy rotation, retry-safe error mapping and
    concurrency limiting."""

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._session: AsyncSession[Response] | None = None
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._proxy_pool = ProxyPool(config.proxies)

    @property
    def is_open(self) -> bool:
        return self._session is not None

    async def open(self) -> None:
        """Create the underlying session if it does not exist yet."""
        if self._session is not None:
            return
        session: AsyncSession[Response] = AsyncSession(
            impersonate=cast(BrowserTypeLiteral, self._config.impersonate),
            timeout=self._config.timeout,
            response_class=Response,
        )
        session.headers.update(self._base_headers())
        self._session = session

    async def close(self) -> None:
        """Close the underlying session. Idempotent."""
        if self._session is None:
            return
        await self._session.close()
        self._session = None

    def _base_headers(self) -> dict[str, str]:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": ACCEPT_LANGUAGE,
            "priority": PRIORITY_HEADER,
            "sec-ch-ua": SEC_CH_UA,
            "sec-ch-ua-mobile": SEC_CH_UA_MOBILE,
            "sec-ch-ua-platform": SEC_CH_UA_PLATFORM,
            "user-agent": self._config.user_agent,
            "referer": self._config.build_referer(),
            **self._config.extra_headers,
        }

    def build_headers(
        self,
        *,
        referer_suffix: str = "",
        accept: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "referer": self._config.build_referer(referer_suffix),
        }
        if accept is not None:
            headers["accept"] = accept
        if extra:
            headers.update(extra)
        return headers

    def build_cors_headers(
        self,
        *,
        referer_suffix: str = "",
        accept: str | None = None,
    ) -> dict[str, str]:
        return self.build_headers(
            referer_suffix=referer_suffix,
            accept=accept,
            extra={
                "sec-fetch-mode": SEC_FETCH_MODE_CORS,
                "sec-fetch-site": SEC_FETCH_SITE,
            },
        )

    async def request(
        self,
        method: Method,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Response:
        session = await self._ensure_session()
        async with self._semaphore:
            return await self._request_with_proxy_fallback(
                session, method, url, params, headers, json
            )

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        method: Method = "POST" if json is not None else "GET"
        response = await self.request(method, url, params=params, headers=headers, json=json)
        try:
            raw_data = json_module.loads(response.content)
        except json_module.JSONDecodeError as exc:
            raise ResponseParseError(f"Response from {url} is not valid JSON: {exc}") from exc
        if not isinstance(raw_data, dict):
            raise ResponseParseError(
                f"Response from {url} is not a JSON object: {type(raw_data).__name__}"
            )
        return cast(dict[str, Any], raw_data)

    async def _ensure_session(self) -> AsyncSession[Response]:
        if self._session is None:
            await self.open()
        if self._session is None:
            raise TransportError("HTTP session could not be opened")
        return self._session

    async def _request_with_proxy_fallback(
        self,
        session: AsyncSession[Response],
        method: Method,
        url: str,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
        json_body: dict[str, Any] | None,
    ) -> Response:
        for proxy in await self._proxy_pool.candidates():
            try:
                return await self._attempt_request(
                    session, method, url, params, headers, json_body, proxy
                )
            except TransportError:
                if proxy is None:
                    raise
                await self._proxy_pool.disable(proxy)
                logger.warning(
                    "Disabled failed proxy %s for %s %s",
                    _proxy_label(proxy),
                    method,
                    url,
                )
        raise RuntimeError("proxy candidates exhausted")  # pragma: no cover

    async def _attempt_request(
        self,
        session: AsyncSession[Response],
        method: Method,
        url: str,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
        json_body: dict[str, Any] | None,
        proxy: str | None,
    ) -> Response:
        logger.debug("Request %s %s through %s", method, url, _proxy_label(proxy))
        try:
            response = await _session_request(
                session,
                method,
                url,
                params=params,
                headers=headers,
                json_body=json_body,
                timeout=self._config.timeout,
                proxies=_proxy_spec(proxy),
            )
        except RequestsError as exc:
            raise TransportError(f"{method} {url} failed: {exc}") from exc
        self._raise_for_status(response, op=f"{method} {url}")
        return response

    async def stream(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[str | bytes]:
        session = await self._ensure_session()
        async with self._semaphore:
            for proxy in await self._proxy_pool.candidates():
                yielded = False
                try:
                    async with session.stream(
                        "GET",
                        url,
                        params=params,
                        headers=headers,
                        timeout=self._config.stream_timeout,
                        proxies=_proxy_spec(proxy),
                    ) as response:
                        self._raise_for_status(response, op=f"GET {url}")
                        async for line in _aiter_lines(response):
                            yielded = True
                            yield line
                        return
                except GeneratorExit:
                    return
                except HTTPStatusError:
                    raise
                except (RequestsError, RuntimeError) as exc:
                    if isinstance(exc, RuntimeError) and _GENERATOR_QUIRK in str(exc):
                        return
                    if proxy is None or yielded:
                        raise TransportError(f"GET {url} failed: {exc}") from exc
                    await self._proxy_pool.disable(proxy)
                    logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)

    async def stream_multipart(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        files: MultipartFiles | None = None,
        data: dict[str, str] | None = None,
    ) -> AsyncIterator[str | bytes]:
        session = await self._ensure_session()
        async with self._semaphore:
            for proxy in await self._proxy_pool.candidates():
                yielded = False
                mime = CurlMime()
                try:
                    for field, (filename, content, mime_type) in (files or {}).items():
                        mime.addpart(
                            name=field,
                            filename=filename,
                            content_type=mime_type,
                            data=content,
                        )
                    async with session.stream(
                        "POST",
                        url,
                        params=params,
                        headers=headers,
                        multipart=mime,
                        data=data,
                        timeout=self._config.stream_timeout,
                        proxies=_proxy_spec(proxy),
                    ) as response:
                        self._raise_for_status(response, op=f"POST {url}")
                        async for line in _aiter_lines(response):
                            yielded = True
                            yield line
                        return
                except GeneratorExit:
                    return
                except HTTPStatusError:
                    raise
                except (RequestsError, RuntimeError) as exc:
                    if isinstance(exc, RuntimeError) and _GENERATOR_QUIRK in str(exc):
                        return
                    if proxy is None or yielded:
                        raise TransportError(f"POST {url} failed: {exc}") from exc
                    await self._proxy_pool.disable(proxy)
                    logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)
                finally:
                    mime.close()

    @staticmethod
    def _raise_for_status(response: Response, *, op: str) -> None:
        status_code = response.status_code
        if status_code < 400:
            return
        raise HTTPStatusError(
            f"{op} failed: HTTP {status_code}",
            status_code=status_code,
            response_text=response.text,
        )


__all__ = ["Transport"]
