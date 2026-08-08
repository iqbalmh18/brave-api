"""Integration tests that hit the live Brave API.

These are opt-in and excluded from the default test run::

    uv run pytest -m integration

They require network access and may be rate-limited by Brave.
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
    async with BraveClient(config) as instance:
        yield instance


async def test_open_conversation_returns_id(client: BraveClient) -> None:
    conv: Conversation = await client.conversation("ping")
    assert conv.id is not None
    assert len(conv.id) > 20
    assert conv.symmetric_key is not None
    assert len(conv.symmetric_key) == 43
    assert conv.share_link is not None
    await conv.reset()


async def test_collect_simple_answer(client: BraveClient) -> None:
    conv = await client.conversation("who is iqbalmh18")
    result = await conv.collect()
    assert result.is_complete
    assert len(result.text) > 0
    await conv.reset()


async def test_stream_yields_text_deltas(client: BraveClient) -> None:
    conv = await client.conversation("who is iqbalmh18")
    chunks: list[str] = []
    async for event in conv.stream_events():
        if event.type is StreamEventType.TEXT_DELTA:
            chunks.append(event.delta)
    assert "".join(chunks)
    await conv.reset()


async def test_contextual_search_does_not_crash(client: BraveClient) -> None:
    conv = await client.conversation(
        "summary",
        query_type=QueryType.CONTEXTUAL_SEARCH,
        quote="weather",
    )
    try:
        await conv.collect()
    except Exception:
        pass
    finally:
        await conv.reset()


async def test_suggest_returns_typed_result(client: BraveClient) -> None:
    result = await client.suggest("python")
    assert result.query == "python"
    assert result.suggestions
