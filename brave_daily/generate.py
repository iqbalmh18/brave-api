"""Build the Brave Daily for GitHub Pages.

Generates a multi-module intelligence dashboard by querying Brave News,
Search, Images, Videos, and Ask across five domains:

  - Global Pulse:    multi-domain trending stories
  - Trend Radar:     topic momentum sparklines
  - Threat Wire:     cybersecurity / OSINT digest
  - Market Scanner:  financial intelligence signals
  - Search Playground: pre-built brave-api demo results

The static site is fully self-contained (HTML + JSON). CSV and Markdown
exports are generated server-side so visitors can download them.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import re
import shutil
from collections.abc import Awaitable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

from brave_api import (
    BraveClient,
    ClientConfig,
    ImageResult,
    NewsResult,
    SearchResult,
    VideoResult,
    WebResult,
)

MAX_NEWS = 6
MAX_WEB = 5
MAX_IMAGES = 6
MAX_VIDEOS = 4

PULSE_DOMAINS: list[tuple[str, str, str]] = [
    ("tech", "Technology", "latest technology breakthroughs and big tech news today"),
    ("geopolitics", "Geopolitics", "geopolitics conflicts diplomacy international relations today"),
    ("finance", "Finance", "stock market economy financial news and central bank today"),
    ("cyber", "Cybersecurity", "cybersecurity hacking data breach vulnerability today"),
    ("science", "Science", "science discoveries research space climate today"),
]

TREND_TOPICS: list[tuple[str, str]] = [
    ("ai", "Artificial Intelligence"),
    ("quantum", "Quantum Computing"),
    ("ev", "Electric Vehicles"),
    ("space", "Space Exploration"),
    ("crypto", "Cryptocurrency"),
    ("climate", "Climate Change"),
    ("biotech", "Biotechnology"),
    ("chips", "Semiconductor Chips"),
    ("robotics", "Robotics & Automation"),
    ("nuclear", "Nuclear Energy"),
]

THREAT_QUERIES: list[tuple[str, str]] = [
    ("cve", "CVE vulnerability exploit critical zero-day today"),
    ("breach", "data breach leak exposed records today"),
    ("malware", "malware ransomware cyber attack campaign today"),
    ("apt", "APT threat actor nation state cyber espionage today"),
]

MARKET_QUERIES: list[tuple[str, str, str]] = [
    ("crypto", "Crypto", "bitcoin ethereum cryptocurrency market price today"),
    ("equities", "Equities", "stock market S&P NASDAQ earnings today"),
    ("macro", "Macro Economy", "federal reserve interest rate inflation GDP economy today"),
]

PLAYGROUND_QUERIES: list[tuple[str, str, str]] = [
    ("news_demo", "News Search", "artificial intelligence regulation 2025"),
    ("web_demo", "Web Search", "best open source projects 2025"),
    ("image_demo", "Image Search", "James Webb Space Telescope latest images"),
    ("video_demo", "Video Search", "machine learning tutorial beginner"),
    ("ask_demo", "AI Ask", "Explain quantum entanglement in simple terms"),
]

SEVERITY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "zero-day",
        "0-day",
        "critical",
        "rce",
        "remote code execution",
        "actively exploited",
        "emergency",
    ],
    "high": ["vulnerability", "exploit", "ransomware", "apt", "nation-state", "breach", "millions"],
    "medium": ["malware", "phishing", "trojan", "botnet", "campaign", "leak", "exposed"],
    "low": ["patch", "update", "advisory", "disclosure", "bug", "fix"],
}


@dataclass(frozen=True)
class Article:
    """Compact news/web result for the frontend."""

    title: str
    description: str
    url: str
    source: str
    domain: str
    age: str
    thumbnail: str | None


@dataclass(frozen=True)
class ThreatItem:
    """A single threat intelligence item."""

    title: str
    description: str
    url: str
    source: str
    severity: str
    category: str
    indicators: list[str]
    age: str


@dataclass(frozen=True)
class TrendPoint:
    """A single trend topic with heat metrics."""

    topic_id: str
    label: str
    article_count: int
    top_headline: str
    top_url: str
    momentum: str


@dataclass
class PlaygroundResult:
    """Pre-built API demo result."""

    query_id: str
    label: str
    query: str
    api_method: str
    python_code: str
    result_count: int
    results: list[dict[str, str | None]]


def article_from_news(result: NewsResult) -> Article:
    """Convert a Brave NewsResult to the site contract."""
    domain = urlparse(result.url).netloc.removeprefix("www.")
    return Article(
        title=result.title or "Untitled",
        description=result.description or "",
        url=result.url,
        source=result.source or domain or "Unknown",
        domain=domain,
        age=result.age or "Today",
        thumbnail=result.thumbnail,
    )


def article_from_web(result: WebResult) -> Article:
    """Convert a Brave WebResult to the site contract."""
    domain = urlparse(result.url).netloc.removeprefix("www.")
    return Article(
        title=result.title or "Untitled",
        description=result.description or "",
        url=result.url,
        source=result.source or domain or "Unknown",
        domain=domain,
        age=result.age or "Today",
        thumbnail=result.thumbnail,
    )


def compact_image(result: ImageResult) -> dict[str, str | None]:
    return {
        "title": result.title,
        "url": result.url,
        "thumbnail": result.thumbnail,
        "source": result.source,
    }


def compact_video(result: VideoResult) -> dict[str, str | None]:
    return {
        "title": result.title,
        "url": result.url,
        "thumbnail": result.thumbnail,
        "channel": result.channel,
        "duration": result.duration,
    }


def classify_severity(text: str) -> str:
    """Classify threat severity based on keyword matching."""
    lower = text.lower()
    for level in ("critical", "high", "medium", "low"):
        if any(kw in lower for kw in SEVERITY_KEYWORDS[level]):
            return level
    return "low"


def extract_indicators(text: str) -> list[str]:
    """Extract potential IOCs (IPs, CVEs, domains) from text."""
    indicators: list[str] = []
    indicators.extend(re.findall(r"CVE-\d{4}-\d{4,}", text, re.IGNORECASE))
    indicators.extend(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text))
    return list(dict.fromkeys(indicators))[:5]


async def safe_search(operation: Awaitable[SearchResult], query: str) -> SearchResult:
    """Return an empty result when an optional enrichment fails."""
    try:
        return await operation
    except Exception:
        return SearchResult(query=query)


async def ask_summary(client: BraveClient, prompt: str, fallback: str) -> tuple[str, str]:
    """Generate an AI editorial summary with fallback."""
    try:
        result = await client.ask(prompt, auto_tools=False, store_raw_events=False)
    except Exception:
        return fallback, "fallback"
    text = result.text.strip() if result.text else ""
    return (text, "Brave Ask") if text else (fallback, "fallback")


async def fetch_pulse_domain(
    client: BraveClient,
    domain_id: str,
    domain_label: str,
    query: str,
) -> dict[str, Any]:
    """Fetch one Global Pulse domain."""
    news = await safe_search(client.search_news(query), query)
    web = await safe_search(client.search(query), query)
    images = await safe_search(client.search_images(query), query)

    articles: list[Article] = []
    seen: set[str] = set()
    for r in news.news:
        if r.url not in seen:
            seen.add(r.url)
            articles.append(article_from_news(r))
    for r in web.web:
        if r.url not in seen:
            seen.add(r.url)
            articles.append(article_from_web(r))
    articles = articles[:MAX_NEWS]

    sources = {a.domain for a in articles}
    diversity = min(len(sources), 5)

    context = "\n".join(f"- {a.title}" for a in articles[:6])
    summary, source = await ask_summary(
        client,
        f"Write a concise 50-word intelligence brief about today's {domain_label} landscape "
        f"using only these headlines. No heading, no invented facts:\n{context}",
        f"Today's {domain_label} landscape is evolving. Explore the sources below.",
    )
    return {
        "id": domain_id,
        "label": domain_label,
        "query": query,
        "summary": summary,
        "summary_source": source,
        "diversity_score": diversity,
        "articles": [asdict(a) for a in articles],
        "images": [compact_image(i) for i in images.images[:MAX_IMAGES]],
    }


async def fetch_trend_topic(client: BraveClient, topic_id: str, label: str) -> dict[str, Any]:
    """Fetch a single trend topic's heat signal."""
    query = f"{label} news today"
    news = await safe_search(client.search_news(query), query)
    count = len(news.news)
    top = news.news[0] if news.news else None
    momentum = "rising" if count >= 5 else ("stable" if count >= 2 else "cooling")
    return {
        "topic_id": topic_id,
        "label": label,
        "article_count": count,
        "top_headline": top.title if top else "No coverage",
        "top_url": top.url if top else f"https://search.brave.com/search?q={quote_plus(query)}",
        "momentum": momentum,
    }


async def fetch_threat_wire(client: BraveClient) -> list[dict[str, Any]]:
    """Fetch Threat Wire module data."""
    threats: list[dict[str, Any]] = []
    for category, query in THREAT_QUERIES:
        news = await safe_search(client.search_news(query), query)
        web = await safe_search(client.search(query), query)
        seen: set[str] = set()
        for r in news.news:
            if r.url not in seen:
                seen.add(r.url)
                text = f"{r.title or ''} {r.description or ''}"
                threats.append(
                    {
                        "title": r.title or "Untitled",
                        "description": r.description or "",
                        "url": r.url,
                        "source": r.source or urlparse(r.url).netloc,
                        "severity": classify_severity(text),
                        "category": category,
                        "indicators": extract_indicators(text),
                        "age": r.age or "Today",
                    }
                )
        for r in web.web[:3]:
            if r.url not in seen:
                seen.add(r.url)
                text = f"{r.title or ''} {r.description or ''}"
                threats.append(
                    {
                        "title": r.title or "Untitled",
                        "description": r.description or "",
                        "url": r.url,
                        "source": r.source or urlparse(r.url).netloc,
                        "severity": classify_severity(text),
                        "category": category,
                        "indicators": extract_indicators(text),
                        "age": r.age or "Today",
                    }
                )
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    threats.sort(key=lambda t: severity_order.get(str(t["severity"]), 4))
    return threats[:20]


async def fetch_market_scanner(client: BraveClient) -> list[dict[str, Any]]:
    """Fetch Market Scanner module data."""
    sectors: list[dict[str, Any]] = []
    for sector_id, label, query in MARKET_QUERIES:
        news = await safe_search(client.search_news(query), query)
        articles = [asdict(article_from_news(r)) for r in news.news[:MAX_NEWS]]
        context = "\n".join(f"- {a['title']}" for a in articles[:5])
        sentiment, source = await ask_summary(
            client,
            f"In exactly 30 words, describe the market sentiment for {label} today "
            f"based only on these headlines. Use terms like bullish/bearish/neutral/mixed. "
            f"No heading:\n{context}",
            f"{label} sentiment is mixed today. Check the sources for details.",
        )
        sectors.append(
            {
                "id": sector_id,
                "label": label,
                "query": query,
                "sentiment": sentiment,
                "sentiment_source": source,
                "articles": articles,
            }
        )
    return sectors


async def fetch_playground(client: BraveClient) -> list[dict[str, Any]]:
    """Fetch Search Playground demo results."""
    demos: list[dict[str, Any]] = []
    for query_id, label, query in PLAYGROUND_QUERIES:
        if query_id == "ask_demo":
            try:
                result = await client.ask(query, auto_tools=False, store_raw_events=False)
                demos.append(
                    {
                        "query_id": query_id,
                        "label": label,
                        "query": query,
                        "api_method": "client.ask()",
                        "python_code": f'result = await client.ask("{query}")\nprint(result.text)',
                        "result_count": 1,
                        "results": [
                            {"text": result.text.strip() if result.text else "No response"}
                        ],
                    }
                )
            except Exception:
                demos.append(
                    {
                        "query_id": query_id,
                        "label": label,
                        "query": query,
                        "api_method": "client.ask()",
                        "python_code": f'result = await client.ask("{query}")\nprint(result.text)',
                        "result_count": 0,
                        "results": [{"text": "Demo unavailable"}],
                    }
                )
        elif query_id == "news_demo":
            sr = await safe_search(client.search_news(query), query)
            py_code = (
                f'result = await client.search_news("{query}")\n'
                "for item in result.news:\n"
                "    print(item.title)"
            )
            demos.append(
                {
                    "query_id": query_id,
                    "label": label,
                    "query": query,
                    "api_method": "client.search_news()",
                    "python_code": py_code,
                    "result_count": len(sr.news),
                    "results": [
                        {"title": r.title, "url": r.url, "source": r.source, "age": r.age}
                        for r in sr.news[:5]
                    ],
                }
            )
        elif query_id == "image_demo":
            sr = await safe_search(client.search_images(query), query)
            py_code = (
                f'result = await client.search_images("{query}")\n'
                "for img in result.images:\n"
                "    print(img.url)"
            )
            demos.append(
                {
                    "query_id": query_id,
                    "label": label,
                    "query": query,
                    "api_method": "client.search_images()",
                    "python_code": py_code,
                    "result_count": len(sr.images),
                    "results": [compact_image(r) for r in sr.images[:6]],
                }
            )
        elif query_id == "video_demo":
            sr = await safe_search(client.search_videos(query), query)
            py_code = (
                f'result = await client.search_videos("{query}")\n'
                "for v in result.videos:\n"
                "    print(v.title)"
            )
            demos.append(
                {
                    "query_id": query_id,
                    "label": label,
                    "query": query,
                    "api_method": "client.search_videos()",
                    "python_code": py_code,
                    "result_count": len(sr.videos),
                    "results": [compact_video(r) for r in sr.videos[:5]],
                }
            )
        else:
            sr = await safe_search(client.search(query), query)
            py_code = (
                f'result = await client.search("{query}")\n'
                "for item in result.web:\n"
                "    print(item.title, item.url)"
            )
            demos.append(
                {
                    "query_id": query_id,
                    "label": label,
                    "query": query,
                    "api_method": "client.search()",
                    "python_code": py_code,
                    "result_count": len(sr.web),
                    "results": [
                        {
                            "title": r.title,
                            "url": r.url,
                            "description": r.description,
                            "source": r.source,
                        }
                        for r in sr.web[:5]
                    ],
                }
            )
    return demos


def build_csv(dataset: dict[str, Any]) -> str:
    """Flatten the daily dataset into a CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["module", "category", "title", "description", "url", "source", "age", "severity"]
    )

    for domain in dataset.get("pulse", {}).get("domains", []):
        for article in domain.get("articles", []):
            writer.writerow(
                [
                    "Global Pulse",
                    domain.get("label", ""),
                    article.get("title", ""),
                    article.get("description", ""),
                    article.get("url", ""),
                    article.get("source", ""),
                    article.get("age", ""),
                    "",
                ]
            )

    for threat in dataset.get("threats", []):
        writer.writerow(
            [
                "Threat Wire",
                threat.get("category", ""),
                threat.get("title", ""),
                threat.get("description", ""),
                threat.get("url", ""),
                threat.get("source", ""),
                threat.get("age", ""),
                threat.get("severity", ""),
            ]
        )

    for sector in dataset.get("market", []):
        for article in sector.get("articles", []):
            writer.writerow(
                [
                    "Market Scanner",
                    sector.get("label", ""),
                    article.get("title", ""),
                    article.get("description", ""),
                    article.get("url", ""),
                    article.get("source", ""),
                    article.get("age", ""),
                    "",
                ]
            )

    return output.getvalue()


def build_markdown_report(dataset: dict[str, Any]) -> str:
    """Generate a Markdown daily intelligence report."""
    date = dataset.get("generated_at", "Unknown")
    lines: list[str] = [
        "# Brave Daily — Daily Report",
        "",
        f"**Generated:** {date}  ",
        "**Source:** Brave News, Search, Images, Videos, Ask  ",
        "**Product:** brave-api (github.com/iqbalmh18/brave-api)",
        "",
        "---",
        "",
    ]

    lines.append("## Global Pulse\n")
    for domain in dataset.get("pulse", {}).get("domains", []):
        lines.append(f"### {domain.get('label', '')}\n")
        lines.append(f"{domain.get('summary', '')}\n")
        for article in domain.get("articles", []):
            title = article.get("title", "")
            url = article.get("url", "")
            src = article.get("source", "")
            age = article.get("age", "")
            lines.append(f"- [{title}]({url}) — *{src}* ({age})")
        lines.append("")

    lines.append("## Trend Radar\n")
    lines.append("| Topic | Articles | Momentum | Top Headline |")
    lines.append("|-------|----------|----------|-------------|")
    for topic in dataset.get("trends", []):
        lbl = topic.get("label", "")
        cnt = topic.get("article_count", 0)
        mom = str(topic.get("momentum", "")).upper()
        top = topic.get("top_headline", "")
        lines.append(f"| {lbl} | {cnt} | [{mom}] | {top} |")
    lines.append("")

    lines.append("## Threat Wire\n")
    for threat in dataset.get("threats", [])[:10]:
        sev = str(threat.get("severity", "")).upper()
        title = threat.get("title", "")
        url = threat.get("url", "")
        src = threat.get("source", "")
        lines.append(f"- **[{sev}]** [{title}]({url}) — *{src}*")
        if threat.get("indicators"):
            lines.append(f"  - IOCs: `{'`, `'.join(threat['indicators'])}`")
    lines.append("")

    lines.append("## Market Scanner\n")
    for sector in dataset.get("market", []):
        lines.append(f"### {sector.get('label', '')}\n")
        lines.append(f"**Sentiment:** {sector.get('sentiment', '')}\n")
        for article in sector.get("articles", [])[:3]:
            lines.append(f"- [{article.get('title', '')}]({article.get('url', '')})")
        lines.append("")

    lines.append("---\n")
    lines.append(
        "*Generated automatically by [brave-api](https://github.com/iqbalmh18/brave-api)*\n"
    )
    return "\n".join(lines)


def build_threat_feed(threats: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    """Build a STIX-lite threat intelligence feed."""
    return {
        "type": "brave-intel-threat-feed",
        "version": "1.0",
        "generated_at": generated_at,
        "source": "Brave Daily via brave-api",
        "threat_count": len(threats),
        "severity_breakdown": {
            level: sum(1 for t in threats if t.get("severity") == level)
            for level in ("critical", "high", "medium", "low")
        },
        "threats": threats,
    }


async def build_dataset() -> dict[str, Any]:
    """Build the complete daily intelligence dataset."""
    config = ClientConfig(language="en", ui_lang="en-us", country="us", max_retries=2)
    async with BraveClient(config) as client:
        pulse_domains: list[dict[str, Any]] = []
        for domain_id, label, query in PULSE_DOMAINS:
            domain = await fetch_pulse_domain(client, domain_id, label, query)
            pulse_domains.append(domain)

        trends: list[dict[str, Any]] = []
        for topic_id, label in TREND_TOPICS:
            trend = await fetch_trend_topic(client, topic_id, label)
            trends.append(trend)

        threats = await fetch_threat_wire(client)
        market = await fetch_market_scanner(client)
        playground = await fetch_playground(client)

        all_headlines: list[str] = []
        for d in pulse_domains:
            for a in d.get("articles", [])[:2]:
                all_headlines.append(a.get("title", ""))
        context = "\n".join(f"- {h}" for h in all_headlines[:10])
        brief, brief_source = await ask_summary(
            client,
            f"Write a 100-word global intelligence briefing connecting these headlines "
            f"into one cohesive overview. Cover tech, geopolitics, finance, cyber, science. "
            f"Professional tone, no heading:\n{context}",
            "Today's intelligence landscape spans technology breakthroughs, geopolitical shifts, "
            "financial market movements, cybersecurity threats, and scientific discoveries. "
            "Explore each module below for detailed coverage and downloadable datasets.",
        )

    generated_at = datetime.now(UTC).isoformat()

    total_articles = sum(len(d.get("articles", [])) for d in pulse_domains)
    total_articles += sum(len(s.get("articles", [])) for s in market)
    total_articles += len(threats)
    total_sources = len({a.get("domain") for d in pulse_domains for a in d.get("articles", [])})

    dataset: dict[str, Any] = {
        "generated_at": generated_at,
        "product": "Brave Daily",
        "source": "Brave News, Search, Images, Videos, Ask via brave-api",
        "brief": brief,
        "brief_source": brief_source,
        "stats": {
            "total_articles": total_articles,
            "total_sources": total_sources,
            "total_threats": len(threats),
            "total_trends": len(trends),
            "modules": 6,
        },
        "pulse": {"domains": pulse_domains},
        "trends": trends,
        "threats": threats,
        "market": market,
        "playground": playground,
    }
    return dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("brave_daily/dist"))
    return parser.parse_args()


def main() -> None:
    """Generate the Brave Daily site and data exports."""
    args = parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    for filename in ("index.html", "styles.css", "app.js", "favicon.svg"):
        shutil.copy2(Path(__file__).with_name(filename), out / filename)

    dataset = asyncio.run(build_dataset())
    generated_at = str(dataset.get("generated_at", ""))

    data_dir = out / "data"
    data_dir.mkdir(exist_ok=True)

    (data_dir / "intel.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    threat_feed = build_threat_feed(list(dataset.get("threats", [])), generated_at)
    (data_dir / "threats.json").write_text(
        json.dumps(threat_feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    csv_content = build_csv(dataset)
    (data_dir / "export.csv").write_text(csv_content, encoding="utf-8")

    md_content = build_markdown_report(dataset)
    (data_dir / "report.md").write_text(md_content, encoding="utf-8")

    stats = dataset.get("stats", {})
    print(
        f"Brave Daily: {stats.get('total_articles', 0)} articles, "
        f"{stats.get('total_threats', 0)} threats, "
        f"{stats.get('total_trends', 0)} trends -> {out}"
    )


if __name__ == "__main__":
    main()
