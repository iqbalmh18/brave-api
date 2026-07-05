from __future__ import annotations

from pydantic import BaseModel, Field

from .constants import (
    BASE_URL_DEFAULT,
    COUNTRY_DEFAULT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
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
    base_url: str = Field(default=BASE_URL_DEFAULT, description="Base URL untuk Brave Search API")
    impersonate: str = Field(default=IMPERSONATE_DEFAULT, description="Browser fingerprint untuk curl_cffi")
    user_agent: str = Field(default=USER_AGENT_DEFAULT, description="User-Agent header")
    geoloc: str = Field(default=GEOLOC_DEFAULT, description="Koordinat geolokasi (format: lat,lng)")
    country: str = Field(default=COUNTRY_DEFAULT, description="Kode negara (ISO 3166-1 alpha-2)")
    language: str = Field(default=LANGUAGE_DEFAULT, description="Kode bahasa untuk respons (id/en/dll)")
    ui_lang: str = Field(default=UI_LANG_DEFAULT, description="Bahasa UI (format: id-id, en-us, dll)")
    safesearch: str = Field(default=SAFESEARCH_DEFAULT, description="Level safe search (off/moderate/strict)")
    force_safesearch: int = Field(default=0, ge=0, le=1, description="Paksa safe search (0=tidak, 1=ya)")
    units_of_measurement: str = Field(default=UNITS_DEFAULT, description="Sistem unit (metric/imperial)")
    use_location: int = Field(default=1, ge=0, le=1, description="Gunakan lokasi untuk hasil (0=tidak, 1=ya)")
    premium_cookie_name: str = Field(default=PREMIUM_COOKIE_NAME_DEFAULT, description="Nama cookie untuk Brave Premium")
    source: str = Field(default=SOURCE_DEFAULT, description="Sumber traffic (home/search/dll)")
    enable_research: bool = Field(default=False, description="Aktifkan mode research untuk pencarian mendalam")
    request_timeout_seconds: float = Field(default=DEFAULT_REQUEST_TIMEOUT_SECONDS, gt=0, description="Timeout untuk setiap request HTTP non-streaming (detik)")
    stream_timeout_seconds: float | None = Field(default=DEFAULT_STREAM_TIMEOUT_SECONDS, ge=0, description="Timeout untuk koneksi streaming (None = tidak ada batas waktu; 0 = tidak ada batas waktu)")
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=0, description="Jumlah maksimal retry untuk request yang gagal")
    retry_backoff_seconds: float = Field(default=DEFAULT_RETRY_BACKOFF_SECONDS, gt=0, description="Backoff exponential untuk retry (detik)")
    extra_headers: dict[str, str] = Field(default_factory=dict, description="Header HTTP tambahan")

    model_config = {"frozen": True, "extra": "forbid"}

    def build_referer(self, path_suffix: str = "") -> str:
        return f"{self.base_url}{path_suffix}"

    def build_correlation_id(self, query: str) -> str:
        return f"{self.impersonate}::{len(query)}::{query[:32]}"


__all__ = ["ClientConfig"]
