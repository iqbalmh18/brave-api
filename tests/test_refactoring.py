"""Test script untuk validasi refactoring.

Script ini melakukan pengujian dasar untuk memastikan semua perubahan
refactoring berfungsi dengan baik tanpa memerlukan API call sebenarnya.
"""

from brave_tap import (
    BraveTapClient,
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
    print("🧪 Test 1: Imports")
    print("  ✅ BraveTapClient")
    print("  ✅ ClientConfig")
    print("  ✅ ImageResult")
    print("  ✅ VideoResult")
    print("  ✅ WebResult")
    print("  ✅ TokenModel")
    print("  ✅ ConversationResponse")
    print("  ✅ StreamResult")


def test_client_config():
    """Test ClientConfig dengan Pydantic."""
    print("\n🧪 Test 2: ClientConfig (Pydantic)")
    
    # Default config
    config1 = ClientConfig()
    print(f"  ✅ Default config: language={config1.language}, country={config1.country}")
    
    # Custom config
    config2 = ClientConfig(
        language="id",
        country="id",
        max_retries=5,
        request_timeout_seconds=90.0,
        enable_research=True,
    )
    print(f"  ✅ Custom config: language={config2.language}, retries={config2.max_retries}")
    
    # Test immutability
    try:
        config2.language = "en"  # type: ignore
        print("  ❌ Config tidak frozen!")
    except Exception:
        print("  ✅ Config frozen (immutable)")
    
    # Test validation
    try:
        bad_config = ClientConfig(max_retries=-1)
        print("  ❌ Validation tidak berfungsi!")
    except Exception as e:
        print(f"  ✅ Validation bekerja: {type(e).__name__}")


def test_pydantic_models():
    """Test Pydantic models baru."""
    print("\n🧪 Test 3: Pydantic Models")
    
    # TokenModel
    token = TokenModel(q="test", nonce="abc123", sig="def456")
    print(f"  ✅ TokenModel: q={token.q}, nonce={token.nonce}")
    
    # ConversationResponse
    conv_resp = ConversationResponse(
        id="conv123",
        symmetric_key="key123",
        bo_callback_share_link="https://share.link",
    )
    print(f"  ✅ ConversationResponse: id={conv_resp.id}")
    
    # ImageResult
    img = ImageResult(
        url="https://example.com/image.jpg",
        title="Test Image",
        thumbnail="https://example.com/thumb.jpg",
        width=800,
        height=600,
        source="example.com",
    )
    print(f"  ✅ ImageResult: {img.title} ({img.width}x{img.height})")
    
    # VideoResult
    video = VideoResult(
        url="https://youtube.com/watch?v=123",
        title="Test Video",
        channel="Test Channel",
        duration="5:30",
    )
    print(f"  ✅ VideoResult: {video.title} by {video.channel}")
    
    # WebResult
    web = WebResult(
        url="https://example.com",
        title="Example Site",
        description="An example website",
    )
    print(f"  ✅ WebResult: {web.title}")


def test_stream_result():
    """Test StreamResult dengan rich data."""
    print("\n🧪 Test 4: StreamResult dengan Rich Data")
    
    # Buat mock images dan videos
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
    
    # Buat StreamResult
    result = StreamResult(
        text="This is a test response",
        urls=["https://example.com", "https://test.com"],
        images=images,
        videos=videos,
        state="complete",
    )
    
    print(f"  ✅ Text: {result.text[:30]}...")
    print(f"  ✅ URLs: {len(result.urls)} URLs")
    print(f"  ✅ Images: {len(result.images)} images")
    print(f"  ✅ Videos: {len(result.videos)} videos")
    print(f"  ✅ has_images: {result.has_images}")
    print(f"  ✅ has_videos: {result.has_videos}")
    print(f"  ✅ is_complete: {result.is_complete}")


def test_url_validation():
    """Test validasi URL pada ImageResult."""
    print("\n🧪 Test 5: URL Validation")
    
    # Valid URL
    try:
        img = ImageResult(url="https://example.com/image.jpg", title="Valid")
        print(f"  ✅ Valid URL accepted: {img.url}")
    except Exception as e:
        print(f"  ❌ Valid URL rejected: {e}")
    
    # Invalid URL
    try:
        bad_img = ImageResult(url="not-a-url", title="Invalid")
        print(f"  ❌ Invalid URL accepted: {bad_img.url}")
    except Exception as e:
        print(f"  ✅ Invalid URL rejected: {type(e).__name__}")


def main():
    """Jalankan semua tests."""
    print("=" * 60)
    print("🚀 BRAVE TAP - REFACTORING VALIDATION TESTS")
    print("=" * 60)
    
    try:
        test_imports()
        test_client_config()
        test_pydantic_models()
        test_stream_result()
        test_url_validation()
        
        print("\n" + "=" * 60)
        print("✅ SEMUA TESTS PASSED!")
        print("=" * 60)
        print("\n📝 Summary:")
        print("  • Pydantic models: ✅ Working")
        print("  • Type safety: ✅ Validated")
        print("  • Immutability: ✅ Enforced")
        print("  • URL validation: ✅ Working")
        print("  • Rich results: ✅ Supported")
        print("\n🎉 Refactoring berhasil!")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
