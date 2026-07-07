from __future__ import annotations

from typing import Final

BASE_URL_DEFAULT: Final[str] = "https://search.brave.com"
USER_AGENT_DEFAULT: Final[str] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
IMPERSONATE_DEFAULT: Final[str] = "chrome136"

SEC_CH_UA: Final[str] = '"Chromium";v="136", "Google Chrome";v="136", "Not)A;Brand";v="99"'
SEC_CH_UA_MOBILE: Final[str] = "?0"
SEC_CH_UA_PLATFORM: Final[str] = '"Linux"'

ACCEPT_LANGUAGE: Final[str] = "en-US,en;q=0.9"
PRIORITY_HEADER: Final[str] = "u=1, i"
SEC_FETCH_DEST: Final[str] = "empty"
SEC_FETCH_MODE_CORS: Final[str] = "cors"
SEC_FETCH_MODE_NO_CORS: Final[str] = "no-cors"
SEC_FETCH_SITE: Final[str] = "same-origin"

PREMIUM_COOKIE_NAME_DEFAULT: Final[str] = "__Secure-sku#brave-search-premium"
SOURCE_DEFAULT: Final[str] = "home"

GEOLOC_DEFAULT: Final[str] = "0x0"
COUNTRY_DEFAULT: Final[str] = "us"
LANGUAGE_DEFAULT: Final[str] = "en"
UI_LANG_DEFAULT: Final[str] = "en-us"
SAFESEARCH_DEFAULT: Final[str] = "moderate"
UNITS_DEFAULT: Final[str] = "metric"

PATH_PRIME: Final[str] = "/ask"
PATH_DATA_JSON: Final[str] = "/ask/__data.json"
PATH_NEW: Final[str] = "/api/tap/v1/new"
PATH_STREAM: Final[str] = "/api/tap/v1/stream"
PATH_STREAM_MULTIMODAL: Final[str] = "/api/tap/v1/stream_multimodal"
PATH_RUN_TOOL: Final[str] = "/api/tap/v1/run_tool"
PATH_HAS_CURRENT_STATE: Final[str] = "/api/tap/v1/has_current_state"
PATH_SEARCH: Final[str] = "/search"
PATH_SUGGEST: Final[str] = "/api/suggest"

DATA_QUERY_PARAM_NAME: Final[str] = "x-sveltekit-invalidated"
DATA_QUERY_PARAM_VALUE: Final[str] = "01"

STREAM_DONE_MARKER: Final[str] = "[DONE]"

AES_KEY_BYTES: Final[int] = 32
AES_KEY_BASE64_LENGTH: Final[int] = 43

RETRYABLE_STATUS_MAX: Final[int] = 599
RETRYABLE_CLIENT_STATUS_MAX: Final[int] = 499

DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 120.0
DEFAULT_STREAM_TIMEOUT_SECONDS: Final[float | None] = None
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_RETRY_BACKOFF_SECONDS: Final[float] = 1.5
DEFAULT_RETRY_JITTER_MIN: Final[float] = 0.5
DEFAULT_RETRY_JITTER_MAX: Final[float] = 1.5
DEFAULT_MAX_CONCURRENT: Final[int] = 5

IMAGE_MAX_DIMENSION: Final[int] = 1000
IMAGE_QUALITY: Final[int] = 92
THUMBNAIL_MAX_DIMENSION: Final[int] = 256
THUMBNAIL_QUALITY: Final[int] = 85

VERSION: Final[str] = "0.1.2"

__all__ = [
    "ACCEPT_LANGUAGE",
    "AES_KEY_BASE64_LENGTH",
    "AES_KEY_BYTES",
    "BASE_URL_DEFAULT",
    "COUNTRY_DEFAULT",
    "DATA_QUERY_PARAM_NAME",
    "DATA_QUERY_PARAM_VALUE",
    "DEFAULT_MAX_CONCURRENT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "DEFAULT_RETRY_JITTER_MAX",
    "DEFAULT_RETRY_JITTER_MIN",
    "DEFAULT_STREAM_TIMEOUT_SECONDS",
    "GEOLOC_DEFAULT",
    "IMAGE_MAX_DIMENSION",
    "IMAGE_QUALITY",
    "IMPERSONATE_DEFAULT",
    "LANGUAGE_DEFAULT",
    "PATH_DATA_JSON",
    "PATH_HAS_CURRENT_STATE",
    "PATH_NEW",
    "PATH_PRIME",
    "PATH_RUN_TOOL",
    "PATH_SEARCH",
    "PATH_STREAM",
    "PATH_STREAM_MULTIMODAL",
    "PATH_SUGGEST",
    "PREMIUM_COOKIE_NAME_DEFAULT",
    "PRIORITY_HEADER",
    "RETRYABLE_CLIENT_STATUS_MAX",
    "RETRYABLE_STATUS_MAX",
    "SAFESEARCH_DEFAULT",
    "SEC_CH_UA",
    "SEC_CH_UA_MOBILE",
    "SEC_CH_UA_PLATFORM",
    "SEC_FETCH_DEST",
    "SEC_FETCH_MODE_CORS",
    "SEC_FETCH_MODE_NO_CORS",
    "SEC_FETCH_SITE",
    "SOURCE_DEFAULT",
    "STREAM_DONE_MARKER",
    "THUMBNAIL_MAX_DIMENSION",
    "THUMBNAIL_QUALITY",
    "UI_LANG_DEFAULT",
    "UNITS_DEFAULT",
    "USER_AGENT_DEFAULT",
    "VERSION",
]
