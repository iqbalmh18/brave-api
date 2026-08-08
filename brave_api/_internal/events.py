"""Typed parsing boundary between raw vendor events and the accumulator.

This is the *single* integration boundary where untyped server JSON is
consumed. Everything below it deals in ``Any``; everything above it deals in
strongly-typed :class:`ParsedEvent` values built from :class:`WebResult`,
:class:`ImageResult`, :class:`VideoResult` and :class:`Infobox` models.

The pyright unknown-type rules are intentionally disabled *only here*: chasing
exact types through live vendor payload shapes would add noise without
catching real bugs. Every extraction is still guarded with ``isinstance``
checks, and no ``Unknown`` ever leaks past this module's return types.

:class:`ParsedEvent` deliberately exposes no raw payload access. The only
pass-through copies it carries (``tool_use``, ``annotation``, ``citation``,
``usage``) are explicit, typed fields that exist to populate the corresponding
observability fields of :class:`brave_api.models.StreamResult` — so the
application layer cannot reach back into vendor payloads for business logic.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..enums import StreamEventType
from ..models import ImageResult, Infobox, StreamEvent, VideoResult, WebResult

logger = logging.getLogger("brave_api.events")

_WEB_SERVICE_TYPES = frozenset({"search", "news", "discussions", "local", "shopping"})

_ENRICHMENT_TYPES = frozenset(
    {
        StreamEventType.AUGMENT_WITH_IMAGES,
        StreamEventType.AUGMENT_WITH_VIDEOS,
        StreamEventType.AUGMENT_WITH_WEB_SERP,
        StreamEventType.AUGMENT_WITH_WEB,
        StreamEventType.AUGMENT_WITH_NEWS,
        StreamEventType.AUGMENT_WITH_DISCUSSIONS,
        StreamEventType.AUGMENT_WITH_SHOPPING,
        StreamEventType.AUGMENT_WITH_LOCAL,
    }
)

_INFOBOX_SKIP_KEYS = frozenset(
    {
        "title",
        "full_title",
        "name",
        "label",
        "subtitle",
        "description",
        "subtype",
        "type",
        "image",
        "thumbnail",
        "image_url",
        "images",
        "url",
        "website_url",
        "website",
        "profiles",
        "providers",
        "infobox",
        "is_source_local",
        "is_source_both",
        "fetched_content_timestamp",
        "page_age",
        "page_fetched",
        "family_friendly",
        "language",
        "position",
        "found_in_urls",
        "qanda",
        "actions",
        "icons",
        "attributes_shown",
        "distance",
        "zoom_level",
        "location",
        "coordinates",
        "category",
        "is_location",
    }
)


@dataclass(frozen=True)
class Extracted:
    """Typed results lifted out of an arbitrary ``service_response`` payload."""

    web: tuple[WebResult, ...] = ()
    images: tuple[ImageResult, ...] = ()
    videos: tuple[VideoResult, ...] = ()
    infobox: Infobox | None = None


@dataclass(frozen=True)
class ParsedEvent:
    """A raw :class:`StreamEvent` reduced to its typed, usable fields.

    No raw payload is exposed here. The ``tool_use``, ``annotation``,
    ``citation`` and ``usage`` fields are explicit pass-through copies that map
    one-to-one onto the observability fields of :class:`StreamResult`.
    """

    type: StreamEventType
    delta: str = ""
    tool_use: dict[str, Any] | None = None
    annotation: dict[str, Any] | None = None
    citation: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    followups: tuple[str, ...] = ()
    rag: tuple[dict[str, Any], ...] = ()
    toc: tuple[dict[str, Any], ...] = ()
    extracted: Extracted = Extracted()


def extract_web_results(results: Any) -> list[WebResult]:
    """Build :class:`WebResult` objects from an arbitrary results list."""
    web: list[WebResult] = []
    if not isinstance(results, list):
        return web

    for result in results:
        if not isinstance(result, dict):
            continue
        url = result.get("url")
        if not isinstance(url, str) or not url:
            continue

        favicon: str | None = None
        meta_url = result.get("meta_url")
        if isinstance(meta_url, dict):
            favicon = meta_url.get("favicon")
        if not favicon:
            favicon = result.get("favicon")

        thumbnail_url: str | None = None
        thumbnail_original: str | None = None
        thumbnail = result.get("thumbnail")
        if isinstance(thumbnail, dict):
            thumbnail_url = thumbnail.get("src") or thumbnail.get("resized")
            thumbnail_original = thumbnail.get("original")
        elif isinstance(thumbnail, str) and thumbnail.startswith(("http://", "https://")):
            thumbnail_url = thumbnail

        try:
            web.append(
                WebResult(
                    url=url,
                    title=result.get("title") or result.get("full_title"),
                    description=result.get("description"),
                    favicon=favicon,
                    thumbnail=thumbnail_url,
                    thumbnail_original=thumbnail_original,
                )
            )
        except Exception as exc:
            logger.debug("Failed to create WebResult for %s: %s", url, exc)
    return web


def extract_image_results(results: Any) -> list[ImageResult]:
    """Build :class:`ImageResult` objects from an arbitrary results list."""
    images: list[ImageResult] = []
    if not isinstance(results, list):
        return images

    for result in results:
        if not isinstance(result, dict):
            continue
        properties = result.get("properties")
        url = (
            result.get("image_url")
            or (properties.get("url") if isinstance(properties, dict) else None)
            or result.get("url")
            or result.get("src")
            or ""
        )
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue

        thumbnail: str | None = None
        raw_thumbnail = result.get("thumbnail") or result.get("thumbnail_url")
        if isinstance(raw_thumbnail, dict):
            thumbnail = raw_thumbnail.get("src") or raw_thumbnail.get("resized")
        elif isinstance(raw_thumbnail, str) and raw_thumbnail.startswith(("http://", "https://")):
            thumbnail = raw_thumbnail

        try:
            images.append(
                ImageResult(
                    url=url,
                    title=result.get("title"),
                    thumbnail=thumbnail,
                    source=result.get("source") or result.get("domain"),
                    width=(properties.get("width") if isinstance(properties, dict) else None)
                    or result.get("width"),
                    height=(properties.get("height") if isinstance(properties, dict) else None)
                    or result.get("height"),
                )
            )
        except Exception as exc:
            logger.debug("Failed to create ImageResult for %s: %s", url, exc)
    return images


def extract_video_results(results: Any) -> list[VideoResult]:
    """Build :class:`VideoResult` objects from an arbitrary results list."""
    videos: list[VideoResult] = []
    if not isinstance(results, list):
        return videos

    for result in results:
        if not isinstance(result, dict):
            continue
        url = result.get("url", "")
        if not url:
            continue

        thumbnail: str | None = None
        raw_thumbnail = result.get("thumbnail")
        if isinstance(raw_thumbnail, dict):
            thumbnail = raw_thumbnail.get("src") or raw_thumbnail.get("resized")
        elif isinstance(raw_thumbnail, str) and raw_thumbnail.startswith(("http://", "https://")):
            thumbnail = raw_thumbnail

        try:
            videos.append(
                VideoResult(
                    url=url,
                    title=result.get("title"),
                    thumbnail=thumbnail,
                    duration=result.get("duration"),
                    channel=result.get("channel") or result.get("author"),
                )
            )
        except Exception as exc:
            logger.debug("Failed to create VideoResult for %s: %s", url, exc)
    return videos


def extract_infobox(data: Any) -> Infobox | None:
    """Build a :class:`Infobox` from an arbitrary payload, if recognizable."""
    if not isinstance(data, dict):
        return None
    title = data.get("title") or data.get("name") or data.get("full_title") or data.get("label")
    if not title:
        return None
    subtitle = (
        data.get("subtitle") or data.get("description") or data.get("subtype") or data.get("type")
    )

    image_url: str | None = None
    raw_image = data.get("image") or data.get("thumbnail") or data.get("image_url")
    if isinstance(raw_image, dict):
        image_url = (
            raw_image.get("src")
            or raw_image.get("original")
            or raw_image.get("resized")
            or raw_image.get("url")
        )
    elif isinstance(raw_image, str) and raw_image.startswith(("http://", "https://")):
        image_url = raw_image
    if not image_url:
        images = data.get("images")
        if isinstance(images, list) and images and isinstance(images[0], dict):
            image_url = (
                images[0].get("original") or images[0].get("src") or images[0].get("resized")
            )

    url: str | None = None
    raw_url = data.get("url") or data.get("website_url") or data.get("website")
    if isinstance(raw_url, str) and raw_url.startswith(("http://", "https://")):
        url = raw_url
    if not url:
        profiles = data.get("profiles") or data.get("providers")
        if isinstance(profiles, list):
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue
                profile_url = profile.get("url", "")
                if isinstance(profile_url, str):
                    if "wikipedia" in profile_url:
                        url = profile_url
                        break
                    if url is None and profile_url:
                        url = profile_url

    attributes = _build_infobox_attributes(data)
    try:
        return Infobox(
            title=str(title),
            subtitle=str(subtitle) if subtitle else None,
            image_url=image_url,
            url=url,
            attributes=attributes,
        )
    except Exception as exc:
        logger.debug("Failed to create Infobox for %s: %s", title, exc)
        return None


def _build_infobox_attributes(data: dict[str, Any]) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    long_desc = data.get("long_desc")
    if long_desc:
        attributes["long_desc"] = long_desc

    raw_attributes = data.get("attributes")
    if isinstance(raw_attributes, list):
        for attr in raw_attributes:
            if isinstance(attr, list) and len(attr) == 2:
                attributes[str(attr[0])] = attr[1]

    for key, value in data.items():
        if key not in _INFOBOX_SKIP_KEYS and key not in attributes and value is not None:
            attributes[key] = value
    return attributes


def extract_service_response(service: Any, *, include_infobox: bool = False) -> Extracted:
    """Lift typed results out of a ``service_response`` of any service type."""
    if not isinstance(service, dict):
        return Extracted()

    web: list[WebResult] = []
    images: list[ImageResult] = []
    videos: list[VideoResult] = []

    service_type = service.get("type")
    results = service.get("results")
    if isinstance(results, list):
        if service_type == "images":
            images.extend(extract_image_results(results))
        elif service_type == "videos":
            videos.extend(extract_video_results(results))
        elif service_type in _WEB_SERVICE_TYPES:
            web.extend(extract_web_results(results))

    raw_web = service.get("web")
    if isinstance(raw_web, dict):
        web.extend(extract_web_results(raw_web.get("results", [])))

    raw_images = service.get("images")
    if isinstance(raw_images, dict):
        images.extend(extract_image_results(raw_images.get("results", [])))
    elif isinstance(raw_images, list):
        images.extend(extract_image_results(raw_images))

    raw_videos = service.get("videos")
    if isinstance(raw_videos, dict):
        videos.extend(extract_video_results(raw_videos.get("results", [])))
    elif isinstance(raw_videos, list):
        videos.extend(extract_video_results(raw_videos))

    raw_news = service.get("news")
    if isinstance(raw_news, dict):
        web.extend(extract_web_results(raw_news.get("results", [])))

    raw_discussions = service.get("discussions")
    if isinstance(raw_discussions, dict):
        web.extend(extract_web_results(raw_discussions.get("results", [])))

    return Extracted(
        web=tuple(web),
        images=tuple(images),
        videos=tuple(videos),
        infobox=extract_infobox_from_service_response(service) if include_infobox else None,
    )


def extract_infobox_from_service_response(service: Any) -> Infobox | None:
    """The infobox may sit under ``infobox`` or on the service response itself."""
    if not isinstance(service, dict):
        return None
    infobox_data = service.get("infobox")
    if not infobox_data and all(key in service for key in ("title", "description", "type")):
        infobox_data = service
    return extract_infobox(infobox_data)


def parse_event(event: StreamEvent) -> ParsedEvent:
    """Reduce a raw :class:`StreamEvent` to its typed, usable fields."""
    event_type = event.type
    payload = event.payload

    if event_type in {StreamEventType.TEXT_DELTA, StreamEventType.THINKING_DELTA}:
        return ParsedEvent(type=event_type, delta=str(payload.get("delta") or ""))
    if event_type is StreamEventType.TOOL_USE:
        tool_id = payload.get("id")
        return ParsedEvent(
            type=event_type,
            tool_use=payload if isinstance(tool_id, str) else None,
        )
    if event_type is StreamEventType.AUGMENT_WITH_TOOL_USE:
        return ParsedEvent(
            type=event_type,
            citation=payload,
            extracted=extract_service_response(
                payload.get("service_response"), include_infobox=True
            ),
        )
    if event_type is StreamEventType.INITIAL_RESPONSE:
        return ParsedEvent(
            type=event_type,
            extracted=extract_service_response(payload.get("service_response")),
        )
    if event_type is StreamEventType.AUGMENT_WITH_INFOBOX:
        return ParsedEvent(type=event_type, extracted=_extracted_from_infobox_payload(payload))
    if event_type is StreamEventType.FOLLOWUPS:
        return ParsedEvent(type=event_type, followups=_extract_followups(payload))
    if event_type is StreamEventType.INLINE_ENTITY:
        return ParsedEvent(type=event_type, annotation=payload)
    if event_type in {
        StreamEventType.INLINE_CITATION,
        StreamEventType.AUGMENT_WITH_INLINE_CITATION,
    }:
        return ParsedEvent(type=event_type, annotation=payload)
    if event_type in _ENRICHMENT_TYPES:
        return ParsedEvent(
            type=event_type,
            extracted=_extracted_from_enrichment_payload(event_type, payload),
        )
    if event_type is StreamEventType.RAG:
        return ParsedEvent(type=event_type, rag=_extract_rag(payload))
    if event_type is StreamEventType.TABLE_OF_CONTENT:
        return ParsedEvent(type=event_type, toc=_extract_toc(payload))
    if event_type is StreamEventType.USAGE:
        return ParsedEvent(type=event_type, usage=payload)
    return ParsedEvent(type=event_type)


def _extract_followups(payload: dict[str, Any]) -> tuple[str, ...]:
    candidates = payload.get("followups") or payload.get("queries") or []
    followups: list[str] = []
    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, str) and item.strip():
                followups.append(item.strip())
            elif isinstance(item, dict):
                question = item.get("query") or item.get("text") or item.get("title")
                if isinstance(question, str) and question.strip():
                    followups.append(question.strip())
    return tuple(followups)


def _extract_rag(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    content = payload.get("content") or payload.get("rag") or payload.get("results")
    return tuple(content) if isinstance(content, list) else ()


def _extract_toc(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    items_raw = payload.get("items") or payload.get("toc") or payload.get("headings")
    return tuple(items_raw) if isinstance(items_raw, list) else ()


def _extracted_from_infobox_payload(payload: dict[str, Any]) -> Extracted:
    data = payload.get("infobox")
    if not isinstance(data, dict):
        data = payload
    return Extracted(infobox=extract_infobox(data))


def _extracted_from_enrichment_payload(
    event_type: StreamEventType, payload: dict[str, Any]
) -> Extracted:
    service = payload.get("service_response")
    if service is not None:
        return extract_service_response(service)

    results = payload.get("results", [])
    if event_type is StreamEventType.AUGMENT_WITH_IMAGES:
        return Extracted(images=tuple(extract_image_results(results)))
    if event_type is StreamEventType.AUGMENT_WITH_VIDEOS:
        return Extracted(videos=tuple(extract_video_results(results)))
    return Extracted(web=tuple(extract_web_results(results)))


__all__ = [
    "Extracted",
    "ParsedEvent",
    "extract_infobox",
    "extract_service_response",
    "parse_event",
]
