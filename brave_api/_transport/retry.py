from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from .._internal.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_RETRY_JITTER_MAX,
    DEFAULT_RETRY_JITTER_MIN,
    RETRYABLE_CLIENT_STATUS_MAX,
)
from ..exceptions import HTTPStatusError, TransportError

T = TypeVar("T")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    operation_name: str,
    max_attempts: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    jitter_min: float = DEFAULT_RETRY_JITTER_MIN,
    jitter_max: float = DEFAULT_RETRY_JITTER_MAX,
    is_retryable: Callable[[BaseException], bool],
) -> T:
    if max_attempts <= 0:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    last_exception: BaseException | None = None
    for attempt_index in range(1, max_attempts + 1):
        try:
            return await operation()
        except BaseException as exc:
            last_exception = exc
            if not is_retryable(exc):
                raise
            if attempt_index == max_attempts:
                break

            jitter = random.uniform(jitter_min, jitter_max)
            await asyncio.sleep(backoff_seconds * attempt_index * jitter)

    assert last_exception is not None
    raise last_exception


def is_http_retryable(exc: BaseException) -> bool:
    if isinstance(exc, TransportError):
        return True

    if isinstance(exc, HTTPStatusError):
        if exc.status_code is None:
            return False
        if exc.status_code == 429:
            return True

        return exc.status_code > RETRYABLE_CLIENT_STATUS_MAX
    return False


__all__ = ["is_http_retryable", "retry_async"]
