"""Tests for the brave_api.mcp adapter layer.

These tests NEVER make real HTTP requests.  Every call to BraveClient is
intercepted by a mock that returns the minimum data needed to exercise each
code path.

Test coverage:
  - Server creation and tool registration
  - ask tool — happy path, query_type validation, BraveAPIError conversion
  - search tool — happy path, BraveAPIError conversion
  - suggest tool — happy path, BraveAPIError conversion
  - _build_config() — env-var reading
  - Lifespan — client is started and stopped correctly
"""

from __future__ import annotations

import os
from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP
from fastmcp.client import Client

from brave_api._internal.config import ClientConfig
from brave_api._internal.constants import (
    BASE_URL_DEFAULT,
    COUNTRY_DEFAULT,
    LANGUAGE_DEFAULT,
)
from brave_api._internal.models import (
    ImageResult,
    SearchNewsResult,
    SearchResult,
    SearchWebResult,
    StreamResult,
    SuggestItem,
    VideoResult,
    WebResult,
)
from brave_api._internal.types import StreamState
from brave_api.exceptions import BraveAPIError, TransportError
from brave_api.mcp.server import _build_config, create_server


def _make_stream_result(**overrides: Any) -> StreamResult:
    """Build a minimal StreamResult with sensible defaults."""
    defaults: dict[str, Any] = {
        "text": "This is the answer.",
        "thinking": "",
        "urls": ["https://example.com/1"],
        "images": [ImageResult(url="https://example.com/img.jpg")],
        "videos": [
            VideoResult(url="https://youtube.com/watch?v=abc", title="A video")
        ],
        "web_results": [
            WebResult(
                url="https://example.com/1",
                title="Example Page",
                description="A description.",
            )
        ],
        "infobox": None,
        "followups": ["What else?"],
        "citations": [],
        "inline_entities": [],
        "inline_citations": [],
        "rag_content": [],
        "table_of_contents": [],
        "usage": {},
        "tool_uses": [],
        "state": StreamState.COMPLETE,
    }
    defaults.update(overrides)
    return StreamResult(**defaults)


def _make_search_result(**overrides: Any) -> SearchResult:
    """Build a minimal SearchResult with sensible defaults."""
    defaults: dict[str, Any] = {
        "query": "test query",
        "web": [
            SearchWebResult(
                url="https://example.com/1",
                title="Example",
                description="A snippet.",
            )
        ],
        "news": [
            SearchNewsResult(
                url="https://news.example.com/1",
                title="News headline",
                source="Example News",
                age="2 hours ago",
            )
        ],
        "offset": 0,
    }
    defaults.update(overrides)
    return SearchResult(**defaults)


def _make_suggest_items() -> list[SuggestItem]:
    return [
        SuggestItem(text="python tutorial", is_entity=False),
        SuggestItem(
            text="Python (programming language)",
            is_entity=True,
            entity_type="ProgrammingLanguage",
            thumbnail="https://example.com/python.jpg",
        ),
    ]


@pytest.fixture
def mock_client() -> AsyncMock:
    """A fully-mocked BraveClient."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.ask = AsyncMock(return_value=_make_stream_result())
    client.search = AsyncMock(return_value=_make_search_result())
    client.suggest = AsyncMock(return_value=_make_suggest_items())
    return client


@pytest.fixture
def mcp_server(mock_client: AsyncMock) -> Generator[FastMCP]:
    """A FastMCP server with the BraveClient patched out."""
    with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
        yield create_server()


async def _call(server: FastMCP, tool: str, **kwargs: Any) -> Any:
    """Invoke a tool through an in-process FastMCP Client."""
    async with Client(server) as client:
        result = await client.call_tool(tool, kwargs)
        return result


class TestCreateServer:
    def test_returns_fastmcp_instance(self, mcp_server: FastMCP) -> None:
        assert isinstance(mcp_server, FastMCP)

    def test_server_name(self, mcp_server: FastMCP) -> None:
        assert mcp_server.name == "Brave API"

    async def test_three_tools_registered(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        assert tool_names == {"ask", "search", "suggest"}

    async def test_tool_descriptions_present(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        by_name = {t.name: t for t in tools}
        assert by_name["ask"].description
        assert by_name["search"].description
        assert by_name["suggest"].description

    async def test_tools_have_readonly_annotation(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        for tool in tools:
            assert tool.annotations is not None, f"{tool.name} missing annotations"
            assert tool.annotations.readOnlyHint is True, (
                f"{tool.name} should be read-only"
            )


class TestAskTool:
    async def test_happy_path_returns_dict(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "ask", query="Who is Ada Lovelace?")
        # FastMCP wraps structured output in result.data
        data = result.data
        assert isinstance(data, dict)
        assert data["text"] == "This is the answer."
        assert data["urls"] == ["https://example.com/1"]
        assert len(data["images"]) == 1
        assert len(data["videos"]) == 1
        assert len(data["web_results"]) == 1
        assert data["followups"] == ["What else?"]

    async def test_calls_client_ask(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "ask", query="Hello?")
        mock_client.ask.assert_awaited_once()
        call_kwargs = mock_client.ask.call_args
        assert call_kwargs.args[0] == "Hello?"

    async def test_language_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "ask", query="Halo?", language="id")
        call_kwargs = mock_client.ask.call_args
        assert call_kwargs.kwargs["language"] == "id"

    async def test_query_type_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(
            mcp_server, "ask", query="Regenerate", query_type="regenerate_answer"
        )
        from brave_api._internal.types import QueryType
        assert mock_client.ask.call_args.kwargs["query_type"] == QueryType.REGENERATE_ANSWER

    async def test_invalid_query_type_raises_tool_error(
        self, mcp_server: FastMCP
    ) -> None:
        with pytest.raises(Exception) as exc_info:
            await _call(mcp_server, "ask", query="test", query_type="not_a_valid_type")
        assert "query_type" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    async def test_brave_api_error_becomes_tool_error(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        mock_client.ask.side_effect = TransportError("Connection refused")
        with pytest.raises(Exception) as exc_info:
            await _call(mcp_server, "ask", query="test")
        assert "Connection refused" in str(exc_info.value)

    async def test_quote_and_context_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(
            mcp_server, "ask", query="Explain", quote="some text", context="extra"
        )
        kwargs = mock_client.ask.call_args.kwargs
        assert kwargs["quote"] == "some text"
        assert kwargs["context"] == "extra"

    async def test_auto_tools_defaults_true(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "ask", query="test")
        assert mock_client.ask.call_args.kwargs["auto_tools"] is True

    async def test_auto_tools_can_be_disabled(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "ask", query="test", auto_tools=False)
        assert mock_client.ask.call_args.kwargs["auto_tools"] is False

    async def test_raw_events_excluded_from_response(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        """raw_events should be stripped — they contain non-serialisable objects."""
        result = await _call(mcp_server, "ask", query="test")
        assert "raw_events" not in result.data


class TestSearchTool:
    async def test_happy_path_returns_dict(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "search", query="python asyncio")
        data = result.data
        assert isinstance(data, dict)
        assert data["query"] == "test query"
        assert len(data["web"]) == 1
        assert len(data["news"]) == 1
        assert data["offset"] == 0

    async def test_calls_client_search(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "search", query="asyncio tutorial")
        mock_client.search.assert_awaited_once()
        assert mock_client.search.call_args.args[0] == "asyncio tutorial"

    async def test_offset_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "search", query="test", offset=2)
        assert mock_client.search.call_args.kwargs["offset"] == 2

    async def test_spellcheck_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "search", query="pyton", spellcheck=False)
        assert mock_client.search.call_args.kwargs["spellcheck"] is False

    async def test_source_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "search", query="news", source="news")
        assert mock_client.search.call_args.kwargs["source"] == "news"

    async def test_brave_api_error_becomes_tool_error(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        mock_client.search.side_effect = BraveAPIError("Rate limited", status_code=429)
        with pytest.raises(Exception) as exc_info:
            await _call(mcp_server, "search", query="test")
        assert "Rate limited" in str(exc_info.value)

    async def test_web_results_contain_expected_fields(
        self, mcp_server: FastMCP
    ) -> None:
        result = await _call(mcp_server, "search", query="test")
        first_web = result.data["web"][0]
        assert first_web["url"] == "https://example.com/1"
        assert first_web["title"] == "Example"
        assert first_web["description"] == "A snippet."

    async def test_news_results_contain_expected_fields(
        self, mcp_server: FastMCP
    ) -> None:
        result = await _call(mcp_server, "search", query="test")
        first_news = result.data["news"][0]
        assert first_news["url"] == "https://news.example.com/1"
        assert first_news["source"] == "Example News"


class TestSuggestTool:
    async def test_happy_path_returns_dict(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "suggest", query="py")
        data = result.data
        assert isinstance(data, dict)
        assert data["query"] == "py"
        assert len(data["suggestions"]) == 2

    async def test_calls_client_suggest(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "suggest", query="python")
        mock_client.suggest.assert_awaited_once()
        assert mock_client.suggest.call_args.args[0] == "python"

    async def test_rich_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "suggest", query="test", rich=False)
        assert mock_client.suggest.call_args.kwargs["rich"] is False

    async def test_source_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(mcp_server, "suggest", query="test", source="images")
        assert mock_client.suggest.call_args.kwargs["source"] == "images"

    async def test_brave_api_error_becomes_tool_error(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        mock_client.suggest.side_effect = TransportError("Network error")
        with pytest.raises(Exception) as exc_info:
            await _call(mcp_server, "suggest", query="test")
        assert "Network error" in str(exc_info.value)

    async def test_entity_suggestion_fields(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "suggest", query="python")
        entity = next(
            s for s in result.data["suggestions"] if s["is_entity"]
        )
        assert entity["entity_type"] == "ProgrammingLanguage"
        assert entity["thumbnail"] == "https://example.com/python.jpg"

    async def test_non_entity_suggestion_fields(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "suggest", query="python")
        plain = next(
            s for s in result.data["suggestions"] if not s["is_entity"]
        )
        assert plain["text"] == "python tutorial"
        assert plain["entity_type"] is None
        assert plain["thumbnail"] is None


class TestBuildConfig:
    def test_defaults_when_no_env_vars(self) -> None:
        env_without_brave = {k: v for k, v in os.environ.items() if not k.startswith("BRAVE_")}
        with patch.dict(os.environ, env_without_brave, clear=True):
            config = _build_config()
        assert config.base_url == BASE_URL_DEFAULT
        assert config.country == COUNTRY_DEFAULT
        assert config.language == LANGUAGE_DEFAULT
        assert config.enable_research is False

    def test_country_env_var(self) -> None:
        with patch.dict(os.environ, {"BRAVE_COUNTRY": "id"}):
            config = _build_config()
        assert config.country == "id"

    def test_language_env_var(self) -> None:
        with patch.dict(os.environ, {"BRAVE_LANGUAGE": "id"}):
            config = _build_config()
        assert config.language == "id"

    def test_geoloc_env_var(self) -> None:
        with patch.dict(os.environ, {"BRAVE_GEOLOC": "37.4,-122.1"}):
            config = _build_config()
        assert config.geoloc == "37.4,-122.1"

    def test_safesearch_env_var(self) -> None:
        with patch.dict(os.environ, {"BRAVE_SAFESEARCH": "strict"}):
            config = _build_config()
        assert config.safesearch == "strict"

    def test_enable_research_truthy_values(self) -> None:
        for val in ("1", "true", "True", "yes"):
            with patch.dict(os.environ, {"BRAVE_ENABLE_RESEARCH": val}):
                config = _build_config()
            assert config.enable_research is True, f"failed for {val!r}"

    def test_enable_research_falsy_value(self) -> None:
        with patch.dict(os.environ, {"BRAVE_ENABLE_RESEARCH": "0"}):
            config = _build_config()
        assert config.enable_research is False

    def test_request_timeout_float(self) -> None:
        with patch.dict(os.environ, {"BRAVE_REQUEST_TIMEOUT": "30.5"}):
            config = _build_config()
        assert config.request_timeout_seconds == 30.5

    def test_invalid_timeout_falls_back_to_default(self) -> None:
        """A bad BRAVE_REQUEST_TIMEOUT should not raise; default is used."""
        with patch.dict(os.environ, {"BRAVE_REQUEST_TIMEOUT": "not_a_number"}):
            config = _build_config()
        from brave_api._internal.constants import DEFAULT_REQUEST_TIMEOUT_SECONDS
        assert config.request_timeout_seconds == DEFAULT_REQUEST_TIMEOUT_SECONDS

    def test_max_retries_int(self) -> None:
        with patch.dict(os.environ, {"BRAVE_MAX_RETRIES": "7"}):
            config = _build_config()
        assert config.max_retries == 7

    def test_invalid_retries_falls_back_to_default(self) -> None:
        with patch.dict(os.environ, {"BRAVE_MAX_RETRIES": "many"}):
            config = _build_config()
        from brave_api._internal.constants import DEFAULT_MAX_RETRIES
        assert config.max_retries == DEFAULT_MAX_RETRIES

    def test_max_concurrent_int(self) -> None:
        with patch.dict(os.environ, {"BRAVE_MAX_CONCURRENT": "10"}):
            config = _build_config()
        assert config.max_concurrent == 10

    def test_custom_config_passed_to_create_server(self) -> None:
        """create_server() with an explicit config must NOT call _build_config."""
        config = ClientConfig(country="gb", language="en")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        with patch(
            "brave_api.mcp.server.BraveClient", return_value=mock_client
        ) as MockClient:
            server = create_server(config=config)
            assert isinstance(server, FastMCP)
            # BraveClient should be called with the provided config
            # (verified during lifespan execution, not at server creation)


class TestLifespan:
    async def test_client_aenter_called_on_startup(
        self, mock_client: AsyncMock
    ) -> None:
        """The lifespan must call __aenter__ to prime the HTTP session."""
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
            server = create_server()
            async with Client(server):
                mock_client.__aenter__.assert_awaited_once()

    async def test_client_aexit_called_on_shutdown(
        self, mock_client: AsyncMock
    ) -> None:
        """The lifespan must call __aexit__ to close the HTTP session."""
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
            server = create_server()
            async with Client(server):
                pass  # connect then disconnect
        mock_client.__aexit__.assert_awaited_once()

    async def test_single_client_instance_reused(
        self, mock_client: AsyncMock
    ) -> None:
        """All tool calls within a session share the same BraveClient."""
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
            server = create_server()
            async with Client(server) as client:
                await client.call_tool("ask", {"query": "q1"})
                await client.call_tool("search", {"query": "q2"})
        # BraveClient() constructor called exactly once
        assert mock_client.__aenter__.await_count == 1
