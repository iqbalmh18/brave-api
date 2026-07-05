from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from curl_cffi import CurlMime
from curl_cffi.requests import AsyncSession, Response

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from .._internal.config import ClientConfig

from .._internal.constants import (
    ACCEPT_LANGUAGE,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    PRIORITY_HEADER,
    SEC_CH_UA,
    SEC_CH_UA_MOBILE,
    SEC_CH_UA_PLATFORM,
    SEC_FETCH_MODE_CORS,
    SEC_FETCH_SITE,
)
from ..exceptions import HTTPStatusError, InvalidResponseError

Method = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]


class HTTPClient:
    def __init__(self, config: ClientConfig) -> None:
        self._config: ClientConfig = config
        self._session: AsyncSession[Response] | None = None

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

    async def _ensure_session(self) -> AsyncSession:
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
        session = await self._ensure_session()
        response = await session.request(
            method,
            url,
            params=params,
            headers=headers,
            json=json_body,
            timeout=self._config.request_timeout_seconds,
        )
        self._raise_for_status(response, op=f"{method} {url}")
        return response

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
        stream_timeout = self._config.stream_timeout_seconds
        try:
            async with session.stream(
                "GET",
                url,
                params=params,
                headers=headers,
                timeout=stream_timeout,
            ) as response:
                self._raise_for_status(response, op=f"GET {url}")
                try:
                    async for line in response.aiter_lines():
                        yield line
                except GeneratorExit:
                    return
        except RuntimeError as exc:
            if "generator didn't stop after" in str(exc):
                return
            raise

    async def stream_multipart(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        data: dict[str, str] | None = None,
    ) -> AsyncGenerator[str | bytes, None]:
        session = await self._ensure_session()
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
            
            try:
                async with session.stream(
                    "POST",
                    url,
                    params=params,
                    headers=headers,
                    multipart=mime,
                    data=data,
                    timeout=stream_timeout,
                ) as response:
                    self._raise_for_status(response, op=f"POST {url}")
                    try:
                        async for line in response.aiter_lines():
                            yield line
                    except GeneratorExit:
                        return
            except RuntimeError as exc:
                if "generator didn't stop after" in str(exc):
                    return
                raise
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


def build_default_timeout(config: ClientConfig) -> float:
    if config.request_timeout_seconds <= 0:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS
    return config.request_timeout_seconds


__all__ = ["HTTPClient", "Response", "build_default_timeout"]
