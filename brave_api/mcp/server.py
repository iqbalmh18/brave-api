"""FastMCP server exposing Brave API tools over stdio or HTTP/SSE."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal, cast

from fastmcp import FastMCP

from .._internal.constants import (
    BASE_URL_DEFAULT,
    COUNTRY_DEFAULT,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    GEOLOC_DEFAULT,
    LANGUAGE_DEFAULT,
    SAFESEARCH_DEFAULT,
    UI_LANG_DEFAULT,
)
from .._version import __version__
from ..client import BraveClient
from ..config import ClientConfig
from . import tools as _tools

logger = logging.getLogger("brave_api.mcp.server")

SafeSearch = Literal["off", "moderate", "strict"]

_INSTRUCTIONS = f"""\
Brave API MCP Server — powered by brave-api v{__version__}.

Available tools:
  • ask     — Ask Brave AI a question and receive a complete AI-generated
              answer with citations, images, videos, and follow-up suggestions.
  • search  — Perform a Brave Search query and retrieve structured web and
              news results (SERP, no AI answer).
  • search_images, search_news, search_videos, search_goggles — Search a
              specific Brave Search vertical with structured results.
  • suggest — Fetch autocomplete suggestions for a partial query, including
              rich entity suggestions with thumbnails.

All tools call the Brave Search API through the brave-api library.
"""


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def _parse_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning("Invalid float value %r, using default %s.", value, default)
        return default


def _parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning("Invalid int value %r, using default %s.", value, default)
        return default


def _parse_proxies(value: str) -> list[str]:
    return [proxy.strip() for proxy in value.split(",") if proxy.strip()]


def _build_config() -> ClientConfig:
    """Build a :class:`ClientConfig` from the environment.

    Invalid numeric or boolean values fall back to defaults with a warning
    instead of failing at startup.
    """
    timeout = _parse_float(
        os.getenv("BRAVE_REQUEST_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT_SECONDS)),
        DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )

    stream_timeout: float | None = None
    raw_stream_timeout = os.getenv("BRAVE_STREAM_TIMEOUT")
    if raw_stream_timeout:
        stream_timeout = _parse_float(raw_stream_timeout, 0.0) or None

    safesearch = os.getenv("BRAVE_SAFESEARCH", SAFESEARCH_DEFAULT)
    if safesearch not in {"off", "moderate", "strict"}:
        logger.warning(
            "Invalid BRAVE_SAFESEARCH %r, using default %s.", safesearch, SAFESEARCH_DEFAULT
        )
        safesearch = SAFESEARCH_DEFAULT

    return ClientConfig(
        base_url=os.getenv("BRAVE_BASE_URL", BASE_URL_DEFAULT),
        geoloc=os.getenv("BRAVE_GEOLOC", GEOLOC_DEFAULT),
        country=os.getenv("BRAVE_COUNTRY", COUNTRY_DEFAULT),
        language=os.getenv("BRAVE_LANGUAGE", LANGUAGE_DEFAULT),
        ui_lang=os.getenv("BRAVE_UI_LANG", UI_LANG_DEFAULT),
        safesearch=cast(SafeSearch, safesearch),
        enable_research=_parse_bool(os.getenv("BRAVE_ENABLE_RESEARCH", "false")),
        timeout=timeout,
        stream_timeout=stream_timeout,
        max_retries=_parse_int(
            os.getenv("BRAVE_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)),
            DEFAULT_MAX_RETRIES,
        ),
        max_concurrent=_parse_int(
            os.getenv("BRAVE_MAX_CONCURRENT", str(DEFAULT_MAX_CONCURRENT)),
            DEFAULT_MAX_CONCURRENT,
        ),
        proxies=_parse_proxies(os.getenv("BRAVE_PROXY_LIST", "")),
    )


@asynccontextmanager
async def _brave_lifespan(
    config: ClientConfig | None = None,
) -> AsyncGenerator[dict[str, BraveClient], None]:
    """Open the shared :class:`BraveClient` for the server's lifetime."""
    cfg = config or _build_config()
    async with BraveClient(cfg) as client:
        logger.info(
            "BraveClient started (base_url=%s, country=%s, language=%s).",
            cfg.base_url,
            cfg.country,
            cfg.language,
        )
        try:
            yield {"client": client}
        finally:
            logger.info("BraveClient shut down.")


def create_server(config: ClientConfig | None = None) -> FastMCP:
    """Create the FastMCP server.

    Args:
        config: Optional client configuration; when omitted, it is built from
            environment variables at lifespan startup.
    """

    @asynccontextmanager
    async def _lifespan(
        server: FastMCP,
    ) -> AsyncGenerator[dict[str, BraveClient], None]:
        async with _brave_lifespan(config) as context:
            yield context

    mcp = FastMCP(
        name="Brave API",
        instructions=_INSTRUCTIONS,
        lifespan=_lifespan,
    )
    for fn in (
        _tools.ask,
        _tools.search,
        _tools.search_images,
        _tools.search_news,
        _tools.search_videos,
        _tools.search_goggles,
        _tools.suggest,
    ):
        mcp.add_tool(fn)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Brave API MCP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--http",
        action="store_true",
        default=False,
        help="Run with HTTP/SSE transport instead of stdio.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind to (HTTP transport only).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (HTTP transport only).",
    )
    parser.add_argument(
        "--log-level",
        default="warning",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(levelname)s [%(name)s] %(message)s",
    )

    server = create_server()
    if args.http:
        server.run(
            transport="http",
            host=args.host,
            port=args.port,
            log_level=args.log_level,
        )
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()

__all__ = ["create_server", "main"]
