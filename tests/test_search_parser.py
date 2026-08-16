"""Tests for the SERP HTML and suggest JSON parsers."""

from __future__ import annotations

from brave_api._internal.search_parser import (
    parse_search_html,
    parse_suggest_json,
    parse_vertical_html,
)
from brave_api.enums import SearchType

_SERP_HTML = """
<html>
<body>
<div class="snippet" data-pos="0">
  <a data-href="https://example.com/1"><span class="snippet-title">Example One</span></a>
  <p class="snippet-description">First description.</p>
  <span class="t-secondary">2 days ago</span>
</div>
<div class="snippet" data-pos="1">
  <a data-href="https://example.com/2"><div class="title" title="Example Two"></div></a>
  <p class="snippet-description">Aug 1, 2026 - Second description.</p>
</div>
<div class="news-article">
  <a href="https://news.example.com/n1"><span class="snippet-title">News One</span></a>
  <span class="source">Example News</span>
  <img src="https://news.example.com/thumb.jpg">
</div>
</body>
</html>
"""


class TestSearchHtml:
    def test_parses_web_results(self) -> None:
        result = parse_search_html(_SERP_HTML, query="python", offset=0)
        assert result.query == "python"
        assert len(result.web) == 2
        assert result.web[0].url == "https://example.com/1"
        assert result.web[0].title == "Example One"
        assert result.web[0].description == "First description."
        assert result.web[0].age == "2 days ago"

    def test_strips_date_prefix_from_description(self) -> None:
        result = parse_search_html(_SERP_HTML, query="python")
        assert result.web[1].description == "Second description."
        assert result.web[1].title == "Example Two"

    def test_parses_news_results(self) -> None:
        result = parse_search_html(_SERP_HTML, query="python")
        assert len(result.news) == 1
        news = result.news[0]
        assert news.url == "https://news.example.com/n1"
        assert news.title == "News One"
        assert news.source == "Example News"
        assert news.thumbnail == "https://news.example.com/thumb.jpg"

    def test_has_results_and_urls(self) -> None:
        result = parse_search_html(_SERP_HTML, query="python")
        assert result.has_results
        assert "https://example.com/1" in result.urls
        assert "https://news.example.com/n1" in result.urls

    def test_skips_brave_search_internal_links(self) -> None:
        html = """
        <div class="snippet" data-pos="0">
          <a href="https://search.brave.com/search?q=x"><span class="snippet-title">t</span></a>
          <a href="https://example.com/real"><span class="snippet-title">Real</span></a>
        </div>
        """
        result = parse_search_html(html, query="x")
        assert [item.url for item in result.web] == ["https://example.com/real"]

    def test_empty_html_yields_empty_result(self) -> None:
        result = parse_search_html("", query="x")
        assert result.web == []
        assert result.news == []
        assert not result.has_results

    def test_parses_images_vertical(self) -> None:
        html = (
            '<button class="image-result" style="--width: 400; --height: 300;">'
            '<img src="https://imgs.example/image.jpg" alt="An image">'
            '<span class="image-metadata-source">example.com</span>'
            '<span class="image-metadata-title">An image</span></button>'
        )
        result = parse_vertical_html(html, "cats", search_type=SearchType.IMAGES)
        assert result.search_type is SearchType.IMAGES
        assert result.images[0].url == "https://imgs.example/image.jpg"
        assert result.images[0].width == 400
        assert result.images[0].source == "example.com"

    def test_parses_videos_vertical(self) -> None:
        html = (
            '<div class="snippet" data-pos="0" data-type="videos">'
            '<a class="thumbnail"><img src="https://img.example/thumb.jpg"></a>'
            '<a href="https://video.example/watch/1">'
            '<div class="title">Video title</div><div class="duration">01:22</div>'
            '<div class="site-name-content">Example Channel</div></a></div>'
        )
        result = parse_vertical_html(html, "cats", search_type=SearchType.VIDEOS)
        assert result.videos[0].url == "https://video.example/watch/1"
        assert result.videos[0].title == "Video title"
        assert result.videos[0].duration == "01:22"

    def test_parses_goggles_as_web_results(self) -> None:
        result = parse_vertical_html(_SERP_HTML, "python", search_type=SearchType.GOGGLES, offset=2)
        assert result.search_type is SearchType.GOGGLES
        assert result.offset == 2
        assert len(result.web) == 2


class TestSuggestJson:
    def test_parses_tuple_form(self) -> None:
        items = parse_suggest_json(["python", ["python tutorial", "python 3"]], query="python")
        assert [item.text for item in items] == ["python tutorial", "python 3"]
        assert all(not item.is_entity for item in items)

    def test_parses_dict_form_with_entities(self) -> None:
        data = {
            "suggestions": [
                {
                    "q": "python",
                    "is_entity": True,
                    "entity_type": "ProgrammingLanguage",
                    "img": "https://example.com/py.jpg",
                }
            ]
        }
        items = parse_suggest_json(data, query="py")
        assert len(items) == 1
        item = items[0]
        assert item.text == "python"
        assert item.is_entity
        assert item.entity_type == "ProgrammingLanguage"
        assert item.thumbnail == "https://example.com/py.jpg"

    def test_rejects_relative_thumbnails(self) -> None:
        data = {"results": [{"q": "x", "img": "/images/thumb.jpg"}]}
        items = parse_suggest_json(data, query="x")
        assert items[0].thumbnail is None

    def test_skips_empty_and_non_dict_items(self) -> None:
        items = parse_suggest_json(["q", ["", 42, {"q": "ok"}]], query="q")
        assert [item.text for item in items] == ["ok"]

    def test_malformed_data_yields_empty(self) -> None:
        assert parse_suggest_json(None, query="x") == []
        assert parse_suggest_json(["only-one-element"], query="x") == []
