"""Tests for the typed parsing boundary (:mod:`brave_api._internal.events`).

This module is the only place where arbitrary server JSON is consumed; these
tests pin down the shapes it extracts so vendor changes surface as failures
here rather than as silent regressions downstream.
"""

from __future__ import annotations

from typing import Any

from brave_api._internal.events import (
    extract_image_results,
    extract_infobox,
    extract_service_response,
    extract_video_results,
    extract_web_results,
    parse_event,
)
from brave_api.enums import StreamEventType
from brave_api.models import StreamEvent


def event(event_type: StreamEventType, **payload: Any) -> StreamEvent:
    return StreamEvent(type=event_type, raw_type=str(event_type), payload=payload)


class TestWebExtraction:
    def test_extracts_core_fields(self) -> None:
        web = extract_web_results(
            [
                {
                    "url": "https://example.com/1",
                    "title": "One",
                    "description": "Desc",
                    "meta_url": {"favicon": "https://example.com/f.ico"},
                }
            ]
        )
        assert len(web) == 1
        assert web[0].url == "https://example.com/1"
        assert web[0].title == "One"
        assert web[0].favicon == "https://example.com/f.ico"

    def test_full_title_fallback_and_thumbnail_dict(self) -> None:
        web = extract_web_results(
            [
                {
                    "url": "https://example.com/2",
                    "full_title": "Full",
                    "thumbnail": {
                        "src": "https://example.com/t.jpg",
                        "original": "https://example.com/o.jpg",
                    },
                }
            ]
        )
        assert web[0].title == "Full"
        assert web[0].thumbnail == "https://example.com/t.jpg"
        assert web[0].thumbnail_original == "https://example.com/o.jpg"

    def test_ignores_missing_or_invalid_urls(self) -> None:
        assert extract_web_results([{}, {"url": ""}, {"url": 42}]) == []

    def test_non_list_input_returns_empty(self) -> None:
        assert extract_web_results("nope") == []
        assert extract_web_results(None) == []


class TestImageExtraction:
    def test_prefers_image_url_and_properties(self) -> None:
        images = extract_image_results(
            [
                {
                    "image_url": "https://example.com/img.jpg",
                    "title": "A photo",
                    "properties": {"width": 800, "height": 600},
                }
            ]
        )
        assert images[0].url == "https://example.com/img.jpg"
        assert images[0].width == 800
        assert images[0].height == 600

    def test_accepts_thumbnail_url_variants(self) -> None:
        images = extract_image_results(
            [
                {
                    "url": "https://example.com/img2.jpg",
                    "thumbnail": {"resized": "https://example.com/t.jpg"},
                }
            ]
        )
        assert images[0].thumbnail == "https://example.com/t.jpg"

    def test_rejects_non_http_urls(self) -> None:
        assert extract_image_results([{"image_url": "/relative.jpg"}]) == []


class TestVideoExtraction:
    def test_extracts_video_fields(self) -> None:
        videos = extract_video_results(
            [
                {
                    "url": "https://youtube.com/watch?v=x",
                    "title": "Vid",
                    "duration": "5:30",
                    "author": "Channel",
                    "thumbnail": "https://example.com/v.jpg",
                }
            ]
        )
        assert videos[0].channel == "Channel"
        assert videos[0].duration == "5:30"


class TestInfoboxExtraction:
    def test_builds_infobox_with_attributes(self) -> None:
        box = extract_infobox(
            {
                "title": "Mount Bromo",
                "description": "Active volcano",
                "long_desc": "Long description",
                "attributes": [["height", "2329 m"]],
                "url": "https://en.wikipedia.org/wiki/Mount_Bromo",
                "image": {"src": "https://example.com/b.jpg"},
            }
        )
        assert box is not None
        assert box.title == "Mount Bromo"
        assert box.url == "https://en.wikipedia.org/wiki/Mount_Bromo"
        assert box.attributes["long_desc"] == "Long description"
        assert box.attributes["height"] == "2329 m"

    def test_returns_none_without_title(self) -> None:
        assert extract_infobox({"description": "no title"}) is None
        assert extract_infobox("nope") is None


class TestServiceResponseExtraction:
    def test_dispatch_by_service_type(self) -> None:
        service = {
            "type": "search",
            "results": [{"url": "https://example.com/w1", "title": "W"}],
            "images": [{"image_url": "https://example.com/i1.jpg"}],
            "videos": [{"url": "https://example.com/v1"}],
            "news": {"results": [{"url": "https://example.com/n1", "title": "N"}]},
        }
        extracted = extract_service_response(service)
        assert [item.url for item in extracted.web] == [
            "https://example.com/w1",
            "https://example.com/n1",
        ]
        assert extracted.images[0].url == "https://example.com/i1.jpg"
        assert extracted.videos[0].url == "https://example.com/v1"

    def test_infobox_only_when_requested(self) -> None:
        service = {"infobox": {"title": "X", "description": "y"}}
        assert extract_service_response(service).infobox is None
        assert extract_service_response(service, include_infobox=True).infobox is not None

    def test_infobox_on_service_response_itself(self) -> None:
        service = {"type": "local", "title": "Place", "description": "d"}
        box = extract_service_response(service, include_infobox=True).infobox
        assert box is not None
        assert box.title == "Place"

    def test_non_dict_service_returns_empty(self) -> None:
        assert extract_service_response(None).web == ()
        assert extract_service_response([]).web == ()


class TestParseEvent:
    def test_text_delta_is_extracted(self) -> None:
        parsed = parse_event(event(StreamEventType.TEXT_DELTA, delta="hello"))
        assert parsed.type is StreamEventType.TEXT_DELTA
        assert parsed.delta == "hello"

    def test_tool_use_payload_is_carried_when_actionable(self) -> None:
        parsed = parse_event(event(StreamEventType.TOOL_USE, id="t1", name="search"))
        assert parsed.tool_use is not None
        assert parsed.tool_use["id"] == "t1"

    def test_tool_use_without_id_is_not_actionable(self) -> None:
        parsed = parse_event(event(StreamEventType.TOOL_USE, name="search"))
        assert parsed.tool_use is None

    def test_followups_accept_str_and_dict_items(self) -> None:
        parsed = parse_event(event(StreamEventType.FOLLOWUPS, followups=["q1", {"query": "q2"}]))
        assert parsed.followups == ("q1", "q2")

    def test_rag_and_toc(self) -> None:
        parsed = parse_event(event(StreamEventType.RAG, content=[{"doc": 1}]))
        assert parsed.rag == ({"doc": 1},)
        parsed = parse_event(event(StreamEventType.TABLE_OF_CONTENT, items=[{"h": "x"}]))
        assert parsed.toc == ({"h": "x"},)

    def test_inline_annotations_are_carried(self) -> None:
        parsed = parse_event(event(StreamEventType.INLINE_ENTITY, name="X"))
        assert parsed.annotation == {"name": "X"}
        parsed = parse_event(event(StreamEventType.INLINE_CITATION, idx=1))
        assert parsed.annotation == {"idx": 1}
        parsed = parse_event(event(StreamEventType.AUGMENT_WITH_INLINE_CITATION, idx=2))
        assert parsed.annotation == {"idx": 2}

    def test_augment_with_tool_use_carries_citation(self) -> None:
        parsed = parse_event(
            event(
                StreamEventType.AUGMENT_WITH_TOOL_USE,
                service_response={
                    "type": "search",
                    "results": [{"url": "https://example.com/1"}],
                },
            )
        )
        assert parsed.citation is not None
        assert parsed.citation["service_response"]["type"] == "search"

    def test_usage_payload_is_carried(self) -> None:
        parsed = parse_event(event(StreamEventType.USAGE, total_tokens=42))
        assert parsed.usage == {"total_tokens": 42}

    def test_unhandled_events_pass_through_untyped(self) -> None:
        parsed = parse_event(event(StreamEventType.DEBUG_LABELS, labels=["a"]))
        assert parsed.type is StreamEventType.DEBUG_LABELS
        assert parsed.delta == ""
        assert parsed.tool_use is None
        assert parsed.extracted.web == ()
        # an unhandled event must not expose its payload to the application layer
        assert not hasattr(parsed, "raw")

    def test_augment_with_web_uses_service_response(self) -> None:
        parsed = parse_event(
            event(
                StreamEventType.AUGMENT_WITH_WEB,
                service_response={
                    "type": "search",
                    "results": [{"url": "https://example.com/1"}],
                },
            )
        )
        assert [item.url for item in parsed.extracted.web] == ["https://example.com/1"]

    def test_augment_with_images_falls_back_to_results(self) -> None:
        parsed = parse_event(
            event(
                StreamEventType.AUGMENT_WITH_IMAGES,
                results=[{"image_url": "https://example.com/i.jpg"}],
            )
        )
        assert [item.url for item in parsed.extracted.images] == ["https://example.com/i.jpg"]

    def test_augment_with_tool_use_includes_infobox(self) -> None:
        parsed = parse_event(
            event(
                StreamEventType.AUGMENT_WITH_TOOL_USE,
                service_response={
                    "type": "search",
                    "infobox": {"title": "Entity", "description": "d"},
                    "results": [{"url": "https://example.com/1"}],
                },
            )
        )
        assert parsed.extracted.infobox is not None
        assert parsed.extracted.infobox.title == "Entity"
