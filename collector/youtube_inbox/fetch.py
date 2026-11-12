from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from .parse import is_video_id

WATCH_URL = "https://www.youtube.com/watch?v={id}"
VTT_TAG_RE = re.compile(r"</?c>|<[\d:.]+>|<[^>]+>")
COOKIE_BROWSERS = ("firefox", "edge", "chrome")


class FetchError(RuntimeError):
    pass


def watch_url(video_id: str) -> str:
    return WATCH_URL.format(id=video_id)


def _pick_caption_url(info: dict[str, Any]) -> str | None:
    for bucket_name in ("subtitles", "automatic_captions"):
        bucket = info.get(bucket_name) or {}
        for lang in ("en", "en-US", "en-GB", "en-orig"):
            tracks = bucket.get(lang) or []
            json3 = next((t for t in tracks if t.get("ext") == "json3" and t.get("url")), None)
            if json3:
                return json3["url"]
            any_track = next((t for t in tracks if t.get("url")), None)
            if any_track:
                return any_track["url"]
        for tracks in bucket.values():
            json3 = next((t for t in tracks if t.get("ext") == "json3" and t.get("url")), None)
            if json3:
                return json3["url"]
    return None


def _parse_json3(payload: str) -> str:
    data = json.loads(payload)
    lines: list[str] = []
    current: list[str] = []
    last_t = 0
    for event in data.get("events") or []:
        segs = event.get("segs")
        if not segs:
            continue
        t = int(event.get("tStartMs") or 0)
        piece = "".join(seg.get("utf8", "") for seg in segs)
        piece = piece.replace("\n", " ").strip()
        if not piece:
            continue
        if current and t - last_t > 2500:
            lines.append(" ".join(current).strip())
            current = []
        current.append(piece)
        last_t = t
    if current:
        lines.append(" ".join(current).strip())
    return "\n\n".join(line for line in lines if line)


def _parse_vtt(payload: str) -> str:
    lines: list[str] = []
    current: list[str] = []

    def flush() -> None:
        joined = VTT_TAG_RE.sub("", " ".join(current)).strip()
        joined = re.sub(r"\s+", " ", joined)
        if joined and (not lines or lines[-1] != joined):
            lines.append(joined)
        current.clear()

    for raw in payload.splitlines():
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            flush()
            continue
        if line.isdigit():
            continue
        current.append(line)
    flush()
    return "\n\n".join(lines)


def _http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "signals-youtube-inbox/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _caption_browsers() -> list[str | None]:
    named = (os.environ.get("SIGNALS_YT_COOKIES_BROWSER") or "").strip().lower()
    if named:
        return [named, None]
    return [*COOKIE_BROWSERS, None]


def _parse_caption_payload(payload: str) -> str | None:
    stripped = payload.lstrip()
    if not stripped:
        return None
    if stripped.startswith("{") or stripped.startswith("["):
        text = _parse_json3(payload)
    else:
        text = _parse_vtt(payload)
    return text or None


def _download_transcript_with_ytdlp(video_id: str, yt_dlp: Any) -> str | None:
    url = watch_url(video_id)
    last_error: Exception | None = None
    for browser in _caption_browsers():
        with tempfile.TemporaryDirectory(prefix="signals-subs-") as tmp:
            opts: dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noprogress": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB", "en-orig"],
                "subtitlesformat": "json3/vtt/best",
                "outtmpl": str(Path(tmp) / "%(id)s"),
                "ignore_no_formats_error": True,
            }
            if browser:
                opts["cookiesfrombrowser"] = (browser,)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
            except Exception as exc:
                last_error = exc
                continue
            files = sorted(Path(tmp).glob("*"), key=lambda p: (p.suffix != ".json3", p.name))
            for path in files:
                try:
                    text = _parse_caption_payload(path.read_text(encoding="utf-8", errors="replace"))
                except Exception as exc:
                    last_error = exc
                    continue
                if text:
                    return text
    if last_error:
        raise last_error
    return None


def _transcript_from_info(info: dict[str, Any], *, yt_dlp: Any) -> str | None:
    url = _pick_caption_url(info)
    if url:
        try:
            payload = _http_get(url)
            text = _parse_caption_payload(payload)
            if text:
                return text
        except Exception:
            pass
    return _download_transcript_with_ytdlp(info.get("id") or "", yt_dlp)


def fetch_video(video_id: str) -> dict[str, Any]:
    if not is_video_id(video_id):
        raise FetchError(f"invalid video id: {video_id}")
    try:
        import yt_dlp
    except ImportError as exc:
        raise FetchError("yt-dlp is not installed; pip install -e collector/") from exc

    url = watch_url(video_id)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noprogress": True,
        "extract_flat": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise FetchError(f"yt-dlp failed for {video_id}: {exc}") from exc

    if not info:
        raise FetchError(f"no metadata for {video_id}")

    upload_date = info.get("upload_date") or ""
    published = (
        f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        if len(upload_date) == 8
        else None
    )
    transcript = None
    transcript_error = None
    try:
        transcript = _transcript_from_info(info, yt_dlp=yt_dlp)
    except Exception as exc:
        transcript_error = str(exc)

    chapters = []
    for chapter in info.get("chapters") or []:
        start = chapter.get("start_time")
        title = chapter.get("title")
        if start is None or not title:
            continue
        chapters.append({"start": int(start), "title": str(title)})

    return {
        "id": info.get("id") or video_id,
        "title": info.get("title") or video_id,
        "author": info.get("uploader") or info.get("channel") or "",
        "channel_url": info.get("channel_url") or info.get("uploader_url") or "",
        "url": info.get("webpage_url") or url,
        "published": published,
        "views": info.get("view_count"),
        "duration_seconds": info.get("duration"),
        "description": info.get("description") or "",
        "thumbnail": info.get("thumbnail")
        or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "tags": info.get("tags") or [],
        "chapters": chapters,
        "transcript": transcript,
        "transcript_error": transcript_error,
    }
