"""Video link parsing: VK Видео / Rutube / YouTube -> embed URL (MVP, ARCHITECTURE §2)."""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

PROVIDER_VK = "vk"
PROVIDER_RUTUBE = "rutube"
PROVIDER_YOUTUBE = "youtube"

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_RUTUBE_ID = re.compile(r"^[0-9a-f]{32}$")
_VK_VIDEO = re.compile(r"^/video(-?\d+)_(\d+)/?$")


class VideoUrlError(ValueError):
    """The URL is not a supported video link."""


@dataclass(frozen=True)
class ParsedVideo:
    provider: str
    embed_url: str


def _host(url: str) -> tuple[str, str, dict]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise VideoUrlError("Ссылка должна начинаться с http:// или https://")
    host = parsed.hostname.lower().removeprefix("www.").removeprefix("m.")
    return host, parsed.path, parse_qs(parsed.query)


def parse_video_url(url: str) -> ParsedVideo:
    """Detect the provider and build a safe embed URL. Raises VideoUrlError."""
    host, path, query = _host(url)

    if host in ("youtube.com", "youtube-nocookie.com", "youtu.be"):
        video_id = None
        if host == "youtu.be":
            video_id = path.strip("/").split("/")[0]
        elif path == "/watch":
            video_id = (query.get("v") or [None])[0]
        else:
            match = re.match(r"^/(?:embed|shorts|live)/([^/?]+)", path)
            video_id = match.group(1) if match else None
        if not video_id or not _YOUTUBE_ID.match(video_id):
            raise VideoUrlError("Не удалось распознать ссылку на YouTube")
        return ParsedVideo(PROVIDER_YOUTUBE, f"https://www.youtube-nocookie.com/embed/{video_id}")

    if host == "rutube.ru":
        match = re.match(r"^/(?:video|play/embed)/([0-9a-f]{32})/?$", path)
        if not match or not _RUTUBE_ID.match(match.group(1)):
            raise VideoUrlError("Не удалось распознать ссылку на Rutube")
        return ParsedVideo(PROVIDER_RUTUBE, f"https://rutube.ru/play/embed/{match.group(1)}")

    if host in ("vk.com", "vkvideo.ru", "vk.ru"):
        match = _VK_VIDEO.match(path)
        if match:
            oid, vid = match.groups()
            return ParsedVideo(PROVIDER_VK, f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=2")
        if path == "/video_ext.php" and query.get("oid") and query.get("id"):
            oid, vid = query["oid"][0], query["id"][0]
            if re.fullmatch(r"-?\d+", oid) and re.fullmatch(r"\d+", vid):
                extra = (
                    f"&hash={query['hash'][0]}"
                    if re.fullmatch(r"\w+", (query.get("hash") or [""])[0])
                    else ""
                )
                return ParsedVideo(
                    PROVIDER_VK, f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=2{extra}"
                )
        raise VideoUrlError("Не удалось распознать ссылку на VK Видео")

    raise VideoUrlError("Поддерживаются только VK Видео, Rutube и YouTube")
