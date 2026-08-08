"""Tests for the brave_api.mcp adapter layer.

No real HTTP requests are made: every call to BraveClient is intercepted by a
mock that returns the minimum data needed to exercise each code path.
"""

# pyright: reportPrivateUsage=false, reportUnknownArgumentType=false

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP
from fastmcp.client import Client

from brave_api._internal.constants import (
    BASE_URL_DEFAULT,
    COUNTRY_DEFAULT,
    LANGUAGE_DEFAULT,
)
from brave_api.config import ClientConfig
from brave_api.enums import QueryType, StreamState
from brave_api.exceptions import BraveAPIError, TransportError
from brave_api.mcp.server import _build_config, create_server
from brave_api.models import (
    ImageResult,
    NewsResult,
    SearchResult,
    StreamResult,
    SuggestItem,
    SuggestResult,
    VideoResult,
    WebResult,
)


def _make_stream_result(**overrides: Any) -> StreamResult:
    defaults: dict[str, Any] = {
        "text": "This is the answer.",
        "thinking": "",
        "urls": ["https://example.com/1"],
        "images": [ImageResult(url="https://example.com/img.jpg")],
        "videos": [VideoResult(url="https://youtube.com/watch?v=abc", title="A video")],
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
    defaults: dict[str, Any] = {
        "query": "test query",
        "web": [WebResult(url="https://example.com/1", title="Example", description="A snippet.")],
        "news": [
            NewsResult(
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


def _make_suggest_result() -> SuggestResult:
    return SuggestResult(
        query="py",
        suggestions=[
            SuggestItem(text="python tutorial", is_entity=False),
            SuggestItem(
                text="Python (programming language)",
                is_entity=True,
                entity_type="ProgrammingLanguage",
                thumbnail="https://example.com/python.jpg",
            ),
        ],
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.ask = AsyncMock(return_value=_make_stream_result())
    client.search = AsyncMock(return_value=_make_search_result())
    client.suggest = AsyncMock(return_value=_make_suggest_result())
    return client


@pytest.fixture
def mcp_server(mock_client: AsyncMock) -> Generator[FastMCP]:
    with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
        yield create_server()


async def _call(server: FastMCP, tool: str, **kwargs: Any) -> Any:
    async with Client(server) as client:
        return await client.call_tool(tool, kwargs)


class TestCreateServer:
    def test_returns_fastmcp_instance(self, mcp_server: FastMCP) -> None:
        assert isinstance(mcp_server, FastMCP)

    def test_server_name(self, mcp_server: FastMCP) -> None:
        assert mcp_server.name == "Brave API"

    async def test_three_tools_registered(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        assert {tool.name for tool in tools} == {"ask", "search", "suggest"}

    async def test_tool_descriptions_present(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        by_name = {tool.name: tool for tool in tools}
        assert all(by_name[name].description for name in ("ask", "search", "suggest"))

    async def test_tools_have_readonly_annotation(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        for tool in tools:
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is True

    async def test_ask_query_type_is_an_enum_in_schema(self, mcp_server: FastMCP) -> None:
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        ask = next(tool for tool in tools if tool.name == "ask")
        enum_values = ask.inputSchema["properties"]["query_type"]["enum"]
        assert set(enum_values) == {value for value in QueryType}


class TestAskTool:
    async def test_happy_path_returns_dict(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "ask", query="Who is Ada Lovelace?")
        data = result.data
        assert isinstance(data, dict)
        assert data["text"] == "This is the answer."
        assert data["urls"] == ["https://example.com/1"]
        assert len(data["images"]) == 1
        assert data["followups"] == ["What else?"]

    async def test_calls_client_ask(self, mcp_server: FastMCP, mock_client: AsyncMock) -> None:
        await _call(mcp_server, "ask", query="Hello?")
        mock_client.ask.assert_awaited_once()
        assert mock_client.ask.call_args.args[0] == "Hello?"

    async def test_language_forwarded(self, mcp_server: FastMCP, mock_client: AsyncMock) -> None:
        await _call(mcp_server, "ask", query="Halo?", language="id")
        assert mock_client.ask.call_args.kwargs["language"] == "id"

    async def test_query_type_forwarded(self, mcp_server: FastMCP, mock_client: AsyncMock) -> None:
        await _call(mcp_server, "ask", query="Regenerate", query_type="regenerate_answer")
        assert mock_client.ask.call_args.kwargs["query_type"] == QueryType.REGENERATE_ANSWER

    async def test_brave_api_error_becomes_tool_error(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        mock_client.ask.side_effect = TransportError("Connection refused")
        with pytest.raises(Exception) as exc_info:
            await _call(mcp_server, "ask", query="test")
        assert "Connection refused" in str(exc_info.value)

    async def test_quote_context_and_auto_tools_forwarded(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        await _call(
            mcp_server,
            "ask",
            query="Explain",
            quote="some text",
            context="extra",
            auto_tools=False,
        )
        kwargs = mock_client.ask.call_args.kwargs
        assert kwargs["quote"] == "some text"
        assert kwargs["context"] == "extra"
        assert kwargs["auto_tools"] is False

    async def test_raw_events_excluded_from_response(self, mcp_server: FastMCP) -> None:
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

    async def test_args_forwarded(self, mcp_server: FastMCP, mock_client: AsyncMock) -> None:
        await _call(mcp_server, "search", query="pyton", offset=2, spellcheck=False, source="news")
        call = mock_client.search.call_args
        assert call.args[0] == "pyton"
        assert call.kwargs["offset"] == 2
        assert call.kwargs["spellcheck"] is False
        assert call.kwargs["source"] == "news"

    async def test_brave_api_error_becomes_tool_error(
        self, mcp_server: FastMCP, mock_client: AsyncMock
    ) -> None:
        mock_client.search.side_effect = BraveAPIError("Rate limited", status_code=429)
        with pytest.raises(Exception) as exc_info:
            await _call(mcp_server, "search", query="test")
        assert "Rate limited" in str(exc_info.value)


class TestSuggestTool:
    async def test_happy_path_returns_suggestions(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "suggest", query="py")
        data = result.data
        assert isinstance(data, dict)
        assert data["query"] == "py"
        assert len(data["suggestions"]) == 2

    async def test_args_forwarded(self, mcp_server: FastMCP, mock_client: AsyncMock) -> None:
        await _call(mcp_server, "suggest", query="python", rich=False, source="images")
        call = mock_client.suggest.call_args
        assert call.args[0] == "python"
        assert call.kwargs["rich"] is False
        assert call.kwargs["source"] == "images"

    async def test_entity_suggestion_fields(self, mcp_server: FastMCP) -> None:
        result = await _call(mcp_server, "suggest", query="python")
        entity = next(s for s in result.data["suggestions"] if s["is_entity"])
        assert entity["entity_type"] == "ProgrammingLanguage"
        assert entity["thumbnail"] == "https://example.com/python.jpg"


class TestBuildConfig:
    def _env_without_brave(self) -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if not k.startswith("BRAVE_")}

    def test_defaults_when_no_env_vars(self) -> None:
        with patch.dict(os.environ, self._env_without_brave(), clear=True):
            config = _build_config()
        assert config.base_url == BASE_URL_DEFAULT
        assert config.country == COUNTRY_DEFAULT
        assert config.language == LANGUAGE_DEFAULT
        assert config.enable_research is False
        assert config.proxies == []

    def test_country_language_and_geoloc_env_vars(self) -> None:
        with patch.dict(
            os.environ,
            {"BRAVE_COUNTRY": "id", "BRAVE_LANGUAGE": "id", "BRAVE_GEOLOC": "37.4x-122.1"},
        ):
            config = _build_config()
        assert config.country == "id"
        assert config.language == "id"
        assert config.geoloc == "37.4x-122.1"

    def test_enable_research_truthy_and_falsy_values(self) -> None:
        for value in ("1", "true", "True", "yes"):
            with patch.dict(os.environ, {"BRAVE_ENABLE_RESEARCH": value}):
                assert _build_config().enable_research is True
        with patch.dict(os.environ, {"BRAVE_ENABLE_RESEARCH": "0"}):
            assert _build_config().enable_research is False

    def test_timeout_and_stream_timeout_env_vars(self) -> None:
        with patch.dict(
            os.environ, {"BRAVE_REQUEST_TIMEOUT": "30.5", "BRAVE_STREAM_TIMEOUT": "60"}
        ):
            config = _build_config()
        assert config.timeout == 30.5
        assert config.stream_timeout == 60.0

    def test_invalid_timeout_falls_back_to_default(self) -> None:
        with patch.dict(os.environ, {"BRAVE_REQUEST_TIMEOUT": "not_a_number"}):
            config = _build_config()
        assert config.timeout == 120.0

    def test_int_env_vars(self) -> None:
        with patch.dict(os.environ, {"BRAVE_MAX_RETRIES": "7", "BRAVE_MAX_CONCURRENT": "10"}):
            config = _build_config()
        assert config.max_retries == 7
        assert config.max_concurrent == 10

    def test_proxy_list_env_var(self) -> None:
        with patch.dict(
            os.environ,
            {"BRAVE_PROXY_LIST": "http://a:8080, socks5://b:1080 , ,"},
        ):
            config = _build_config()
        assert config.proxies == ["http://a:8080", "socks5://b:1080"]


class TestLifespan:
    async def test_client_aenter_called_on_startup(self, mock_client: AsyncMock) -> None:
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
            server = create_server()
            async with Client(server):
                mock_client.__aenter__.assert_awaited_once()

    async def test_client_aexit_called_on_shutdown(self, mock_client: AsyncMock) -> None:
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
            server = create_server()
            async with Client(server):
                pass
        mock_client.__aexit__.assert_awaited_once()

    async def test_single_client_instance_reused(self, mock_client: AsyncMock) -> None:
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client):
            server = create_server()
            async with Client(server) as client:
                await client.call_tool("ask", {"query": "q1"})
                await client.call_tool("search", {"query": "q2"})
        assert mock_client.__aenter__.await_count == 1

    async def test_custom_config_passed_to_create_server(self) -> None:
        config = ClientConfig(country="gb", language="en")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        with patch("brave_api.mcp.server.BraveClient", return_value=mock_client) as MockClient:
            server = create_server(config=config)
            assert isinstance(server, FastMCP)
            async with Client(server):
                pass
        MockClient.assert_called_once_with(config)
