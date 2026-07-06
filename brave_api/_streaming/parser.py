from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, TypeGuard

from .._internal.constants import STREAM_DONE_MARKER
from .._internal.models import StreamEvent
from .._internal.types import StreamEventType, SupportsRawStream

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger("brave_api.stream.parser")


def parse_line(raw_line: str) -> StreamEvent | None:
    if not raw_line:
        return None
    
    line = raw_line.strip()
    if not line or line == STREAM_DONE_MARKER:
        return None
    
    if line.startswith("data:"):
        line = line[5:].lstrip()
        if not line:
            return None

    try:
        payload: dict[str, Any] = json.loads(line)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse stream line: %s", e)
        return None
    if not isinstance(payload, dict):
        return None

    raw_type = str(payload.get("type", ""))
    if raw_type:
        try:
            event_type = StreamEventType(raw_type)
        except ValueError:
            return None
    else:
        event_type = StreamEventType.ERROR

    return StreamEvent(type=event_type, raw_type=raw_type, payload=payload)


def is_terminal_event(event: StreamEvent) -> TypeGuard[bool]:
    return event.type in (
        StreamEventType.TEXT_STOP,
        StreamEventType.ERROR,
        StreamEventType.CHALLENGE,
    )


async def iter_events(
    source: SupportsRawStream,
) -> AsyncGenerator[StreamEvent, None]:
    async for chunk in source:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        event = parse_line(chunk)
        if event is not None:
            yield event


__all__ = ["is_terminal_event", "iter_events", "parse_line"]
