from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
WATCH_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
THUMB_HOST_RE = re.compile(
    r"^(i(?:[0-9]+)?\.ytimg\.com|img\.youtube\.com|ytimg\.googleusercontent\.com)$"
)
PATH_ID_RE = re.compile(
    r"/(?:watch|embed|shorts|live|v|vi|vi_webp)/([A-Za-z0-9_-]{11})(?:[/?]|$)"
)
BARE_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
URL_LINE_RE = re.compile(r"^\s*URL\s*=\s*(\S+)", re.IGNORECASE | re.MULTILINE)


class _HrefSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        for key in ("href", "src", "data-src"):
            value = attr.get(key)
            if value:
                self.urls.append(value)
        srcset = attr.get("srcset")
        if srcset:
            for part in srcset.split(","):
                url = part.strip().split(" ")[0]
                if url:
                    self.urls.append(url)


def is_video_id(value: str) -> bool:
    return bool(VIDEO_ID_RE.match(value or ""))


def video_id_from_url(url: str) -> str | None:
    raw = unquote((url or "").strip().strip("<>").strip("'\""))
    if not raw:
        return None
    if is_video_id(raw):
        return raw
    if raw.startswith("//"):
        raw = "https:" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host_key = host
    else:
        host_key = host

    query = parse_qs(parsed.query)
    if "v" in query and is_video_id(query["v"][0]):
        return query["v"][0]

    if host_key in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
        if is_video_id(candidate):
            return candidate

    path_match = PATH_ID_RE.search(parsed.path)
    if path_match and (host_key in WATCH_HOSTS or THUMB_HOST_RE.match(host_key)):
        return path_match.group(1)

    if THUMB_HOST_RE.match(host_key):
        parts = [p for p in parsed.path.split("/") if p]
        for part in parts:
            if is_video_id(part):
                return part
    return None


def extract_video_ids(*chunks: str | None) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(video_id: str | None) -> None:
        if video_id and video_id not in seen:
            seen.add(video_id)
            found.append(video_id)

    for chunk in chunks:
        if not chunk:
            continue
        text = str(chunk)
        shortcut = URL_LINE_RE.search(text)
        if shortcut:
            add(video_id_from_url(shortcut.group(1)))
        parser = _HrefSrcParser()
        try:
            parser.feed(text)
        except Exception:
            parser.urls = []
        for url in parser.urls:
            add(video_id_from_url(url))
        for url in BARE_URL_RE.findall(text):
            add(video_id_from_url(url))
        add(video_id_from_url(text.strip()))
    return found
