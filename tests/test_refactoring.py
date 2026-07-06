"""Test script untuk validasi refactoring.

Script ini melakukan pengujian dasar untuk memastikan semua perubahan
refactoring berfungsi dengan baik tanpa memerlukan API call sebenarnya.
"""

import pytest

from brave_api import (
    BraveClient,
    ClientConfig,
    ImageResult,
    ConversationResponse,
    StreamResult,
    TokenModel,
    VideoResult,
    WebResult,
)


def test_imports():
    """Test bahwa semua model baru bisa diimport."""
    assert BraveClient is not None
    assert ClientConfig is not None
    assert ImageResult is not None
    assert VideoResult is not None
    assert WebResult is not None
    assert TokenModel is not None
    assert ConversationResponse is not None
    assert StreamResult is not None


def test_client_config():
    """Test ClientConfig dengan Pydantic."""
    # Default config
    config1 = ClientConfig()
    assert config1.language == "en"
    assert config1.country == "us"
    
    # Custom config
    config2 = ClientConfig(
        language="id",
        country="id",
        max_retries=5,
        request_timeout_seconds=90.0,
        enable_research=True,
    )
    assert config2.language == "id"
    assert config2.max_retries == 5
    
    # Test immutability
    with pytest.raises(Exception):
        config2.language = "en"  # type: ignore
    
    # Test validation
    with pytest.raises(Exception):
        ClientConfig(max_retries=-1)


def test_pydantic_models():
    """Test Pydantic models baru."""
    # TokenModel
    token = TokenModel(q="test", nonce="abc123", sig="def456")
    assert token.q == "test"
    assert token.nonce == "abc123"
    
    # ConversationResponse
    conv_resp = ConversationResponse(
        id="conv123",
        symmetric_key="key123",
        bo_callback_share_link="https://share.link",
    )
    assert conv_resp.id == "conv123"
    
    # ImageResult
    img = ImageResult(
        url="https://example.com/image.jpg",
        title="Test Image",
        thumbnail="https://example.com/thumb.jpg",
        width=800,
        height=600,
        source="example.com",
    )
    assert img.width == 800
    
    # VideoResult
    video = VideoResult(
        url="https://youtube.com/watch?v=123",
        title="Test Video",
        channel="Test Channel",
        duration="5:30",
    )
    assert video.title == "Test Video"
    
    # WebResult
    web = WebResult(
        url="https://example.com",
        title="Example Site",
        description="An example website",
    )
    assert web.title == "Example Site"


def test_stream_result():
    """Test StreamResult dengan rich data."""
    images = [
        ImageResult(
            url=f"https://example.com/img{i}.jpg",
            title=f"Image {i}",
            width=800,
            height=600,
        )
        for i in range(3)
    ]
    
    videos = [
        VideoResult(
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            channel="Test Channel",
        )
        for i in range(2)
    ]
    
    result = StreamResult(
        text="This is a test response",
        urls=["https://example.com", "https://test.com"],
        images=images,
        videos=videos,
        state="complete", # type: ignore
    )
    
    assert len(result.urls) == 2
    assert len(result.images) == 3
    assert len(result.videos) == 2
    assert result.has_images is True
    assert result.has_videos is True
    assert result.is_complete is True


def test_url_validation():
    """Test validasi URL pada ImageResult."""
    # Valid URL
    img = ImageResult(url="https://example.com/image.jpg", title="Valid")
    assert img.url == "https://example.com/image.jpg"
    
    # Invalid URL
    with pytest.raises(Exception):
        ImageResult(url="not-a-url", title="Invalid")
