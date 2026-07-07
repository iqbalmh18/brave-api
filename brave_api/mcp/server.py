from __future__ import annotations

import argparse
import logging
import os

from contextlib import asynccontextmanager
from fastmcp import FastMCP
from typing import AsyncGenerator

from .._internal.config import ClientConfig
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
    VERSION,
)
from ..client import BraveClient
from . import tools as _tools

logger = logging.getLogger("brave_api.mcp.server")

_INSTRUCTIONS = f"""\
Brave API MCP Server — powered by brave-api v{VERSION}.

Available tools:
  • ask     — Ask Brave AI a question and receive a complete AI-generated
              answer with citations, images, videos, and follow-up suggestions.
  • search  — Perform a Brave Search query and retrieve structured web and
              news results (SERP, no AI answer).
  • suggest — Fetch autocomplete suggestions for a partial query, including
              rich entity suggestions with thumbnails.

All tools call the Brave Search API through the existing brave-api library.
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


def _build_config() -> ClientConfig:
    return ClientConfig(
        base_url=os.getenv("BRAVE_BASE_URL", BASE_URL_DEFAULT),
        geoloc=os.getenv("BRAVE_GEOLOC", GEOLOC_DEFAULT),
        country=os.getenv("BRAVE_COUNTRY", COUNTRY_DEFAULT),
        language=os.getenv("BRAVE_LANGUAGE", LANGUAGE_DEFAULT),
        ui_lang=os.getenv("BRAVE_UI_LANG", UI_LANG_DEFAULT),
        safesearch=os.getenv("BRAVE_SAFESEARCH", SAFESEARCH_DEFAULT),
        enable_research=_parse_bool(os.getenv("BRAVE_ENABLE_RESEARCH", "false")),
        request_timeout_seconds=_parse_float(
            os.getenv("BRAVE_REQUEST_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT_SECONDS)),
            float(DEFAULT_REQUEST_TIMEOUT_SECONDS),
        ),
        max_retries=_parse_int(
            os.getenv("BRAVE_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)),
            int(DEFAULT_MAX_RETRIES),
        ),
        max_concurrent=_parse_int(
            os.getenv("BRAVE_MAX_CONCURRENT", str(DEFAULT_MAX_CONCURRENT)),
            int(DEFAULT_MAX_CONCURRENT),
        ),
    )


@asynccontextmanager
async def _brave_lifespan(
    server: FastMCP,
    config: ClientConfig | None = None,
) -> AsyncGenerator[dict, None]:
    cfg = config or _build_config()
    async with BraveClient(cfg) as client:
        logger.info(
            "BraveClient starting up (base_url=%s, country=%s, language=%s).",
            cfg.base_url,
            cfg.country,
            cfg.language,
        )
        try:
            yield {"client": client}
        finally:
            logger.info("BraveClient shut down.")


def create_server(config: ClientConfig | None = None) -> FastMCP:
    @asynccontextmanager
    async def _lifespan(server: FastMCP) -> AsyncGenerator[dict, None]:
        async with _brave_lifespan(server, config=config) as ctx:
            yield ctx

    mcp = FastMCP(
        name="Brave API",
        instructions=_INSTRUCTIONS,
        lifespan=_lifespan,
    )
    for fn in (_tools.ask, _tools.search, _tools.suggest):
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