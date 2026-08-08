"""Client tests using an injected fake transport (no network)."""

from __future__ import annotations

import json as json_module
from collections.abc import AsyncIterator
from typing import Any

import pytest

from brave_api.client import BraveClient
from brave_api.config import ClientConfig
from brave_api.exceptions import (
    ChallengeRequiredError,
    ConversationError,
    HTTPStatusError,
    ResponseParseError,
    StreamAbortedError,
    TransportError,
)
from brave_api.models import (
    SearchResult,
    StreamResult,
    SuggestItem,
    SuggestResult,
    WebResult,
)


class FakeResponse:
    """Minimal stand-in for a curl_cffi Response."""

    def __init__(
        self,
        status_code: int = 200,
        *,
        text: str = "",
        json_data: Any = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._json = json_data

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        return json_module.loads(self.text)


class FakeTransport:
    """Records calls and serves canned responses, mirroring Transport error mapping."""

    def __init__(self) -> None:
        self.is_open = False
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []
        self.next_response = FakeResponse()
        self.stream_lines: list[str] = []
        self.json_responses: dict[str, Any] = {}

    async def open(self) -> None:
        self.is_open = True

    async def close(self) -> None:
        self.is_open = False

    def build_headers(self, **kwargs: Any) -> dict[str, str]:
        return {}

    def build_cors_headers(self, **kwargs: Any) -> dict[str, str]:
        return {}

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.requests.append((method, url, params))
        if self.next_response.status_code >= 400:
            raise HTTPStatusError(
                f"{method} {url} failed: HTTP {self.next_response.status_code}",
                status_code=self.next_response.status_code,
                response_text=self.next_response.text,
            )
        return self.next_response

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if url in self.json_responses:
            return self.json_responses[url]
        query = params.get("q") if params else None
        if query is not None:
            return self.json_responses.get(query, {})
        return {}

    async def stream(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[str]:
        for line in self.stream_lines:
            yield line

    async def stream_multipart(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        data: dict[str, str] | None = None,
    ) -> AsyncIterator[str]:
        for line in self.stream_lines:
            yield line


NEW_URL = "https://search.brave.com/api/tap/v1/new"


def _client(transport: FakeTransport, config: ClientConfig | None = None) -> BraveClient:
    return BraveClient(config, transport=transport)  # type: ignore[arg-type]


def _token_payload() -> dict[str, Any]:
    return {"nodes": [{"type": "data", "data": [{"token": {"q": "x", "nonce": "n", "sig": "s"}}]}]}


class TestLifecycle:
    async def test_context_manager_opens_and_closes(self) -> None:
        transport = FakeTransport()
        async with _client(transport) as client:
            assert client.is_open
            assert transport.is_open
        assert not transport.is_open

    async def test_close_is_idempotent(self) -> None:
        transport = FakeTransport()
        client = _client(transport)
        await client.close()
        await client.close()
        assert not transport.is_open


class TestConversation:
    async def test_requires_id_and_key_together(self) -> None:
        transport = FakeTransport()
        client = _client(transport)
        with pytest.raises(ValueError):
            await client.conversation("q", conversation_id="abc")
        with pytest.raises(ValueError):
            await client.conversation("q", symmetric_key="key")

    async def test_new_conversation_returns_open_conversation(self) -> None:
        transport = FakeTransport()
        transport.json_responses["x"] = _token_payload()
        transport.json_responses[NEW_URL] = {"id": "conversation-123"}
        client = _client(transport)
        conv = await client.conversation("x")
        assert conv.is_open
        assert conv.id == "conversation-123"
        assert conv.symmetric_key is not None

    async def test_resume_uses_provided_credentials_without_http(self) -> None:
        transport = FakeTransport()
        client = _client(transport)
        conv = await client.conversation("x", conversation_id="cid", symmetric_key="key")
        assert conv.id == "cid"
        assert conv.symmetric_key == "key"
        assert transport.requests == []

    async def test_missing_id_raises_conversation_error(self) -> None:
        transport = FakeTransport()
        transport.json_responses["x"] = _token_payload()
        transport.json_responses[NEW_URL] = {}
        client = _client(transport)
        with pytest.raises(ConversationError):
            await client.conversation("x")


class TestAsk:
    def _setup_stream(self, lines: list[str]) -> FakeTransport:
        transport = FakeTransport()
        transport.json_responses["q1"] = _token_payload()
        transport.json_responses[NEW_URL] = {"id": "conversation-123"}
        transport.stream_lines = lines
        return transport

    async def test_ask_collects_stream_result(self) -> None:
        transport = self._setup_stream(
            [
                '{"type": "text_delta", "delta": "Hello"}',
                '{"type": "text_delta", "delta": " world"}',
                '{"type": "text_stop"}',
            ]
        )
        client = _client(transport)
        result = await client.ask("q1")
        assert isinstance(result, StreamResult)
        assert result.text == "Hello world"
        assert result.is_complete

    async def test_error_event_raises_stream_aborted(self) -> None:
        transport = self._setup_stream(['{"type": "error", "message": "rate limited"}'])
        client = _client(transport)
        with pytest.raises(StreamAbortedError, match="rate limited"):
            await client.ask("q1")

    async def test_challenge_event_raises_challenge_required(self) -> None:
        transport = self._setup_stream(['{"type": "challenge"}'])
        client = _client(transport)
        with pytest.raises(ChallengeRequiredError):
            await client.ask("q1")

    async def test_ask_stream_yields_events(self) -> None:
        transport = self._setup_stream(
            ['{"type": "text_delta", "delta": "A"}', '{"type": "text_stop"}']
        )
        client = _client(transport)
        events = [event async for event in client.ask_stream("q1")]
        assert [event.delta for event in events] == ["A", ""]


class TestSearch:
    async def test_search_returns_search_result(self) -> None:
        transport = FakeTransport()
        transport.next_response = FakeResponse(
            status_code=200,
            text=(
                '<div class="snippet" data-pos="0">'
                '<a href="https://example.com/1"><span class="snippet-title">T</span></a>'
                '<p class="snippet-description">D</p>'
                "</div>"
            ),
        )
        client = _client(transport)
        result = await client.search("python")
        assert isinstance(result, SearchResult)
        assert result.web == [WebResult(url="https://example.com/1", title="T", description="D")]

    async def test_search_passes_pagination_and_spellcheck(self) -> None:
        transport = FakeTransport()
        client = _client(transport)
        await client.search("rust", offset=1, spellcheck=False)
        method, url, params = transport.requests[-1]
        assert method == "GET"
        assert url.endswith("/search")
        assert params == {"q": "rust", "source": "web", "offset": "1", "spellcheck": "0"}


class TestSuggest:
    async def test_suggest_returns_suggest_result(self) -> None:
        transport = FakeTransport()
        transport.json_responses["py"] = ["python", ["python tutorial"]]
        client = _client(transport)
        result = await client.suggest("py")
        assert isinstance(result, SuggestResult)
        assert result.query == "py"
        assert result.suggestions == [SuggestItem(text="python tutorial")]

    async def test_suggest_falls_back_to_raw_request_on_parse_error(self) -> None:
        transport = FakeTransport()

        async def raw_request(  # type: ignore[override]
            method: str,
            url: str,
            *,
            params: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
        ) -> FakeResponse:
            transport.requests.append((method, url, params))
            return FakeResponse(status_code=200, text='["py", ["alpha", "beta"]]')

        transport.request = raw_request  # type: ignore[method-assign]
        transport.get_json = _raise_parse_error  # type: ignore[method-assign]

        client = _client(transport)
        result = await client.suggest("py")
        assert [item.text for item in result.suggestions] == ["alpha", "beta"]


async def _raise_parse_error(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise ResponseParseError("not an object")


class TestErrorMapping:
    async def test_http_status_error_propagates(self) -> None:
        transport = FakeTransport()
        config = ClientConfig(max_retries=1)
        client = _client(transport, config)
        transport.next_response = FakeResponse(status_code=429, text="slow down")
        with pytest.raises(HTTPStatusError) as exc_info:
            await client.search("x")
        assert exc_info.value.status_code == 429
        assert exc_info.value.response_text == "slow down"

    async def test_transport_errors_are_retried(self) -> None:
        class FlakyTransport(FakeTransport):
            def __init__(self) -> None:
                super().__init__()
                self.failures = 1

            async def request(  # type: ignore[override]
                self,
                method: str,
                url: str,
                *,
                params: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None,
                json: dict[str, Any] | None = None,
            ) -> FakeResponse:
                self.requests.append((method, url, params))
                if self.failures > 0:
                    self.failures -= 1
                    raise TransportError("connection reset")
                return FakeResponse(status_code=200, text="")

        transport = FlakyTransport()
        config = ClientConfig(max_retries=3, retry_backoff=0.01, retry_jitter=False)
        async with _client(transport, config):
            pass
        assert transport.failures == 0
        assert len(transport.requests) == 2

    async def test_non_retryable_errors_are_not_rerun(self) -> None:
        class BadTransport(FakeTransport):
            async def request(  # type: ignore[override]
                self, *args: Any, **kwargs: Any
            ) -> FakeResponse:
                self.requests.append(("GET", "http://bad", None))
                raise ValueError("programmer error")

        transport = BadTransport()
        config = ClientConfig(max_retries=3, retry_backoff=0.01, retry_jitter=False)
        client = _client(transport, config)
        with pytest.raises(ValueError):
            await client.search("x")
        assert len(transport.requests) == 1
