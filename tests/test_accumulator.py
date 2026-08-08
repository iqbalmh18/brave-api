"""Tests for the StreamAccumulator — the core of the streaming pipeline."""

from __future__ import annotations

from typing import Any

from brave_api._internal.accumulator import StreamAccumulator
from brave_api.enums import StreamEventType, StreamState
from brave_api.models import StreamEvent, StreamResult


def event(event_type: StreamEventType, **payload: Any) -> StreamEvent:
    return StreamEvent(type=event_type, raw_type=str(event_type), payload=payload)


def feed_all(accumulator: StreamAccumulator, *events: StreamEvent) -> StreamResult:
    for item in events:
        accumulator.feed(item)
    return accumulator.finalize()


class TestTextAccumulation:
    def test_text_deltas_are_joined(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.TEXT_START, text=""),
            event(StreamEventType.TEXT_DELTA, delta="Hello "),
            event(StreamEventType.TEXT_DELTA, delta="world"),
            event(StreamEventType.TEXT_STOP),
        )
        assert result.text == "Hello world"
        assert result.is_complete

    def test_thinking_is_accumulated_separately(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.THINKING_DELTA, delta="step 1"),
            event(StreamEventType.THINKING_STOP),
            event(StreamEventType.TEXT_DELTA, delta="answer"),
        )
        assert result.thinking == "step 1"
        assert result.text == "answer"

    def test_raw_events_are_recorded(self) -> None:
        accumulator = StreamAccumulator()
        feed_all(accumulator, event(StreamEventType.TEXT_DELTA, delta="x"))
        assert len(accumulator.finalize().raw_events) == 1

    def test_raw_events_can_be_disabled(self) -> None:
        accumulator = StreamAccumulator(store_raw_events=False)
        result = feed_all(accumulator, event(StreamEventType.TEXT_DELTA, delta="x"))
        assert result.raw_events == []


class TestToolEvents:
    def test_tool_use_records_id(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.TOOL_USE, id="t1", name="search", signed_params={}),
        )
        assert result.tool_uses == [{"id": "t1", "name": "search", "signed_params": {}}]
        assert result.has_tool_calls

    def test_tool_use_without_id_is_ignored(self) -> None:
        result = feed_all(StreamAccumulator(), event(StreamEventType.TOOL_USE, name="search"))
        assert result.tool_uses == []

    def test_augment_with_tool_use_extracts_web_results(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(
                StreamEventType.AUGMENT_WITH_TOOL_USE,
                service_response={
                    "type": "search",
                    "results": [
                        {
                            "url": "https://example.com/1",
                            "title": "One",
                            "description": "First result",
                            "meta_url": {"favicon": "https://example.com/f.ico"},
                        }
                    ],
                },
            ),
        )
        assert len(result.web_results) == 1
        web = result.web_results[0]
        assert web.url == "https://example.com/1"
        assert web.title == "One"
        assert web.favicon == "https://example.com/f.ico"
        assert result.urls == ["https://example.com/1"]


class TestRichResults:
    def test_images_are_extracted(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(
                StreamEventType.AUGMENT_WITH_IMAGES,
                service_response={
                    "type": "images",
                    "results": [
                        {
                            "image_url": "https://example.com/img.jpg",
                            "title": "A photo",
                            "properties": {"width": 800, "height": 600},
                        }
                    ],
                },
            ),
        )
        assert len(result.images) == 1
        image = result.images[0]
        assert image.url == "https://example.com/img.jpg"
        assert image.width == 800
        assert image.height == 600
        assert result.has_images

    def test_videos_are_extracted(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(
                StreamEventType.AUGMENT_WITH_VIDEOS,
                results=[
                    {
                        "url": "https://youtube.com/watch?v=abc",
                        "title": "A video",
                        "duration": "5:30",
                        "author": "Some Channel",
                    }
                ],
            ),
        )
        assert len(result.videos) == 1
        video = result.videos[0]
        assert video.url == "https://youtube.com/watch?v=abc"
        assert video.channel == "Some Channel"

    def test_infobox_is_extracted_from_dedicated_event(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(
                StreamEventType.AUGMENT_WITH_INFOBOX,
                infobox={"title": "Mount Bromo", "description": "Active volcano"},
            ),
        )
        assert result.infobox is not None
        assert result.infobox.title == "Mount Bromo"
        assert result.has_infobox

    def test_followups_are_extracted(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.FOLLOWUPS, followups=["q1", "q2"]),
        )
        assert result.followups == ["q1", "q2"]

    def test_rag_and_toc_and_usage(self) -> None:
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.RAG, content=[{"doc": 1}]),
            event(StreamEventType.TABLE_OF_CONTENT, items=[{"heading": "Intro"}]),
            event(StreamEventType.USAGE, total_tokens=42),
        )
        assert result.rag_content == [{"doc": 1}]
        assert result.table_of_contents == [{"heading": "Intro"}]
        assert result.usage == {"total_tokens": 42}


class TestDeduplication:
    def test_urls_are_unique_across_event_types(self) -> None:
        payload = {
            "type": "search",
            "results": [{"url": "https://example.com/1"}],
        }
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.AUGMENT_WITH_WEB, service_response=payload),
            event(StreamEventType.AUGMENT_WITH_NEWS, service_response=payload),
        )
        assert result.urls == ["https://example.com/1"]

    def test_duplicate_images_are_skipped(self) -> None:
        payload = {
            "type": "images",
            "results": [
                {"image_url": "https://example.com/img.jpg"},
                {"image_url": "https://example.com/img.jpg"},
            ],
        }
        result = feed_all(
            StreamAccumulator(),
            event(StreamEventType.AUGMENT_WITH_IMAGES, service_response=payload),
        )
        assert len(result.images) == 1


class TestFailureState:
    def test_mark_failed_prevents_complete(self) -> None:
        accumulator = StreamAccumulator()
        accumulator.feed(event(StreamEventType.TEXT_DELTA, delta="partial"))
        accumulator.mark_failed()
        result = accumulator.finalize()
        assert result.state is StreamState.FAILED
        assert not result.is_complete

    def test_initial_state_is_inactive(self) -> None:
        assert StreamAccumulator().state is StreamState.INACTIVE

    def test_feed_sets_streaming_state(self) -> None:
        accumulator = StreamAccumulator()
        accumulator.feed(event(StreamEventType.TEXT_DELTA, delta="x"))
        assert accumulator.state is StreamState.STREAMING
