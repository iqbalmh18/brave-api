from __future__ import annotations

import functools
import logging
from typing import Annotated, Any, Awaitable, Callable, TypeVar

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from .._internal.types import QueryType
from ..client import BraveClient
from ..exceptions import BraveAPIError

logger = logging.getLogger("brave_api.mcp.tools")

_QUERY_TYPE_CHOICES = ", ".join(f'"{v}"' for v in QueryType)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _client(ctx: Context) -> BraveClient:
    return ctx.lifespan_context["client"]


def _handle_brave_errors(fn: F) -> F:
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except BraveAPIError as exc:
            logger.error("[%s] BraveAPIError: %s", fn.__name__, exc)
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
        Field(description="BCP-47 language code for the response, e.g. 'en' or 'id'. Auto-detected from the query when omitted."),
    ] = None,
    query_type: Annotated[
        str,
        Field(
            description=(
                f"Controls answer behaviour. One of: {_QUERY_TYPE_CHOICES}. "
                "Use 'regular' for a fresh answer (default), "
                "'regenerate_answer' to get a new answer for the same question."
            )
        ),
    ] = QueryType.REGULAR,
    quote: Annotated[
        str | None,
        Field(description="A snippet of text selected by the user to give context to the query."),
    ] = None,
    context: Annotated[
        str | None,
        Field(description="Additional context string appended to the query on the server side."),
    ] = None,
    auto_tools: Annotated[
        bool,
        Field(description="Allow Brave to automatically run web-search and other tool calls to enrich the answer."),
    ] = True,
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    try:
        qt = QueryType(query_type)
    except ValueError:
        raise ToolError(f"Invalid query_type {query_type!r}. Must be one of: {_QUERY_TYPE_CHOICES}.")

    result = await _client(ctx).ask(
        query,
        language=language,
        query_type=qt,
        quote=quote,
        context=context,
        auto_tools=auto_tools,
    )
    return result.model_dump(exclude={"raw_events"})


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
        Field(description="Pagination offset (0 = first page, 1 = second page, …).", ge=0),
    ] = 0,
    spellcheck: Annotated[
        bool,
        Field(description="Enable spell-check and query correction."),
    ] = True,
    source: Annotated[
        str,
        Field(description="Traffic source hint passed to Brave."),
    ] = "web",
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    result = await _client(ctx).search(query, offset=offset, spellcheck=spellcheck, source=source)
    return result.model_dump()


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
    query: Annotated[str, Field(description="A partial or complete query string for autocomplete.")],
    rich: Annotated[
        bool,
        Field(description="Include rich entity suggestions (thumbnails, entity types)."),
    ] = True,
    source: Annotated[
        str,
        Field(description="Traffic source hint passed to Brave."),
    ] = "web",
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    items = await _client(ctx).suggest(query, rich=rich, source=source)
    return {
        "query": query,
        "suggestions": [item.model_dump() for item in items],
    }


__all__ = ["ask", "search", "suggest"]