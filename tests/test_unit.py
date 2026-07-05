"""Unit test brave_tap (tanpa jaringan)."""

from __future__ import annotations

import pytest

from brave_tap import (
    BraveTapError,
    StreamEventType,
    generate_symmetric_key,
    is_valid_symmetric_key,
)
from brave_tap._internal.config import ClientConfig
from brave_tap._internal.types import TokenDict
from brave_tap._streaming.parser import is_terminal_event, parse_line
from brave_tap._transport.sveltekit import decode_pool, find_token
from brave_tap.exceptions import (
    ChallengeRequiredError,
    ConversationError,
    HTTPStatusError,
    InvalidResponseError,
    StreamAbortedError,
    TokenExtractionError,
    TransportError,
)


class TestGenerateSymmetricKey:
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
    def _payload(self, token: dict[str, str]) -> dict[str, object]:
        return {
            "type": "data",
            "nodes": [
                {"type": "skip"},
                {"type": "data", "data": [{"token": token}, "q-text"]},
            ],
        }

    def test_finds_valid_token(self) -> None:
        payload = self._payload({"q": "x", "nonce": "n", "sig": "s"})
        assert find_token(payload) == TokenDict(q="x", nonce="n", sig="s")

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
        assert find_token(payload) == TokenDict(q="a", nonce="b", sig="c")


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

    def test_unknown_type_falls_back_to_error(self) -> None:
        event = parse_line('{"type": "future_event", "foo": 1}')
        assert event is not None
        assert event.raw_type == "future_event"
        assert event.type is StreamEventType.ERROR

    def test_is_terminal_event(self) -> None:
        terminal = parse_line('{"type": "text_stop"}')
        non_terminal = parse_line('{"type": "text_delta", "delta": "x"}')
        assert terminal is not None
        assert non_terminal is not None
        assert is_terminal_event(terminal)
        assert not is_terminal_event(non_terminal)


class TestClientConfig:
    def test_defaults_are_sane(self) -> None:
        config = ClientConfig()
        assert config.base_url.startswith("https://")
        assert config.user_agent
        assert config.max_retries >= 1

    def test_is_frozen(self) -> None:
        from pydantic import ValidationError

        config = ClientConfig()
        with pytest.raises((AttributeError, TypeError, ValidationError)):
            config.base_url = "https://evil.example"  # type: ignore[misc]

    def test_build_referer(self) -> None:
        config = ClientConfig(base_url="https://example.com")
        assert config.build_referer() == "https://example.com"
        assert config.build_referer("/path") == "https://example.com/path"


class TestExceptions:
    def test_all_inherit_base(self) -> None:
        for cls in (
            TransportError,
            TokenExtractionError,
            ConversationError,
            StreamAbortedError,
            ChallengeRequiredError,
            InvalidResponseError,
        ):
            err = cls("test")
            assert isinstance(err, BraveTapError)

    def test_http_status_error_requires_status_code(self) -> None:
        err = HTTPStatusError("boom", status_code=400, response_text="<html>")
        assert err.status_code == 400
        assert err.response_text == "<html>"
