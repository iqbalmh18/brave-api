"""Round-robin proxy pool with failure quarantine."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence


class ProxyPool:
    """Rotates through a fixed proxy list in round-robin order.

    A proxy that fails is quarantined for the lifetime of the pool. When no
    active proxy remains, callers receive ``[None]`` to signal a direct
    connection. Thread-safe across concurrent tasks via an internal lock.
    """

    def __init__(self, proxies: Sequence[str]) -> None:
        self._proxies: list[str] = list(proxies)
        self._disabled: set[str] = set()
        self._next_index = 0
        self._lock = asyncio.Lock()

    async def candidates(self) -> list[str | None]:
        """Return the next rotation order ending with ``None`` (direct)."""
        async with self._lock:
            active = [proxy for proxy in self._proxies if proxy not in self._disabled]
            if not active:
                return [None]
            start = self._next_index % len(active)
            self._next_index = (start + 1) % len(active)
            rotation = active[start:] + active[:start]
            return [*rotation, None]

    async def disable(self, proxy: str) -> None:
        """Quarantine *proxy* so it is never offered again."""
        async with self._lock:
            self._disabled.add(proxy)

    @property
    def disabled_count(self) -> int:
        return len(self._disabled)


__all__ = ["ProxyPool"]
