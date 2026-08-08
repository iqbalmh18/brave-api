"""Tests for the retry policy."""

from __future__ import annotations

import asyncio

import pytest

from brave_api._internal.retry import is_http_retryable, retry_async
from brave_api.exceptions import HTTPStatusError, TransportError


class _Failing:
    def __init__(self, failures: int, exc: Exception) -> None:
        self.remaining = failures
        self.exc = exc
        self.attempts = 0

    async def __call__(self) -> str:
        self.attempts += 1
        if self.remaining > 0:
            self.remaining -= 1
            raise self.exc
        return "ok"


class TestRetryAsync:
    async def test_retries_until_success(self) -> None:
        op = _Failing(2, TransportError("boom"))
        result = await retry_async(
            op,
            operation_name="test",
            max_attempts=5,
            backoff_seconds=0.01,
            jitter=False,
            is_retryable=is_http_retryable,
        )
        assert result == "ok"
        assert op.attempts == 3

    async def test_exhausts_after_max_attempts(self) -> None:
        op = _Failing(10, TransportError("boom"))
        with pytest.raises(TransportError):
            await retry_async(
                op,
                operation_name="test",
                max_attempts=3,
                backoff_seconds=0.01,
                jitter=False,
                is_retryable=is_http_retryable,
            )
        assert op.attempts == 3

    async def test_non_retryable_failure_raises_immediately(self) -> None:
        op = _Failing(1, HTTPStatusError("bad request", status_code=400))
        with pytest.raises(HTTPStatusError):
            await retry_async(
                op,
                operation_name="test",
                max_attempts=5,
                backoff_seconds=0.01,
                jitter=False,
                is_retryable=is_http_retryable,
            )
        assert op.attempts == 1

    async def test_raises_value_error_for_invalid_attempts(self) -> None:
        with pytest.raises(ValueError):
            await retry_async(
                lambda: asyncio.sleep(0),  # type: ignore[arg-type]
                operation_name="test",
                max_attempts=0,
                backoff_seconds=0.01,
                jitter=False,
                is_retryable=is_http_retryable,
            )

    async def test_cancellation_is_not_retried(self) -> None:
        op = _Failing(0, TransportError("boom"))

        async def cancelled() -> str:
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await retry_async(
                cancelled,
                operation_name="test",
                max_attempts=5,
                backoff_seconds=0.01,
                jitter=False,
                is_retryable=is_http_retryable,
            )
        assert op.attempts == 0

    async def test_backoff_grows_exponentially(self, monkeypatch: pytest.MonkeyPatch) -> None:
        delays: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            delays.append(seconds)

        monkeypatch.setattr("brave_api._internal.retry.asyncio.sleep", fake_sleep)

        op = _Failing(3, TransportError("boom"))
        await retry_async(
            op,
            operation_name="test",
            max_attempts=4,
            backoff_seconds=2.0,
            jitter=False,
            is_retryable=is_http_retryable,
        )
        assert delays == [2.0, 4.0, 8.0]


class TestIsHttpRetryable:
    def test_transport_errors_are_retryable(self) -> None:
        assert is_http_retryable(TransportError("boom"))

    def test_http_429_is_retryable(self) -> None:
        assert is_http_retryable(HTTPStatusError("x", status_code=429))

    def test_http_5xx_is_retryable(self) -> None:
        assert is_http_retryable(HTTPStatusError("x", status_code=500))
        assert is_http_retryable(HTTPStatusError("x", status_code=503))

    def test_http_4xx_is_not_retryable(self) -> None:
        assert not is_http_retryable(HTTPStatusError("x", status_code=404))
        assert not is_http_retryable(HTTPStatusError("x", status_code=400))

    def test_http_501_is_not_retryable(self) -> None:
        assert not is_http_retryable(HTTPStatusError("x", status_code=501))

    def test_unrelated_errors_are_not_retryable(self) -> None:
        assert not is_http_retryable(ValueError("x"))
