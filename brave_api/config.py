"""Client configuration.

:class:`ClientConfig` is a frozen Pydantic model: every field is validated at
construction time, and instances cannot be mutated after creation.
"""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._internal.constants import (
    BASE_URL_DEFAULT,
    COUNTRY_DEFAULT,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    GEOLOC_DEFAULT,
    IMPERSONATE_DEFAULT,
    LANGUAGE_DEFAULT,
    PREMIUM_COOKIE_NAME_DEFAULT,
    SAFESEARCH_DEFAULT,
    SOURCE_DEFAULT,
    UI_LANG_DEFAULT,
    UNITS_DEFAULT,
    USER_AGENT_DEFAULT,
)

_COUNTRY_RE = re.compile(r"^[a-z]{2}$")
_LANGUAGE_RE = re.compile(r"^[a-z]{2}(?:-[a-zA-Z0-9]{2,8})?$")
_GEOLOC_RE = re.compile(r"^-?\d+(?:\.\d+)?x-?\d+(?:\.\d+)?$")


class ClientConfig(BaseModel):
    """Configuration for :class:`brave_api.BraveClient`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_url: str = Field(
        default=BASE_URL_DEFAULT,
        description="Base URL of the Brave Search API.",
    )
    impersonate: str = Field(
        default=IMPERSONATE_DEFAULT,
        description="Browser fingerprint used by curl_cffi.",
    )
    user_agent: str = Field(default=USER_AGENT_DEFAULT, description="User-Agent header.")
    geoloc: str = Field(
        default=GEOLOC_DEFAULT,
        description="Geolocation as 'lat x lng', e.g. '0x0' or '-6.2x106.8'.",
    )
    country: str = Field(
        default=COUNTRY_DEFAULT,
        description="ISO 3166-1 alpha-2 country code, e.g. 'us'.",
    )
    language: str = Field(
        default=LANGUAGE_DEFAULT,
        description="Response language code (BCP-47), e.g. 'en' or 'id'.",
    )
    ui_lang: str = Field(
        default=UI_LANG_DEFAULT,
        description="UI language, e.g. 'en-us'.",
    )
    safesearch: Literal["off", "moderate", "strict"] = Field(
        default=SAFESEARCH_DEFAULT,
        description="Safe search level.",
    )
    force_safesearch: bool = Field(
        default=False, description="Force safe search regardless of user settings."
    )
    units_of_measurement: Literal["metric", "imperial"] = Field(
        default=UNITS_DEFAULT, description="Measurement system."
    )
    use_location: bool = Field(
        default=True, description="Use the configured location for search results."
    )
    premium_cookie_name: str = Field(
        default=PREMIUM_COOKIE_NAME_DEFAULT,
        description="Cookie name for Brave Premium.",
    )
    source: str = Field(
        default=SOURCE_DEFAULT,
        description="Traffic source hint sent to Brave ('home', 'search', ...).",
    )
    enable_research: bool = Field(default=False, description="Enable deep research mode.")
    timeout: float = Field(
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        gt=0,
        description="Timeout for each non-streaming HTTP request, in seconds.",
    )
    stream_timeout: float | None = Field(
        default=None,
        ge=0,
        description="Timeout for streaming connections; None means unlimited.",
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES,
        ge=0,
        description="Maximum number of retries for failed requests.",
    )
    retry_backoff: float = Field(
        default=DEFAULT_RETRY_BACKOFF_SECONDS,
        gt=0,
        description="Base retry backoff in seconds (grows exponentially).",
    )
    retry_jitter: bool = Field(
        default=True,
        description="Add random jitter (0.5x-1.5x) to each backoff delay.",
    )
    max_concurrent: int = Field(
        default=DEFAULT_MAX_CONCURRENT,
        ge=1,
        description="Maximum number of concurrent HTTP requests.",
    )
    extra_headers: dict[str, str] = Field(
        default_factory=dict[str, str], description="Additional HTTP headers sent on every request."
    )
    proxies: list[str] = Field(
        default_factory=list[str],
        description=(
            "Proxy URLs rotated in round-robin order. Direct connections are used "
            "when all proxies fail or none are configured."
        ),
    )

    def build_referer(self, path_suffix: str = "") -> str:
        """Build the Referer header value for a path suffix."""
        return f"{self.base_url}{path_suffix}"

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"base_url must be an absolute http(s) URL, got {value!r}")
        return value.rstrip("/")

    @field_validator("country")
    @classmethod
    def _validate_country(cls, value: str) -> str:
        if not _COUNTRY_RE.fullmatch(value):
            raise ValueError(f"country must be a lowercase ISO 3166-1 alpha-2 code, got {value!r}")
        return value

    @field_validator("language", "ui_lang")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        if not _LANGUAGE_RE.fullmatch(value):
            raise ValueError(f"invalid BCP-47-like language code: {value!r}")
        return value

    @field_validator("geoloc")
    @classmethod
    def _validate_geoloc(cls, value: str) -> str:
        if not _GEOLOC_RE.fullmatch(value):
            raise ValueError(f"geoloc must be a 'lat x lng' value (e.g. '0x0'), got {value!r}")
        return value

    @field_validator("proxies")
    @classmethod
    def _validate_proxies(cls, proxies: list[str]) -> list[str]:
        normalized: list[str] = []
        for proxy in proxies:
            value = proxy.strip()
            parsed = urlparse(value)
            supported = {"http", "https", "socks4", "socks4a", "socks5", "socks5h"}
            if parsed.scheme not in supported or not parsed.netloc:
                raise ValueError(f"invalid proxy URL: {proxy!r}")
            if value not in normalized:
                normalized.append(value)
        return normalized


__all__ = ["ClientConfig"]
