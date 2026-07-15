from __future__ import annotations

import logging
from typing import Any

from .._internal.models import (
    ImageResult,
    Infobox,
    StreamEvent,
    StreamResult,
    VideoResult,
    WebResult,
)
from .._internal.types import StreamEventType, StreamState

logger = logging.getLogger("brave_api.result")


class StreamAccumulator:
    def __init__(self, store_raw_events: bool = True) -> None:
        self._text_parts: list[str] = []
        self._thinking_parts: list[str] = []
        self._tool_uses: list[dict[str, Any]] = []
        self._citations: list[dict[str, Any]] = []
        self._inline_entities: list[dict[str, Any]] = []
        self._inline_citations: list[dict[str, Any]] = []
        self._rag_content: list[dict[str, Any]] = []
        self._table_of_contents: list[dict[str, Any]] = []
        self._usage: dict[str, Any] = {}
        self._raw_events: list[StreamEvent] = []
        self._store_raw_events = store_raw_events
        self._urls: list[str] = []
        self._images: list[ImageResult] = []
        self._videos: list[VideoResult] = []
        self._web_results: list[WebResult] = []
        self._infobox: Infobox | None = None
        self._followups: list[str] = []
        self._seen_urls: set[str] = set()
        self._seen_image_urls: set[str] = set()
        self._state: StreamState = StreamState.INACTIVE
        self._failed: bool = False

    @property
    def state(self) -> StreamState:
        return self._state

    def feed(self, event: StreamEvent) -> None:
        if self._store_raw_events:
            self._raw_events.append(event)
        self._state = StreamState.STREAMING
        event_type = event.type

        if event_type is StreamEventType.TEXT_DELTA:
            self._text_parts.append(event.delta)
        elif event_type is StreamEventType.THINKING_DELTA:
            self._thinking_parts.append(event.delta)
        elif event_type is StreamEventType.TOOL_USE:
            if event.payload.get("id"):
                self._tool_uses.append(event.payload)
        elif event_type is StreamEventType.AUGMENT_WITH_TOOL_USE:
            self._citations.append(event.payload)
            sr = event.payload.get("service_response")
            self._extract_from_service_response(sr)
            # Infobox bisa ada di top-level SR (bukan nested service_response)
            if isinstance(sr, dict) and self._infobox is None:
                self._extract_infobox_from_service_response(sr)
        elif event_type is StreamEventType.INLINE_ENTITY:
            self._inline_entities.append(event.payload)
        elif event_type is StreamEventType.INITIAL_RESPONSE:
            self._extract_from_service_response(event.payload.get("service_response"))
        elif event_type is StreamEventType.AUGMENT_WITH_INFOBOX:
            self._extract_infobox(event.payload)
        elif event_type is StreamEventType.FOLLOWUPS:
            self._extract_followups(event.payload)
        elif event_type is StreamEventType.AUGMENT_WITH_IMAGES:
            service = event.payload.get("service_response")
            if service:
                self._extract_from_service_response(service)
            else:
                self._extract_images_from_results(event.payload.get("results", []))
        elif event_type is StreamEventType.AUGMENT_WITH_VIDEOS:
            service = event.payload.get("service_response")
            if service:
                self._extract_from_service_response(service)
            else:
                self._extract_videos_from_results(event.payload.get("results", []))
        elif event_type in {
            StreamEventType.AUGMENT_WITH_WEB_SERP,
            StreamEventType.AUGMENT_WITH_WEB,
            StreamEventType.AUGMENT_WITH_NEWS,
            StreamEventType.AUGMENT_WITH_DISCUSSIONS,
            StreamEventType.AUGMENT_WITH_SHOPPING,
            StreamEventType.AUGMENT_WITH_LOCAL,
        }:
            service = event.payload.get("service_response")
            if service:
                self._extract_from_service_response(service)
            else:
                self._extract_web_from_results(event.payload.get("results", []))
        elif event_type is StreamEventType.RAG:
            self._extract_rag(event.payload)
        elif event_type is StreamEventType.TABLE_OF_CONTENT:
            self._extract_toc(event.payload)
        elif event_type is StreamEventType.USAGE:
            self._extract_usage(event.payload)
        elif event_type is StreamEventType.INLINE_CITATION:
            self._inline_citations.append(event.payload)
        elif event_type is StreamEventType.AUGMENT_WITH_INLINE_CITATION:
            self._inline_citations.append(event.payload)

    def _add_url(self, url: str) -> None:
        if url and isinstance(url, str) and url not in self._seen_urls:
            self._seen_urls.add(url)
            self._urls.append(url)

    def _extract_from_service_response(self, service: Any) -> None:
        if not isinstance(service, dict):
            return

        results = service.get("results")
        service_type = service.get("type")
        if isinstance(results, list):
            if service_type == "images":
                self._extract_images_from_results(results)
            elif service_type == "videos":
                self._extract_videos_from_results(results)
            elif service_type in {"search", "news", "discussions", "local", "shopping"}:
                self._extract_web_from_results(results)

        web = service.get("web")
        if isinstance(web, dict):
            self._extract_web_from_results(web.get("results", []))

        images_block = service.get("images")
        if isinstance(images_block, dict):
            self._extract_images_from_results(images_block.get("results", []))
        elif isinstance(images_block, list):
            self._extract_images_from_results(images_block)

        videos_block = service.get("videos")
        if isinstance(videos_block, dict):
            self._extract_videos_from_results(videos_block.get("results", []))
        elif isinstance(videos_block, list):
            self._extract_videos_from_results(videos_block)

        news_block = service.get("news")
        if isinstance(news_block, dict):
            self._extract_web_from_results(news_block.get("results", []))

        disc_block = service.get("discussions")
        if isinstance(disc_block, dict):
            self._extract_web_from_results(disc_block.get("results", []))

    def _extract_web_from_results(self, results: list[Any]) -> None:
        for result in results:
            if not isinstance(result, dict):
                continue
            url = result.get("url")
            if not url or not isinstance(url, str):
                continue

            self._add_url(url)

            favicon: str | None = None
            meta_url = result.get("meta_url")
            if isinstance(meta_url, dict):
                favicon = meta_url.get("favicon")
            if not favicon:
                favicon = result.get("favicon")

            thumbnail_url: str | None = None
            thumbnail_original: str | None = None
            thumb = result.get("thumbnail")
            if isinstance(thumb, dict):
                thumbnail_url = thumb.get("src") or thumb.get("resized")
                thumbnail_original = thumb.get("original")
            elif isinstance(thumb, str) and thumb.startswith(("http://", "https://")):
                thumbnail_url = thumb

            try:
                web_result = WebResult(
                    url=url,
                    title=result.get("title") or result.get("full_title"),
                    description=result.get("description"),
                    favicon=favicon,
                    thumbnail=thumbnail_url,
                    thumbnail_original=thumbnail_original,
                )
                self._web_results.append(web_result)
            except Exception as e:
                logger.debug("Failed to create WebResult for %s: %s", url, e)

            img_url = thumbnail_original or thumbnail_url
            if img_url and img_url not in self._seen_image_urls:
                self._seen_image_urls.add(img_url)
                try:
                    image = ImageResult(
                        url=img_url,
                        title=result.get("title"),
                        thumbnail=thumbnail_url if thumbnail_url != img_url else None,
                        source=result.get("url"),
                    )
                    self._images.append(image)
                except Exception as e:
                    logger.debug("Failed to create ImageResult for %s: %s", img_url, e)

    def _extract_images_from_results(self, results: list[Any]) -> None:
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

            thumb_raw = result.get("thumbnail") or result.get("thumbnail_url")
            thumbnail: str | None = None
            if isinstance(thumb_raw, dict):
                thumbnail = thumb_raw.get("src") or thumb_raw.get("resized")
            elif isinstance(thumb_raw, str) and thumb_raw.startswith(("http://", "https://")):
                thumbnail = thumb_raw

            if url not in self._seen_image_urls:
                self._seen_image_urls.add(url)
                try:
                    image = ImageResult(
                        url=url,
                        title=result.get("title"),
                        thumbnail=thumbnail,
                        source=result.get("source") or result.get("domain"),
                        width=(properties.get("width") if isinstance(properties, dict) else None)
                        or result.get("width"),
                        height=(properties.get("height") if isinstance(properties, dict) else None)
                        or result.get("height"),
                    )
                    self._images.append(image)
                    self._add_url(url)
                except Exception as e:
                    logger.debug("Failed to create ImageResult for %s: %s", url, e)

    def _extract_videos_from_results(self, results: list[Any]) -> None:
        for result in results:
            if not isinstance(result, dict):
                continue
            url = result.get("url", "")
            if not url:
                continue

            thumb_raw = result.get("thumbnail")
            thumbnail: str | None = None
            if isinstance(thumb_raw, dict):
                thumbnail = thumb_raw.get("src") or thumb_raw.get("resized")
            elif isinstance(thumb_raw, str) and thumb_raw.startswith(("http://", "https://")):
                thumbnail = thumb_raw

            try:
                video = VideoResult(
                    url=url,
                    title=result.get("title"),
                    thumbnail=thumbnail,
                    duration=result.get("duration"),
                    channel=result.get("channel") or result.get("author"),
                )
                self._videos.append(video)
                self._add_url(url)
            except Exception as e:
                logger.debug("Failed to create VideoResult for %s: %s", url, e)

    def _build_infobox(self, infobox_data: dict[str, Any]) -> Infobox | None:
        title = infobox_data.get("title") or infobox_data.get("name") or infobox_data.get("full_title") or infobox_data.get("label")
        subtitle = infobox_data.get("subtitle") or infobox_data.get("description") or infobox_data.get("subtype") or infobox_data.get("type")

        image_url: str | None = None
        img_raw = infobox_data.get("image") or infobox_data.get("thumbnail") or infobox_data.get("image_url")
        if isinstance(img_raw, dict):
            image_url = img_raw.get("src") or img_raw.get("original") or img_raw.get("resized") or img_raw.get("url")
        elif isinstance(img_raw, str) and img_raw.startswith(("http://", "https://")):
            image_url = img_raw
        if not image_url:
            images = infobox_data.get("images", [])
            if isinstance(images, list) and images:
                first = images[0]
                if isinstance(first, dict):
                    image_url = first.get("original") or first.get("src") or first.get("resized")

        url: str | None = None
        url_raw = infobox_data.get("url") or infobox_data.get("website_url") or infobox_data.get("website")
        if isinstance(url_raw, str) and url_raw.startswith(("http://", "https://")):
            url = url_raw
        if not url:
            profiles = infobox_data.get("profiles") or infobox_data.get("providers", [])
            if isinstance(profiles, list):
                for p in profiles:
                    if isinstance(p, dict):
                        p_url = p.get("url", "")
                        if "wikipedia" in p_url:
                            url = p_url
                            break
                        elif not url:
                            url = p_url or None

        skip = {"title", "full_title", "name", "label", "subtitle", "description", "subtype", "type",
                "image", "thumbnail", "image_url", "images", "url", "website_url", "website", "profiles", "providers",
                "infobox", "is_source_local", "is_source_both", "fetched_content_timestamp",
                "page_age", "page_fetched", "family_friendly", "language",
                "position", "found_in_urls", "qanda", "actions", "icons",
                "attributes_shown", "distance", "zoom_level", "location",
                "coordinates", "category", "is_location"}
        
        attributes: dict[str, Any] = {}
        long_desc = infobox_data.get("long_desc")
        if long_desc:
            attributes["long_desc"] = long_desc
            
        raw_attrs = infobox_data.get("attributes", [])
        if isinstance(raw_attrs, list):
            for attr in raw_attrs:
                if isinstance(attr, list) and len(attr) == 2:
                    attributes[str(attr[0])] = attr[1]
                    
        for k, v in infobox_data.items():
            if k not in skip and k not in attributes and v is not None:
                attributes[k] = v

        if not title:
            return None

        try:
            return Infobox(
                title=str(title),
                subtitle=str(subtitle) if subtitle else None,
                image_url=image_url,
                url=url,
                attributes=attributes,
            )
        except Exception as e:
            logger.debug("Failed to create Infobox for %s: %s", title, e)
            return None

    def _extract_infobox_from_service_response(self, sr: dict[str, Any]) -> None:
        """Ekstrak infobox dari service_response di augment_with_tool_use."""
        infobox_data = sr.get("infobox")
        if not infobox_data and "title" in sr and "description" in sr and "type" in sr:
            infobox_data = sr

        if not isinstance(infobox_data, dict):
            return

        box = self._build_infobox(infobox_data)
        if box and not self._infobox:
            self._infobox = box

    def _extract_infobox(self, payload: dict[str, Any]) -> None:
        """Parse AUGMENT_WITH_INFOBOX payload menjadi Infobox model."""
        if self._infobox is not None:
            return
            
        data: dict[str, Any] = payload.get("infobox") or payload  # type: ignore[assignment]
        if not isinstance(data, dict):
            return

        box = self._build_infobox(data)
        if box:
            self._infobox = box

    def _extract_followups(self, payload: dict[str, Any]) -> None:
        """Parse FOLLOWUPS payload menjadi list pertanyaan."""
        # Server mengirim: {"type": "followups", "followups": ["q1", "q2", ...]}
        # atau: {"type": "followups", "queries": [...]}
        candidates = payload.get("followups") or payload.get("queries") or []
        if not isinstance(candidates, list):
            return
        for item in candidates:
            if isinstance(item, str) and item.strip():
                self._followups.append(item.strip())
            elif isinstance(item, dict):
                q = item.get("query") or item.get("text") or item.get("title")
                if q and isinstance(q, str):
                    self._followups.append(q.strip())

    def mark_failed(self) -> None:
        self._state = StreamState.FAILED
        self._failed = True

    def _extract_rag(self, payload: dict[str, Any]) -> None:
        content = payload.get("content") or payload.get("rag") or payload.get("results") or []
        if isinstance(content, list):
            self._rag_content.extend(content)

    def _extract_toc(self, payload: dict[str, Any]) -> None:
        items = payload.get("items") or payload.get("toc") or payload.get("headings") or []
        if isinstance(items, list):
            self._table_of_contents.extend(items)

    def _extract_usage(self, payload: dict[str, Any]) -> None:
        self._usage = dict(payload)

    def finalize(self) -> StreamResult:
        if not self._failed:
            self._state = StreamState.COMPLETE

        return StreamResult(
            text="".join(self._text_parts),
            thinking="".join(self._thinking_parts),
            tool_uses=list(self._tool_uses),
            urls=list(self._urls),
            images=list(self._images),
            videos=list(self._videos),
            web_results=list(self._web_results),
            infobox=self._infobox,
            followups=list(self._followups),
            citations=list(self._citations),
            inline_entities=list(self._inline_entities),
            inline_citations=list(self._inline_citations),
            rag_content=list(self._rag_content),
            table_of_contents=list(self._table_of_contents),
            usage=self._usage,
            raw_events=list(self._raw_events),
            state=self._state,
        )


__all__ = ["StreamAccumulator"]
