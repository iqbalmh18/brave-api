"""Unit tests for crypto, token extraction, SSE parsing, config and exceptions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brave_api._internal.crypto import generate_symmetric_key, is_valid_symmetric_key
from brave_api._internal.sse import parse_line
from brave_api._internal.token import decode_pool, find_token
from brave_api.config import ClientConfig
from brave_api.enums import StreamEventType
from brave_api.exceptions import (
    BraveAPIError,
    ChallengeRequiredError,
    ConversationError,
    HTTPStatusError,
    ResponseParseError,
    StreamAbortedError,
    TokenExtractionError,
    TransportError,
)
from brave_api.models import TokenModel


class TestSymmetricKey:
    def test_generated_key_is_valid(self) -> None:
        key = generate_symmetric_key()
        assert is_valid_symmetric_key(key)

    def test_validation_rejects_short_string(self) -> None:
        assert not is_valid_symmetric_key("abc")

    def test_validation_rejects_empty_string(self) -> None:
        assert not is_valid_symmetric_key("")

    def test_validation_rejects_non_string(self) -> None:
        assert not is_valid_symmetric_key(None)  # type: ignore[arg-type]
        assert not is_valid_symmetric_key(123)  # type: ignore[arg-type]

    def test_validation_rejects_invalid_base64url(self) -> None:
        assert not is_valid_symmetric_key("!" * 43)

    def test_keys_are_unique_across_calls(self) -> None:
        assert generate_symmetric_key() != generate_symmetric_key()


class TestDecodePool:
    def test_decodes_simple_pool(self) -> None:
        pool = [{"a": 1, "b": 2}, "hello", "world"]
        assert decode_pool(pool) == {"a": "hello", "b": "world"}

    def test_negative_index_resolves_to_none(self) -> None:
        pool = [{"a": -1, "b": 1}, "value"]
        assert decode_pool(pool) == {"a": None, "b": "value"}

    def test_empty_pool_returns_none(self) -> None:
        assert decode_pool([]) is None

    def test_nested_dicts_resolve(self) -> None:
        pool = [{"outer": {"inner": 1}}, "deep"]
        assert decode_pool(pool) == {"outer": {"inner": "deep"}}

    def test_lists_resolve(self) -> None:
        pool = [{"items": [1, 2, 3]}, "a", "b", "c"]
        assert decode_pool(pool) == {"items": ["a", "b", "c"]}

    def test_booleans_pass_through(self) -> None:
        pool = [{"flag": True}, False, True]
        assert decode_pool(pool) == {"flag": True}


class TestFindToken:
    @staticmethod
    def _payload(token: dict[str, str]) -> dict[str, object]:
        return {
            "type": "data",
            "nodes": [
                {"type": "skip"},
                {"type": "data", "data": [{"token": token}, "q-text"]},
            ],
        }

    def test_finds_valid_token(self) -> None:
        payload = self._payload({"q": "x", "nonce": "n", "sig": "s"})
        assert find_token(payload) == TokenModel(q="x", nonce="n", sig="s")

    def test_missing_token_raises(self) -> None:
        with pytest.raises(TokenExtractionError):
            find_token({"nodes": [{"type": "data", "data": [{"foo": 1}]}]})

    def test_partial_token_raises(self) -> None:
        with pytest.raises(TokenExtractionError):
            find_token(self._payload({"q": "x", "nonce": "n"}))  # type: ignore[arg-type]

    def test_skip_nodes_are_skipped(self) -> None:
        payload = {
            "nodes": [
                {"type": "data", "data": [{"foo": 1}, "x"]},
                {
                    "type": "data",
                    "data": [{"token": {"q": "a", "nonce": "b", "sig": "c"}}],
                },
            ],
        }
        assert find_token(payload) == TokenModel(q="a", nonce="b", sig="c")


class TestParseLine:
    def test_parses_typed_event(self) -> None:
        event = parse_line('{"type": "text_delta", "delta": "hi"}')
        assert event is not None
        assert event.type is StreamEventType.TEXT_DELTA
        assert event.delta == "hi"

    def test_strips_data_prefix(self) -> None:
        event = parse_line('data: {"type": "text_delta", "delta": "x"}')
        assert event is not None
        assert event.delta == "x"

    def test_returns_none_for_blank(self) -> None:
        assert parse_line("") is None
        assert parse_line("   ") is None
        assert parse_line("[DONE]") is None

    def test_returns_none_for_garbage(self) -> None:
        assert parse_line("not json") is None
        assert parse_line("[1, 2, 3]") is None

    def test_unknown_type_returns_none(self) -> None:
        event = parse_line('{"type": "future_event", "foo": 1}')
        assert event is None

    def test_error_event_exposes_message(self) -> None:
        event = parse_line('{"type": "error", "message": "boom"}')
        assert event is not None
        assert event.error_message == "boom"


class TestClientConfig:
    def test_defaults_are_sane(self) -> None:
        config = ClientConfig()
        assert config.base_url.startswith("https://")
        assert config.user_agent
        assert config.max_retries >= 1

    def test_is_frozen(self) -> None:
        config = ClientConfig()
        with pytest.raises(ValidationError):
            config.timeout = 1.0  # type: ignore[misc]

    def test_build_referer(self) -> None:
        config = ClientConfig(base_url="https://example.com")
        assert config.build_referer() == "https://example.com"
        assert config.build_referer("/path") == "https://example.com/path"

    def test_rejects_http_relative_base_url(self) -> None:
        with pytest.raises(ValidationError):
            ClientConfig(base_url="example.com")

    def test_rejects_invalid_country(self) -> None:
        with pytest.raises(ValidationError):
            ClientConfig(country="US")

    def test_rejects_invalid_geoloc(self) -> None:
        with pytest.raises(ValidationError):
            ClientConfig(geoloc="jakarta")

    def test_rejects_invalid_safesearch(self) -> None:
        with pytest.raises(ValidationError):
            ClientConfig(safesearch="sometimes")  # type: ignore[arg-type]

    def test_rejects_invalid_proxy_scheme(self) -> None:
        with pytest.raises(ValidationError):
            ClientConfig(proxies=["ftp://proxy.example:21"])

    def test_deduplicates_and_normalizes_proxies(self) -> None:
        config = ClientConfig(proxies=[" http://a:8080 ", "http://a:8080", "socks5://b:1080"])
        assert config.proxies == ["http://a:8080", "socks5://b:1080"]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ClientConfig(not_a_field=True)  # type: ignore[call-arg]


class TestExceptions:
    def test_all_inherit_base(self) -> None:
        for cls in (
            TransportError,
            TokenExtractionError,
            ConversationError,
            StreamAbortedError,
            ChallengeRequiredError,
            ResponseParseError,
        ):
            err = cls("test")
            assert isinstance(err, BraveAPIError)

    def test_http_status_error_carries_status_and_body(self) -> None:
        err = HTTPStatusError("boom", status_code=400, response_text="<html>")
        assert err.status_code == 400
        assert err.response_text == "<html>"
