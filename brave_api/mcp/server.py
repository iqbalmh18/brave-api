from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

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

def _build_config() -> ClientConfig:
    return ClientConfig(
        base_url=os.getenv("BRAVE_BASE_URL", BASE_URL_DEFAULT),
        geoloc=os.getenv("BRAVE_GEOLOC", GEOLOC_DEFAULT),
        country=os.getenv("BRAVE_COUNTRY", COUNTRY_DEFAULT),
        language=os.getenv("BRAVE_LANGUAGE", LANGUAGE_DEFAULT),
        ui_lang=os.getenv("BRAVE_UI_LANG", UI_LANG_DEFAULT),
        safesearch=os.getenv("BRAVE_SAFESEARCH", SAFESEARCH_DEFAULT),
        enable_research=os.getenv("BRAVE_ENABLE_RESEARCH", "false").lower() == "true",
        request_timeout_seconds=float(os.getenv("BRAVE_REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT_SECONDS)),
        max_retries=int(os.getenv("BRAVE_MAX_RETRIES", DEFAULT_MAX_RETRIES)),
        max_concurrent=int(os.getenv("BRAVE_MAX_CONCURRENT", DEFAULT_MAX_CONCURRENT)),
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
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    create_server().run()


if __name__ == "__main__":
    main()


__all__ = ["create_server", "main"]