from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from .constants import (
    BASE_URL_DEFAULT,
    COUNTRY_DEFAULT,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_RETRY_JITTER_MAX,
    DEFAULT_RETRY_JITTER_MIN,
    DEFAULT_STREAM_TIMEOUT_SECONDS,
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


class ClientConfig(BaseModel):
    base_url: str = Field(
        default=BASE_URL_DEFAULT,
        description="Base URL for the Brave Search API",
    )
    impersonate: str = Field(
        default=IMPERSONATE_DEFAULT,
        description="Browser fingerprint used by curl_cffi",
    )
    user_agent: str = Field(
        default=USER_AGENT_DEFAULT,
        description="User-Agent header",
    )
    geoloc: str = Field(
        default=GEOLOC_DEFAULT,
        description="Geolocation coordinates (format: lat,lng)",
    )
    country: str = Field(
        default=COUNTRY_DEFAULT,
        description="Country code (ISO 3166-1 alpha-2)",
    )
    language: str = Field(
        default=LANGUAGE_DEFAULT,
        description="Response language code (id/en/etc.)",
    )
    ui_lang: str = Field(
        default=UI_LANG_DEFAULT,
        description="UI language (format: id-id, en-us, etc.)",
    )
    safesearch: str = Field(
        default=SAFESEARCH_DEFAULT,
        description="Safe search level (off/moderate/strict)",
    )
    force_safesearch: bool = Field(
        default=False,
        description="Force safe search",
    )
    units_of_measurement: str = Field(
        default=UNITS_DEFAULT,
        description="Measurement system (metric/imperial)",
    )
    use_location: bool = Field(
        default=True,
        description="Use location for search results",
    )
    premium_cookie_name: str = Field(
        default=PREMIUM_COOKIE_NAME_DEFAULT,
        description="Cookie name for Brave Premium",
    )
    source: str = Field(
        default=SOURCE_DEFAULT,
        description="Traffic source (home/search/etc.)",
    )
    enable_research: bool = Field(
        default=False,
        description="Enable research mode for deeper search results",
    )
    request_timeout_seconds: float = Field(
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        gt=0,
        description="Timeout for each non-streaming HTTP request (seconds)",
    )
    stream_timeout_seconds: float | None = Field(
        default=DEFAULT_STREAM_TIMEOUT_SECONDS,
        ge=0,
        description="Timeout for streaming connections (None = unlimited; 0 = unlimited)",
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES,
        ge=0,
        description="Maximum number of retries for failed requests",
    )
    retry_backoff_seconds: float = Field(
        default=DEFAULT_RETRY_BACKOFF_SECONDS,
        gt=0,
        description="Exponential retry backoff (seconds)",
    )
    retry_jitter_min: float = Field(
        default=DEFAULT_RETRY_JITTER_MIN,
        ge=0,
        description="Minimum jitter multiplier",
    )
    retry_jitter_max: float = Field(
        default=DEFAULT_RETRY_JITTER_MAX,
        ge=0,
        description="Maximum jitter multiplier",
    )
    max_concurrent: int = Field(
        default=DEFAULT_MAX_CONCURRENT,
        ge=1,
        description="Maximum number of concurrent requests",
    )
    extra_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers",
    )
    proxy_list: list[str] = Field(
        default_factory=list,
        description="List of proxy URLs for automatic rotation. Direct connections will be used if all proxies fail.",
    )

    model_config = {"frozen": True, "extra": "forbid"}

    def build_referer(self, path_suffix: str = "") -> str:
        return f"{self.base_url}{path_suffix}"

    @field_validator("proxy_list")
    @classmethod
    def validate_proxy_list(cls, proxies: list[str]) -> list[str]:
        normalized: list[str] = []

        for proxy in proxies:
            if not isinstance(proxy, str):
                raise ValueError("Each proxy must be a string URL")

            value = proxy.strip()
            parsed = urlparse(value)

            if (
                parsed.scheme
                not in {
                    "http",
                    "https",
                    "socks4",
                    "socks4a",
                    "socks5",
                    "socks5h",
                }
                or not parsed.netloc
            ):
                raise ValueError(f"Invalid proxy URL: {proxy!r}")

            if value not in normalized:
                normalized.append(value)

        return normalized


__all__ = ["ClientConfig"]
