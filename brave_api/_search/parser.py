from __future__ import annotations

import logging
import re

from typing import Any

from .._internal.models import (
    SearchNewsResult,
    SearchResult,
    SearchWebResult,
    SuggestItem,
)

logger = logging.getLogger("brave_api.search.parser")

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

_CITE_URL = re.compile(r'<cite[^>]*>(.*?)</cite>', re.DOTALL)
_NEWS_ARTICLE = re.compile(r'<div[^>]+class="[^"]*\bnews-article\b[^"]*"[^>]*>')


def _strip_tags(html: str) -> str:
    text = _HTML_TAG.sub("", html)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    return text.strip()


def _extract_href(block: str) -> str | None:
    m = _DATA_URL.search(block)
    if m:
        url = m.group(1).strip()
        if url.startswith(("http://", "https://")):
            return url

    m = _A_HREF.search(block)
    if m:
        url = m.group(1).strip()
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("/url?") or url.startswith("//"):
            pass
    return None


def _extract_title(block: str) -> str | None:
    for pat in (_TITLE_DIV, _TITLE_SPAN):
        m = pat.search(block)
        if m:
            title = _strip_tags(m.group(1))
            if title and not title.startswith("›"):
                return title
    m = _TITLE_ATTR.search(block)
    if m:
        return m.group(1) or None
    return None


def _extract_description(block: str) -> str | None:
    m = _DESC_P.search(block)
    if m:
        desc = _strip_tags(m.group(1))
        desc = _DATE_PREFIX.sub("", desc)
        return desc or None
    m = _DESC_INLINE_QA.search(block)
    if m:
        desc = _strip_tags(m.group(1))
        desc = _DATE_PREFIX.sub("", desc)
        return desc or None
    m = _GENERIC_SNIPPET.search(block)
    if m:
        desc = _strip_tags(m.group(1))
        desc = _DATE_PREFIX.sub("", desc)
        return desc or None
    return None


def _extract_age(block: str) -> str | None:
    m = _AGE_SPAN.search(block)
    if m:
        return _strip_tags(m.group(1)) or None
    m = _AGE_T_SECONDARY.search(block)
    if m:
        return _strip_tags(m.group(1)) or None
    m = _AGE_RELATIVE.search(block)
    if m:
        return _strip_tags(m.group(1)) or None
    return None


def _split_into_blocks(html: str, open_tag_pattern: re.Pattern[str]) -> list[str]:
    blocks: list[str] = []
    positions = [m.start() for m in open_tag_pattern.finditer(html)]

    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(html)
        blocks.append(html[start:end])

    return blocks


def _parse_web_results_from_html(html: str) -> list[SearchWebResult]:
    results: list[SearchWebResult] = []
    seen_urls: set[str] = set()

    blocks = _split_into_blocks(html, _RESULT_SNIPPET)

    for block in blocks:
        url = _extract_href(block)
        if not url or url in seen_urls:
            continue

        if "search.brave.com" in url and "/search" in url:
            continue

        seen_urls.add(url)

        title = _extract_title(block)
        description = _extract_description(block)

        if not title:
            m = _CITE_URL.search(block)
            if m:
                title = _strip_tags(m.group(1)) or None

        age = _extract_age(block)

        try:
            results.append(
                SearchWebResult(
                    url=url,
                    title=title,
                    description=description,
                    age=age,
                )
            )
        except Exception as exc:
            logger.warning("Failed to create SearchWebResult for %s: %s", url, exc)

    return results


def _parse_news_results_from_html(html: str) -> list[SearchNewsResult]:
    results: list[SearchNewsResult] = []
    seen_urls: set[str] = set()

    blocks = _split_into_blocks(html, _NEWS_ARTICLE)

    for block in blocks:
        url = _extract_href(block)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = _extract_title(block)
        description = _extract_description(block)
        age = _extract_age(block)

        img_m = _IMG_SRC.search(block)
        thumbnail = img_m.group(1) if img_m else None
        if thumbnail and not thumbnail.startswith(("http://", "https://")):
            thumbnail = None

        src_m = _SOURCE_SPAN.search(block)
        source = _strip_tags(src_m.group(1)) if src_m else None

        try:
            results.append(
                SearchNewsResult(
                    url=url,
                    title=title,
                    description=description,
                    age=age,
                    thumbnail=thumbnail,
                    source=source,
                )
            )
        except Exception as exc:
            logger.warning("Failed to create SearchNewsResult for %s: %s", url, exc)

    return results


def parse_search_html(html: str, query: str, offset: int = 0) -> SearchResult:
    web_results = _parse_web_results_from_html(html)
    news_results = _parse_news_results_from_html(html)

    logger.debug(
        "parse_search_html: query=%r offset=%d web=%d news=%d",
        query,
        offset,
        len(web_results),
        len(news_results),
    )

    return SearchResult(
        query=query,
        web=web_results,
        news=news_results,
        offset=offset,
    )


def parse_suggest_json(data: Any, query: str) -> list[SuggestItem]:
    items: list[SuggestItem] = []

    if isinstance(data, list) and len(data) >= 2:
        suggestions_raw = data[1]

        if isinstance(suggestions_raw, list):
            for item in suggestions_raw:
                if isinstance(item, str):
                    if item:
                        items.append(SuggestItem(text=item))
                elif isinstance(item, dict):
                    text = str(item.get("q") or item.get("query") or item.get("text") or "").strip()
                    if not text:
                        continue

                    is_entity = bool(item.get("is_entity") or item.get("entity"))
                    thumbnail: str | None = item.get("img") or item.get("thumbnail") or item.get("image")
                    if thumbnail and not str(thumbnail).startswith(("http://", "https://")):
                        thumbnail = None
                    entity_type: str | None = item.get("entity_type") or item.get("type") or item.get("category")

                    items.append(
                        SuggestItem(
                            text=text,
                            is_entity=is_entity,
                            thumbnail=str(thumbnail) if thumbnail else None,
                            entity_type=str(entity_type) if entity_type else None,
                        )
                    )

    elif isinstance(data, dict):
        for item in data.get("suggestions") or data.get("results") or []:
            if isinstance(item, str) and item:
                items.append(SuggestItem(text=item))
            elif isinstance(item, dict):
                text = str(item.get("q") or item.get("query") or item.get("text") or "").strip()
                if text:
                    is_entity = bool(item.get("is_entity") or item.get("entity"))
                    thumbnail = item.get("img") or item.get("thumbnail") or item.get("image")
                    if thumbnail and not str(thumbnail).startswith(("http://", "https://")):
                        thumbnail = None
                    entity_type = item.get("entity_type") or item.get("type") or item.get("category")
                    items.append(
                        SuggestItem(
                            text=text,
                            is_entity=is_entity,
                            thumbnail=str(thumbnail) if thumbnail else None,
                            entity_type=str(entity_type) if entity_type else None,
                        )
                    )

    logger.debug("parse_suggest_json: query=%r items=%d", query, len(items))
    return items


__all__ = ["parse_search_html", "parse_suggest_json"]
