"""Parsers for the Brave SERP HTML and the suggest JSON endpoint."""

from __future__ import annotations

import logging
import re
from typing import Any, cast

from ..enums import SearchType
from ..models import ImageResult, NewsResult, SearchResult, SuggestItem, VideoResult, WebResult

logger = logging.getLogger("brave_api.search_parser")

_A_HREF = re.compile(r'<a[^>]+(?:data-href|href)=["\']([^"\']+)["\']', re.DOTALL)
_TITLE_SPAN = re.compile(
    r'<span[^>]+class="[^"]*\bsnippet-title\b[^"]*"[^>]*>(.*?)</span>',
    re.DOTALL,
)
_TITLE_DIV = re.compile(
    r'<div[^>]+class="[^"]*\btitle\b[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
_TITLE_ATTR = re.compile(
    r'<div[^>]+class="[^"]*\btitle\b[^"]*"[^>]+title="([^"]*)"',
    re.DOTALL,
)
_DESC_P = re.compile(
    r'<p[^>]+class="[^"]*\bsnippet-description\b[^"]*"[^>]*>(.*?)</p>',
    re.DOTALL,
)
_DESC_INLINE_QA = re.compile(
    r'<div[^>]+class="[^"]*\binline-qa-question\b[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
_GENERIC_SNIPPET = re.compile(
    r'<div[^>]+class="[^"]*\bgeneric-snippet\b[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
_AGE_T_SECONDARY = re.compile(
    r'<span[^>]+class="t-secondary"[^>]*>([^<]*\d{4})',
    re.DOTALL,
)
_AGE_RELATIVE = re.compile(
    r'<span[^>]+class="t-secondary"[^>]*>(\d+\s+\w+\s+ago)',
    re.DOTALL,
)
_DATE_PREFIX = re.compile(r"^[A-Za-z]+ \d{1,2}, \d{4} -\s*")

_DATA_URL = re.compile(r'\bdata-url=["\']([^"\']+)["\']')
_IMG_SRC = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')
_AGE_SPAN = re.compile(
    r'<span[^>]+class="[^"]*\bage\b[^"]*"[^>]*>(.*?)</span>',
    re.DOTALL,
)
_SOURCE_SPAN = re.compile(
    r'<span[^>]+class="[^"]*\bsource\b[^"]*"[^>]*>(.*?)</span>',
    re.DOTALL,
)
_HTML_TAG = re.compile(r"<[^>]+>")
_RESULT_SNIPPET = re.compile(
    r'<div[^>]+class="[^"]*\bsnippet\b[^"]*"[^>]+data-pos="\d+"',
    re.DOTALL,
)
_CITE_URL = re.compile(r"<cite[^>]*>(.*?)</cite>", re.DOTALL)
_NEWS_ARTICLE = re.compile(r'<div[^>]+class="[^"]*\bnews-article\b[^"]*"[^>]*>')
_IMAGE_RESULT = re.compile(r'<button[^>]+class="[^"]*\bimage-result\b[^"]*"[^>]*>')
_NEWS_RESULT = re.compile(
    r'<div[^>]+class="[^"]*\bsnippet\b[^"]*"[^>]+data-pos="\d+"[^>]+data-type="news"'
)
_VIDEO_RESULT = re.compile(
    r'<div[^>]+class="[^"]*\bsnippet\b[^"]*"[^>]+data-pos="\d+"[^>]+data-type="videos"'
)
_NEXT_PAGE = re.compile(r'href="[^"]*[?&](?:amp;)?offset=(\d+)[^"]*"[^>]*>.*?\bNext\b', re.DOTALL)

_HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&nbsp;": " ",
}


def _strip_tags(html: str) -> str:
    text = _HTML_TAG.sub("", html)
    for entity, replacement in _HTML_ENTITIES.items():
        text = text.replace(entity, replacement)
    return text.strip()


def _is_internal_search(url: str) -> bool:
    return "search.brave.com" in url and "/search" in url


def _extract_href(block: str) -> str | None:
    """Return the first non-internal result URL in a block."""
    match = _DATA_URL.search(block)
    if match:
        url = match.group(1).strip()
        if url.startswith(("http://", "https://")) and not _is_internal_search(url):
            return url
    for match in _A_HREF.finditer(block):
        url = match.group(1).strip()
        if url.startswith(("http://", "https://")) and not _is_internal_search(url):
            return url
    return None


def _extract_title(block: str) -> str | None:
    for pattern in (_TITLE_DIV, _TITLE_SPAN):
        match = pattern.search(block)
        if match:
            title = _strip_tags(match.group(1))
            if title and not title.startswith("›"):
                return title
    match = _TITLE_ATTR.search(block)
    if match:
        return match.group(1) or None
    return None


def _extract_description(block: str) -> str | None:
    for pattern in (_DESC_P, _DESC_INLINE_QA, _GENERIC_SNIPPET):
        match = pattern.search(block)
        if match:
            description = _strip_tags(match.group(1))
            description = _DATE_PREFIX.sub("", description)
            return description or None
    return None


def _extract_age(block: str) -> str | None:
    for pattern in (_AGE_SPAN, _AGE_T_SECONDARY, _AGE_RELATIVE):
        match = pattern.search(block)
        if match:
            return _strip_tags(match.group(1)) or None
    return None


def _extract_attr(block: str, tag: str, attribute: str) -> str | None:
    pattern = re.compile(rf'<{tag}[^>]+{re.escape(attribute)}=["\']([^"\']+)["\']', re.DOTALL)
    match = pattern.search(block)
    return match.group(1).strip() if match else None


def _extract_text_by_class(block: str, class_name: str) -> str | None:
    pattern = re.compile(
        rf'<(?:span|div)[^>]+class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>(.*?)</(?:span|div)>',
        re.DOTALL,
    )
    match = pattern.search(block)
    return _strip_tags(match.group(1)) or None if match else None


def _split_into_blocks(
    html: str,
    open_tag_pattern: re.Pattern[str],
    stop_pattern: re.Pattern[str] | None = None,
) -> list[str]:
    """Split *html* into blocks starting at each ``open_tag_pattern`` match.

    Each block ends at the next start position, the next *stop_pattern* match
    (when given), or the end of the document — so trailing sections such as
    news articles are never absorbed into a preceding result block.
    """
    positions = [match.start() for match in open_tag_pattern.finditer(html)]
    boundaries = list(positions)
    if stop_pattern is not None:
        boundaries.extend(match.start() for match in stop_pattern.finditer(html))
    boundaries.append(len(html))
    boundaries = sorted(set(boundaries))

    blocks: list[str] = []
    for start in positions:
        end = next((boundary for boundary in boundaries if boundary > start), len(html))
        blocks.append(html[start:end])
    return blocks


def _parse_web_results_from_html(html: str) -> list[WebResult]:
    results: list[WebResult] = []
    seen_urls: set[str] = set()

    for block in _split_into_blocks(html, _RESULT_SNIPPET, stop_pattern=_NEWS_ARTICLE):
        url = _extract_href(block)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = _extract_title(block)
        if not title:
            cite = _CITE_URL.search(block)
            if cite:
                title = _strip_tags(cite.group(1)) or None

        try:
            results.append(
                WebResult(
                    url=url,
                    title=title,
                    description=_extract_description(block),
                    age=_extract_age(block),
                )
            )
        except Exception as exc:
            logger.warning("Failed to create WebResult for %s: %s", url, exc)

    return results


def _parse_news_results_from_html(html: str) -> list[NewsResult]:
    results: list[NewsResult] = []
    seen_urls: set[str] = set()

    for block in _split_into_blocks(html, _NEWS_ARTICLE):
        url = _extract_href(block)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        img_match = _IMG_SRC.search(block)
        thumbnail = img_match.group(1) if img_match else None
        if thumbnail and not thumbnail.startswith(("http://", "https://")):
            thumbnail = None

        source_match = _SOURCE_SPAN.search(block)
        source = _strip_tags(source_match.group(1)) if source_match else None

        try:
            results.append(
                NewsResult(
                    url=url,
                    title=_extract_title(block),
                    description=_extract_description(block),
                    age=_extract_age(block),
                    thumbnail=thumbnail,
                    source=source,
                )
            )
        except Exception as exc:
            logger.warning("Failed to create NewsResult for %s: %s", url, exc)

    return results


def _parse_news_vertical_results_from_html(html: str) -> list[NewsResult]:
    results: list[NewsResult] = []
    seen_urls: set[str] = set()
    for block in _split_into_blocks(html, _NEWS_RESULT):
        url = _extract_attr(block, "a", "href")
        if not url or not url.startswith(("http://", "https://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        thumbnail = _extract_attr(block, "img", "src")
        title = _extract_text_by_class(block, "title")
        description = _extract_text_by_class(block, "description")
        source = _extract_text_by_class(block, "site-name-content")
        age = _extract_text_by_class(block, "age-snippet")
        results.append(
            NewsResult(
                url=url,
                title=title,
                description=description,
                age=age,
                thumbnail=thumbnail,
                source=source,
            )
        )
    return results


def _parse_image_results_from_html(html: str) -> list[ImageResult]:
    results: list[ImageResult] = []
    seen_urls: set[str] = set()

    for block in _split_into_blocks(html, _IMAGE_RESULT):
        url = _extract_attr(block, "img", "src")
        if not url or not url.startswith(("http://", "https://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        title = _extract_attr(block, "img", "alt") or _extract_text_by_class(
            block, "image-metadata-title"
        )
        source = _extract_text_by_class(block, "image-metadata-source")
        style = _extract_attr(block, "button", "style") or ""
        width_match = re.search(r"--width:\s*(\d+)", style)
        height_match = re.search(r"--height:\s*(\d+)", style)
        results.append(
            ImageResult(
                url=url,
                title=title,
                thumbnail=url,
                source=source,
                width=int(width_match.group(1)) if width_match else None,
                height=int(height_match.group(1)) if height_match else None,
            )
        )
    return results


def _parse_video_results_from_html(html: str) -> list[VideoResult]:
    results: list[VideoResult] = []
    seen_urls: set[str] = set()

    for block in _split_into_blocks(html, _VIDEO_RESULT):
        url = _extract_attr(block, "a", "href")
        if not url or not url.startswith(("http://", "https://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        thumbnail = _extract_attr(block, "img", "src")
        duration = _extract_text_by_class(block, "duration")
        title = _extract_text_by_class(block, "title") or _extract_text_by_class(
            block, "description"
        )
        channel = _extract_text_by_class(block, "site-name-content")
        results.append(
            VideoResult(
                url=url,
                title=title,
                thumbnail=thumbnail,
                duration=duration,
                channel=channel,
            )
        )
    return results


def _has_next_page(html: str) -> bool | None:
    match = _NEXT_PAGE.search(html)
    if match:
        return True
    if 'class="pagination' in html:
        return False
    return None


def parse_search_html(html: str, query: str, offset: int = 0) -> SearchResult:
    """Parse the SERP HTML into a :class:`SearchResult`."""
    result = SearchResult(
        query=query,
        web=_parse_web_results_from_html(html),
        news=_parse_news_results_from_html(html),
        offset=offset,
        has_more=_has_next_page(html),
    )
    logger.debug(
        "parse_search_html: query=%r offset=%d web=%d news=%d",
        query,
        offset,
        len(result.web),
        len(result.news),
    )
    return result


def parse_vertical_html(
    html: str,
    query: str,
    *,
    search_type: SearchType,
    offset: int = 0,
) -> SearchResult:
    """Parse one of Brave's specialized HTML search verticals."""
    result = SearchResult(
        query=query,
        search_type=search_type,
        offset=offset,
        has_more=_has_next_page(html),
    )
    if search_type is SearchType.IMAGES:
        result = result.model_copy(update={"images": _parse_image_results_from_html(html)})
    elif search_type is SearchType.VIDEOS:
        result = result.model_copy(update={"videos": _parse_video_results_from_html(html)})
    elif search_type is SearchType.NEWS:
        result = result.model_copy(update={"news": _parse_news_vertical_results_from_html(html)})
    elif search_type is SearchType.GOGGLES:
        result = result.model_copy(update={"web": _parse_web_results_from_html(html)})
    else:
        return parse_search_html(html, query=query, offset=offset)
    return result


def parse_suggest_json(data: Any, query: str) -> list[SuggestItem]:
    """Parse the suggest endpoint response into a list of suggestions.

    Supports the legacy ``[query, [items...]]`` tuple form and the object form
    with ``suggestions``/``results`` keys.
    """
    items: list[SuggestItem] = []

    raw_items: Any = None
    if isinstance(data, list):
        sequence = cast(list[Any], data)
        if len(sequence) >= 2:
            raw_items = sequence[1]
    elif isinstance(data, dict):
        data_object = cast(dict[str, Any], data)
        raw_items = data_object.get("suggestions") or data_object.get("results")

    if not isinstance(raw_items, list):
        return items

    for raw_item in cast(list[Any], raw_items):
        if isinstance(raw_item, str):
            if raw_item:
                items.append(SuggestItem(text=raw_item))
            continue
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, Any], raw_item)

        text = str(item.get("q") or item.get("query") or item.get("text") or "").strip()
        if not text:
            continue

        thumbnail: str | None = None
        raw_thumbnail = item.get("img") or item.get("thumbnail") or item.get("image")
        if isinstance(raw_thumbnail, str) and raw_thumbnail.startswith(("http://", "https://")):
            thumbnail = raw_thumbnail

        entity_type: str | None = None
        raw_type = item.get("entity_type") or item.get("type") or item.get("category")
        if raw_type:
            entity_type = str(raw_type)

        items.append(
            SuggestItem(
                text=text,
                is_entity=bool(item.get("is_entity") or item.get("entity")),
                thumbnail=thumbnail,
                entity_type=entity_type,
            )
        )

    logger.debug("parse_suggest_json: query=%r items=%d", query, len(items))
    return items


__all__ = ["parse_search_html", "parse_suggest_json", "parse_vertical_html"]
