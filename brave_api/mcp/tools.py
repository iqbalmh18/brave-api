"""MCP tool definitions for the Brave API server.

The tools are thin adapters: they validate their inputs, call the shared
:class:`BraveClient` from the lifespan context, and translate
:class:`brave_api.BraveAPIError` failures into MCP ``ToolError``. No business
logic lives here.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypeVar

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from ..client import BraveClient
from ..enums import QueryType
from ..exceptions import BraveAPIError

logger = logging.getLogger("brave_api.mcp.tools")

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _client(ctx: Context) -> BraveClient:
    return ctx.lifespan_context["client"]


def _handle_brave_errors(fn: F) -> F:
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except BraveAPIError as exc:
            logger.error("[%s] %s", fn.__name__, exc)
            raise ToolError(str(exc)) from exc

    return wrapper  # type: ignore[return-value]


@tool(
    name="ask",
    description=(
        "Ask Brave AI a question and receive a complete AI-generated answer "
        "with citations, source URLs, images, videos, and follow-up suggestions."
    ),
    annotations=ToolAnnotations(
        title="Ask Brave AI",
        readOnlyHint=True,
        openWorldHint=True,
    ),
)
@_handle_brave_errors
async def ask(
    query: Annotated[str, Field(description="The question or prompt to send to Brave AI.")],
    language: Annotated[
        str | None,
        Field(
            description=(
                "BCP-47 language code for the response, e.g. 'en' or 'id'. "
                "Auto-detected from the query when omitted."
            )
        ),
    ] = None,
    query_type: QueryType = QueryType.REGULAR,
    quote: Annotated[
        str | None,
        Field(description="A snippet of selected text to give context to the query."),
    ] = None,
    context: Annotated[
        str | None,
        Field(description="Additional context string appended to the query on the server side."),
    ] = None,
    auto_tools: Annotated[
        bool,
        Field(
            description=(
                "Allow Brave to automatically run web-search and other tool calls "
                "to enrich the answer."
            )
        ),
    ] = True,
    # FastMCP injects the request Context and removes it from the tool schema.
    ctx: Context = None,  # type: ignore[assignment]  # injected by FastMCP
) -> dict[str, Any]:
    result = await _client(ctx).ask(
        query,
        language=language,
        query_type=query_type,
        quote=quote,
        context=context,
        auto_tools=auto_tools,
    )
    return result.model_dump()


@tool(
    name="search",
    description=(
        "Search Brave and return structured web and news results. "
        "Returns raw SERP data — no AI answer is generated."
    ),
    annotations=ToolAnnotations(
        title="Brave Web Search",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@_handle_brave_errors
async def search(
    query: Annotated[str, Field(description="The search query.")],
    offset: Annotated[
        int,
        Field(
            description="Pagination offset (0 = first page, 1 = second page, ...).",
            ge=0,
        ),
    ] = 0,
    spellcheck: Annotated[
        bool,
        Field(description="Enable spell-check and query correction."),
    ] = True,
    source: Annotated[
        str,
        Field(description="Traffic source hint passed to Brave."),
    ] = "web",
    ctx: Context = None,  # type: ignore[assignment]  # injected by FastMCP
) -> dict[str, Any]:
    result = await _client(ctx).search(query, offset=offset, spellcheck=spellcheck, source=source)
    return result.model_dump()


@tool(
    name="search_images",
    description="Search Brave Images and return structured image results.",
    annotations=ToolAnnotations(
        title="Brave Image Search", readOnlyHint=True, idempotentHint=True, openWorldHint=True
    ),
)
@_handle_brave_errors
async def search_images(
    query: Annotated[str, Field(description="The search query.")],
    offset: Annotated[int, Field(description="Pagination offset.", ge=0)] = 0,
    spellcheck: Annotated[bool, Field(description="Enable spell-check.")] = True,
    source: Annotated[str, Field(description="Traffic source hint passed to Brave.")] = "web",
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return (
        await _client(ctx).search_images(query, offset=offset, spellcheck=spellcheck, source=source)
    ).model_dump()


@tool(
    name="search_news",
    description="Search Brave News and return structured news results.",
    annotations=ToolAnnotations(
        title="Brave News Search", readOnlyHint=True, idempotentHint=True, openWorldHint=True
    ),
)
@_handle_brave_errors
async def search_news(
    query: Annotated[str, Field(description="The search query.")],
    offset: Annotated[int, Field(description="Pagination offset.", ge=0)] = 0,
    spellcheck: Annotated[bool, Field(description="Enable spell-check.")] = True,
    source: Annotated[str, Field(description="Traffic source hint passed to Brave.")] = "web",
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return (
        await _client(ctx).search_news(query, offset=offset, spellcheck=spellcheck, source=source)
    ).model_dump()


@tool(
    name="search_videos",
    description="Search Brave Videos and return structured video results.",
    annotations=ToolAnnotations(
        title="Brave Video Search", readOnlyHint=True, idempotentHint=True, openWorldHint=True
    ),
)
@_handle_brave_errors
async def search_videos(
    query: Annotated[str, Field(description="The search query.")],
    offset: Annotated[int, Field(description="Pagination offset.", ge=0)] = 0,
    spellcheck: Annotated[bool, Field(description="Enable spell-check.")] = True,
    source: Annotated[str, Field(description="Traffic source hint passed to Brave.")] = "web",
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return (
        await _client(ctx).search_videos(query, offset=offset, spellcheck=spellcheck, source=source)
    ).model_dump()


@tool(
    name="search_goggles",
    description="Search Brave using Goggles and return structured web results.",
    annotations=ToolAnnotations(
        title="Brave Goggles Search", readOnlyHint=True, idempotentHint=True, openWorldHint=True
    ),
)
@_handle_brave_errors
async def search_goggles(
    query: Annotated[str, Field(description="The search query.")],
    offset: Annotated[int, Field(description="Pagination offset.", ge=0)] = 0,
    spellcheck: Annotated[bool, Field(description="Enable spell-check.")] = True,
    source: Annotated[str, Field(description="Traffic source hint passed to Brave.")] = "web",
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return (
        await _client(ctx).search_goggles(
            query, offset=offset, spellcheck=spellcheck, source=source
        )
    ).model_dump()


@tool(
    name="suggest",
    description=(
        "Fetch autocomplete suggestions for a partial search query, including "
        "rich entity suggestions with thumbnails and entity types."
    ),
    annotations=ToolAnnotations(
        title="Brave Search Suggest",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@_handle_brave_errors
async def suggest(
    query: Annotated[
        str,
        Field(description="A partial or complete query string for autocomplete."),
    ],
    rich: Annotated[
        bool,
        Field(description="Include rich entity suggestions (thumbnails, entity types)."),
    ] = True,
    source: Annotated[
        str,
        Field(description="Traffic source hint passed to Brave."),
    ] = "web",
    ctx: Context = None,  # type: ignore[assignment]  # injected by FastMCP
) -> dict[str, Any]:
    result = await _client(ctx).suggest(query, rich=rich, source=source)
    return result.model_dump()


__all__ = [
    "ask",
    "search",
    "search_goggles",
    "search_images",
    "search_news",
    "search_videos",
    "suggest",
]
