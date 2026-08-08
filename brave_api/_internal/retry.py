"""Retry policies for HTTP operations.

:func:`retry_async` wraps a single coroutine with a bounded, jittered
exponential-backoff retry loop. :func:`is_http_retryable` classifies
:mod:`brave_api.exceptions` into retryable and non-retryable failures.

The loop catches ``Exception`` only (never ``BaseException``), so
``asyncio.CancelledError``, ``KeyboardInterrupt`` and ``SystemExit`` always
propagate immediately.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")

_JITTER_LOW = 0.5
_JITTER_HIGH = 1.5

_NON_RETRYABLE_5XX = frozenset({501, 505})


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    operation_name: str,
    max_attempts: int,
    backoff_seconds: float,
    jitter: bool,
    is_retryable: Callable[[Exception], bool],
) -> T:
    """Run *operation* up to *max_attempts* times with exponential backoff.

    The first attempt is attempt 1; *max_attempts* is the total number of
    attempts including the first. The sleep before retry *n* is
    ``backoff_seconds * 2 ** (n - 1)`` seconds, optionally multiplied by a
    random 0.5x-1.5x jitter factor. ``ValueError`` is raised for
    ``max_attempts < 1``.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    last_exception: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            last_exception = exc
            if not is_retryable(exc) or attempt == max_attempts:
                raise
            factor = random.uniform(_JITTER_LOW, _JITTER_HIGH) if jitter else 1.0
            await asyncio.sleep(backoff_seconds * (2 ** (attempt - 1)) * factor)

    raise RuntimeError(f"retry_async exhausted attempts for {operation_name}") from last_exception


def is_http_retryable(exc: Exception) -> bool:
    """Return True when *exc* represents a transient, retryable failure."""
    from ..exceptions import HTTPStatusError, TransportError

    if isinstance(exc, TransportError):
        return True
    if isinstance(exc, HTTPStatusError):
        if exc.status_code == 429:
            return True
        return 500 <= exc.status_code <= 599 and exc.status_code not in _NON_RETRYABLE_5XX
    return False


__all__ = ["is_http_retryable", "retry_async"]
