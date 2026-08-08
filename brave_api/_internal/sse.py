"""Streaming event parsing for the Brave AI SSE endpoint."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, cast

from ..enums import StreamEventType
from ..models import StreamEvent
from .constants import STREAM_DONE_MARKER

logger = logging.getLogger("brave_api.sse")


def parse_line(raw_line: str) -> StreamEvent | None:
    """Parse a single streamed line into a :class:`StreamEvent`.

    Returns ``None`` for blank lines, the ``[DONE]`` marker, malformed JSON,
    non-object payloads and unknown event types. Unknown event types are
    intentionally skipped so the client tolerates new server event types.
    """
    line = raw_line.strip()
    if not line or line == STREAM_DONE_MARKER:
        return None
    if line.startswith("data:"):
        line = line[5:].lstrip()
        if not line:
            return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("Failed to parse stream line: %s", raw_line[:200])
        return None
    if not isinstance(payload, dict):
        return None
    typed_payload = cast(dict[str, Any], payload)

    raw_type = str(typed_payload.get("type", ""))
    if raw_type:
        try:
            event_type = StreamEventType(raw_type)
        except ValueError:
            return None
    else:
        event_type = StreamEventType.ERROR

    return StreamEvent(type=event_type, raw_type=raw_type, payload=typed_payload)


async def iter_events(
    source: AsyncIterator[str | bytes],
) -> AsyncGenerator[StreamEvent, None]:
    """Decode raw stream chunks and yield parsed events, skipping blanks."""
    async for chunk in source:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        event = parse_line(chunk)
        if event is not None:
            yield event


__all__ = ["iter_events", "parse_line"]
