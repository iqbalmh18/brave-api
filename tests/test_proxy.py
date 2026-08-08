"""Tests for the ProxyPool rotation and quarantine behavior."""

from __future__ import annotations

import asyncio

from brave_api._internal.proxy import ProxyPool


class TestProxyPool:
    async def test_round_robin_rotation(self) -> None:
        pool = ProxyPool(["p1", "p2"])
        first = await pool.candidates()
        second = await pool.candidates()
        assert first == ["p1", "p2", None]
        assert second == ["p2", "p1", None]

    async def test_empty_pool_yields_direct_connection(self) -> None:
        pool = ProxyPool([])
        assert await pool.candidates() == [None]

    async def test_disabled_proxy_is_never_offered_again(self) -> None:
        pool = ProxyPool(["p1", "p2"])
        await pool.disable("p1")
        candidates = await pool.candidates()
        assert "p1" not in candidates
        assert candidates == ["p2", None]
        assert pool.disabled_count == 1

    async def test_all_disabled_falls_back_to_direct(self) -> None:
        pool = ProxyPool(["p1"])
        await pool.disable("p1")
        assert await pool.candidates() == [None]

    async def test_rotation_wraps_around(self) -> None:
        pool = ProxyPool(["a", "b", "c"])
        seen = [await pool.candidates() for _ in range(3)]
        assert seen[0] == ["a", "b", "c", None]
        assert seen[1] == ["b", "c", "a", None]
        assert seen[2] == ["c", "a", "b", None]
        assert await pool.candidates() == ["a", "b", "c", None]

    async def test_concurrent_rotation_is_safe(self) -> None:
        pool = ProxyPool(["a", "b", "c", "d"])

        async def grab() -> list[str | None]:
            return await pool.candidates()

        results = await asyncio.gather(*[grab() for _ in range(100)])
        heads = [result[0] for result in results]
        assert set(heads) == {"a", "b", "c", "d"}
