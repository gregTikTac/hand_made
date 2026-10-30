"""Video link parsing."""

import pytest

from catalog.video import (
    PROVIDER_RUTUBE,
    PROVIDER_VK,
    PROVIDER_YOUTUBE,
    VideoUrlError,
    parse_video_url,
)

RUTUBE_ID = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/shorts/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=5s",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ],
)
def test_youtube(url):
    parsed = parse_video_url(url)
    assert parsed.provider == PROVIDER_YOUTUBE
    assert parsed.embed_url == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url", [f"https://rutube.ru/video/{RUTUBE_ID}/", f"https://rutube.ru/play/embed/{RUTUBE_ID}"]
)
def test_rutube(url):
    parsed = parse_video_url(url)
    assert parsed.provider == PROVIDER_RUTUBE
    assert parsed.embed_url == f"https://rutube.ru/play/embed/{RUTUBE_ID}"


@pytest.mark.parametrize(
    "url",
    [
        "https://vk.com/video-12345_67890",
        "https://vkvideo.ru/video-12345_67890",
        "https://vk.com/video_ext.php?oid=-12345&id=67890",
    ],
)
def test_vk(url):
    parsed = parse_video_url(url)
    assert parsed.provider == PROVIDER_VK
    assert parsed.embed_url.startswith("https://vk.com/video_ext.php?oid=-12345&id=67890")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "javascript:alert(1)",
        "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://evil.example/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=short",
        'https://www.youtube.com/watch?v="><script>',
        "https://rutube.ru/video/zzz/",
        "https://vk.com/video_ext.php?oid=abc&id=1",
        "https://vk.com/id123",
    ],
)
def test_rejects_unsupported_or_malicious(url):
    with pytest.raises(VideoUrlError):
        parse_video_url(url)
