"""Deterministic checks for the Brave Daily data contract."""

from typing import Any

from brave_api import NewsResult
from brave_daily.generate import (
    article_from_news,
    build_csv,
    build_markdown_report,
    build_threat_feed,
    classify_severity,
    extract_indicators,
)


def test_article_contract_preserves_source_and_domain() -> None:
    article = article_from_news(
        NewsResult(
            url="https://www.example.com/ai-story",
            title="AI story",
            description="A useful summary.",
            age="Today",
            thumbnail="https://example.com/image.jpg",
            source="Example News",
        )
    )

    assert article.domain == "example.com"
    assert article.source == "Example News"


def test_threat_severity_classification() -> None:
    assert classify_severity("Critical 0-day vulnerability actively exploited") == "critical"
    assert classify_severity("High severity ransomware campaign") == "high"
    assert classify_severity("New malware phishing campaign") == "medium"
    assert classify_severity("Security update patch released") == "low"


def test_extract_indicators() -> None:
    text = "Vulnerability CVE-2025-12345 exploited from 192.168.1.1"
    iocs = extract_indicators(text)
    assert "CVE-2025-12345" in iocs
    assert "192.168.1.1" in iocs


def test_export_builders() -> None:
    dataset: dict[str, Any] = {
        "generated_at": "2026-08-22T00:00:00Z",
        "pulse": {"domains": []},
        "trends": [],
        "threats": [
            {
                "title": "Test Threat",
                "description": "Test description",
                "url": "https://example.com/threat",
                "source": "example.com",
                "severity": "high",
                "category": "malware",
                "indicators": ["CVE-2025-0001"],
                "age": "Today",
            }
        ],
        "market": [],
    }

    csv_data = build_csv(dataset)
    assert "Threat Wire" in csv_data
    assert "Test Threat" in csv_data

    md_report = build_markdown_report(dataset)
    assert "# Brave Daily — Daily Report" in md_report

    threat_feed = build_threat_feed(dataset["threats"], "2026-08-22T00:00:00Z")
    assert threat_feed["threat_count"] == 1
    assert threat_feed["severity_breakdown"]["high"] == 1
