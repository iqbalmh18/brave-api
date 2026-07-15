from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal, TypeVar
from urllib.parse import urlsplit

from curl_cffi import CurlMime
from curl_cffi.requests import AsyncSession, ProxySpec, Response

if TYPE_CHECKING:
    from .._internal.config import ClientConfig

from .._internal.constants import (
    ACCEPT_LANGUAGE,
    DEFAULT_MAX_CONCURRENT,
    PRIORITY_HEADER,
    SEC_CH_UA,
    SEC_CH_UA_MOBILE,
    SEC_CH_UA_PLATFORM,
    SEC_FETCH_MODE_CORS,
    SEC_FETCH_SITE,
)
from ..exceptions import HTTPStatusError, InvalidResponseError

Method = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
T = TypeVar("T")
logger = logging.getLogger("brave_api.transport.http")


def _proxy_label(proxy: str | None) -> str:
    if proxy is None:
        return "direct connection"
    parsed = urlsplit(proxy)
    return f"{parsed.scheme}://{parsed.hostname or '<invalid>'}:{parsed.port or '<default>'}"


class ProxyPool:
    """Round-robin proxy pool that permanently removes failed proxies."""

    def __init__(self, proxies: list[str]) -> None:
        self._proxies = list(proxies)
        self._inactive: set[str] = set()
        self._next_index = 0
        self._lock = asyncio.Lock()

    async def candidates(self) -> list[str | None]:
        async with self._lock:
            active = [proxy for proxy in self._proxies if proxy not in self._inactive]
            if active:
                start = self._next_index % len(active)
                self._next_index = (start + 1) % len(active)
                active = active[start:] + active[:start]
            return [*active, None]

    async def disable(self, proxy: str) -> None:
        async with self._lock:
            self._inactive.add(proxy)


class HTTPClient:
    def __init__(self, config: ClientConfig, max_concurrent: int | None = None) -> None:
        self._config: ClientConfig = config
        self._session: AsyncSession[Response] | None = None
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent or config.max_concurrent or DEFAULT_MAX_CONCURRENT)
        self._proxy_pool = ProxyPool(config.proxy_list)

    async def _with_rate_limit(self, operation):
        async with self._semaphore:
            return await operation()

    async def __aenter__(self) -> HTTPClient:
        await self._open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def _open(self) -> None:
        if self._session is not None:
            return
        
        session = AsyncSession(
            impersonate=self._config.impersonate,  # type: ignore[arg-type]
            timeout=self._config.request_timeout_seconds,
            response_class=Response,
        )
        session.headers.update(self._build_base_headers())
        self._session = session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def is_open(self) -> bool:
        return self._session is not None

    def _build_base_headers(self) -> dict[str, str]:
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

    async def _ensure_session(self) -> AsyncSession[Response]:
        if self._session is None:
            await self._open()
        
        assert self._session is not None
        return self._session

    async def request(
        self,
        method: Method,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Response:
        return await self._with_proxy_fallback(
            lambda proxy: self._request_with_proxy(method, url, params, headers, json_body, proxy)
        )

    async def _request_with_proxy(
        self,
        method: Method,
        url: str,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
        json_body: dict[str, Any] | None,
        proxy: str | None,
    ) -> Response:
        session = await self._ensure_session()
        response = await session.request(
            method,
            url,
            params=params,
            headers=headers,
            json=json_body,
            timeout=self._config.request_timeout_seconds,
            proxies=self._proxy_spec(proxy),
        )
        self._raise_for_status(response, op=f"{method} {url}")
        return response

    async def _with_proxy_fallback(self, operation: Callable[[str | None], Awaitable[T]]) -> T:
        candidates = await self._proxy_pool.candidates()
        for index, proxy in enumerate(candidates):
            try:
                logger.debug("Sending request through %s", _proxy_label(proxy))
                return await operation(proxy)
            except HTTPStatusError:
                raise
            except Exception as exc:
                if proxy is None:
                    raise
                await self._proxy_pool.disable(proxy)
                logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)
                if index == len(candidates) - 1:
                    raise
                logger.info("Trying the next proxy or direct connection")
        raise AssertionError("Proxy fallback exhausted without an attempt")

    @staticmethod
    def _proxy_spec(proxy: str | None) -> ProxySpec | None:
        if proxy is None:
            return None
        return {"http": proxy, "https": proxy}

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        method = "POST" if json_body is not None else "GET"
        response = await self.request(
            method,
            url,
            params=params,
            headers=headers,
            json_body=json_body,
        )
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise InvalidResponseError(f"Response is not valid JSON from {url}: {exc}") from exc
        if not isinstance(data, dict):
            raise InvalidResponseError(
                f"Response JSON is not an object from {url}: {type(data).__name__}"
            )
        return data

    async def stream(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncGenerator[str | bytes, None]:
        session = await self._ensure_session()
        for proxy in await self._proxy_pool.candidates():
            yielded = False
            try:
                logger.debug("Opening stream through %s", _proxy_label(proxy))
                async with session.stream(
                    "GET", url, params=params, headers=headers, timeout=self._config.stream_timeout_seconds,
                    proxies=self._proxy_spec(proxy),
                ) as response:
                    self._raise_for_status(response, op=f"GET {url}")
                    async for line in response.aiter_lines():
                        yielded = True
                        yield line
                    return
            except GeneratorExit:
                return
            except HTTPStatusError:
                raise
            except RuntimeError as exc:
                if "generator didn't stop after" in str(exc):
                    return
                if proxy is None or yielded:
                    raise
                await self._proxy_pool.disable(proxy)
                logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)
            except Exception as exc:
                if proxy is None or yielded:
                    raise
                await self._proxy_pool.disable(proxy)
                logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)

    async def stream_multipart(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        data: dict[str, str] | None = None,
    ) -> AsyncGenerator[str | bytes, None]:
        stream_timeout = self._config.stream_timeout_seconds
        mime = CurlMime()
        try:
            for field, (filename, content, mime_type) in (files or {}).items():
                mime.addpart(
                    name=field,
                    filename=filename,
                    content_type=mime_type,
                    data=content,
                )
            
            session = await self._ensure_session()
            for proxy in await self._proxy_pool.candidates():
                yielded = False
                try:
                    logger.debug("Opening multipart stream through %s", _proxy_label(proxy))
                    async with session.stream(
                        "POST", url, params=params, headers=headers, multipart=mime, data=data,
                        timeout=stream_timeout, proxies=self._proxy_spec(proxy),
                    ) as response:
                        self._raise_for_status(response, op=f"POST {url}")
                        async for line in response.aiter_lines():
                            yielded = True
                            yield line
                        return
                except GeneratorExit:
                    return
                except HTTPStatusError:
                    raise
                except RuntimeError as exc:
                    if "generator didn't stop after" in str(exc):
                        return
                    if proxy is None or yielded:
                        raise
                    await self._proxy_pool.disable(proxy)
                    logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)
                except Exception as exc:
                    if proxy is None or yielded:
                        raise
                    await self._proxy_pool.disable(proxy)
                    logger.warning("Disabled failed proxy %s: %s", _proxy_label(proxy), exc)
        finally:
            mime.close()

    @staticmethod
    def _raise_for_status(response: Response, *, op: str) -> None:
        status_code = response.status_code
        if status_code is None or status_code < 400:
            return
        
        raise HTTPStatusError(
            f"{op} failed: HTTP {status_code}",
            status_code=status_code,
            response_text=response.text,
        )


__all__ = ["HTTPClient", "Response"]
