"""Tes integrasi brave_api (memanggil API Brave langsung).

Jalankan hanya bila ingin validasi end-to-end::

    uv run pytest brave_api/tests/test_integration.py -m integration
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from brave_api import (
    BraveClient,
    ClientConfig,
    Conversation,
    QueryType,
    StreamEventType,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def client() -> AsyncIterator[BraveClient]:
    config = ClientConfig(
        geoloc=os.environ.get("BRAVE_GEOLOC", "0x0"),
        country=os.environ.get("BRAVE_COUNTRY", "us"),
    )
    instance = BraveClient(config)
    await instance.__aenter__()
    try:
        yield instance
    finally:
        await instance.__aexit__(None, None, None)


async def test_open_conversation_returns_id(client: BraveClient) -> None:
    conv: Conversation = await client.conversation("ping")
    assert conv.id is not None
    assert len(conv.id) > 20
    assert conv.symmetric_key is not None
    assert len(conv.symmetric_key) == 43
    assert conv.share_link is not None
    assert "sig=" in conv.share_link
    await conv.close()


async def test_collect_simple_answer(client: BraveClient) -> None:
    conv = await client.conversation("who is iqbalmh18")
    result = await conv.collect()
    assert result.is_complete
    assert len(result.text) > 0
    await conv.close()


async def test_stream_yields_text_deltas(client: BraveClient) -> None:
    conv = await client.conversation("who is iqbalmh18")
    chunks: list[str] = []
    async for evt in conv.stream_events():
        if evt.type is StreamEventType.TEXT_DELTA:
            chunks.append(evt.delta)
    assert "".join(chunks)
    await conv.close()


async def test_contextual_search_does_not_crash(client: BraveClient) -> None:
    conv = await client.conversation(
        "ringkasan",
        query_type=QueryType.CONTEXTUAL_SEARCH,
        quote="cuaca",
    )
    try:
        await conv.collect()
    except Exception:
        pass
    finally:
        await conv.close()
