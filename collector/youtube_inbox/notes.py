from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

URL_RE = re.compile(r"https?://[^\s<>\]\)]+")
MY_NOTES_MARK = "## My notes"
SUMMARY_MARK = "## AI summary"
DESCRIPTION_MARK = "## Description"
TRANSCRIPT_MARK = "## Transcript"
VIDEO_REL_DIR = Path("Machine") / "Reference" / "YouTube"


def thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def yaml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return str(value)
    text = str(value)
    if text == "" or text.lower() in {"true", "false", "null", "yes", "no"}:
        return json.dumps(text, ensure_ascii=False)
    if any(ch in text for ch in ":#{}[]&*?|>!%@`'\"\n\t"):
        return json.dumps(text, ensure_ascii=False)
    return text


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_views(views: int | None) -> str:
    if views is None:
        return ""
    return f"{int(views):,}"


def timestamp_link(video_id: str, start: int) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"


def format_clock(start: int) -> str:
    start = int(start)
    hours, rem = divmod(start, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def extract_links(description: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.findall(description or ""):
        url = match.rstrip(".,);")
        if url not in seen:
            seen.add(url)
            found.append(url)
    return found


def existing_my_notes(text: str) -> str:
    if MY_NOTES_MARK not in text:
        return ""
    return text.split(MY_NOTES_MARK, 1)[1].lstrip("\n")


def section_body(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    rest = text[start + len(heading) :]
    next_heading = rest.find("\n## ")
    body = rest if next_heading < 0 else rest[:next_heading]
    return body.strip()


def transcript_box(transcript: str) -> str:
    safe = (
        transcript.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    frame = (
        "max-height:16rem;overflow:auto;"
        "border:1px solid var(--background-modifier-border);"
        "border-radius:8px;background:var(--background-primary);"
    )
    pre = "margin:0;padding:12px 14px;white-space:pre-wrap;background:transparent;border:0;"
    return (
        f'<div class="yt-transcript-box" style="{frame}">\n'
        f'<pre style="{pre}">\n'
        f"{safe}\n"
        "</pre>\n"
        "</div>"
    )


def upsert_summary(text: str, summary: str) -> str:
    block = f"{SUMMARY_MARK}\n\n{summary.strip()}\n\n"
    if SUMMARY_MARK in text:
        start = text.find(SUMMARY_MARK)
        rest = text[start + len(SUMMARY_MARK) :]
        next_heading = rest.find("\n## ")
        end = len(text) if next_heading < 0 else start + len(SUMMARY_MARK) + next_heading + 1
        return text[:start] + block + text[end:].lstrip("\n")
    desc = text.find(DESCRIPTION_MARK)
    if desc < 0:
        return text.rstrip() + "\n\n" + block
    return text[:desc] + block + text[desc:]


def plain_transcript(body: str) -> str:
    if "yt-transcript-box" not in body:
        return body.strip()
    text = re.sub(r"<[^>]+>", " ", body)
    return (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .strip()
    )


def box_existing_transcript(text: str) -> str:
    start = text.find(TRANSCRIPT_MARK)
    end = text.find(MY_NOTES_MARK)
    if start < 0 or end < 0 or start > end:
        return text
    body = text[start + len(TRANSCRIPT_MARK) : end].strip()
    if not body or "yt-transcript-box" in body or body.startswith("_Transcript"):
        return text
    boxed = f"{TRANSCRIPT_MARK}\n\n{transcript_box(body)}\n\n"
    return text[:start] + boxed + text[end:]


def render_video_note(meta: dict[str, Any], *, collected_at: datetime, my_notes: str = "") -> str:
    video_id = meta["id"]
    status = "ok" if meta.get("transcript") else "partial"
    views = meta.get("views")
    duration = meta.get("duration_seconds")
    fields = [
        ("type", "youtube"),
        ("id", video_id),
        ("title", meta.get("title") or ""),
        ("author", meta.get("author") or ""),
        ("channel_url", meta.get("channel_url") or ""),
        ("url", meta.get("url") or ""),
        ("published", meta.get("published") or ""),
        ("views", views if views is not None else ""),
        ("duration_seconds", duration if duration is not None else ""),
        ("thumbnail", meta.get("thumbnail") or ""),
        ("collected_at", collected_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("collection_status", status),
        ("source", "youtube-inbox"),
    ]
    front = "---\n" + "\n".join(f"{k}: {yaml_scalar(v)}" for k, v in fields if v != "") + "\n---\n"
    title = meta.get("title") or video_id
    thumb = meta.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    author = meta.get("author") or ""
    author_line = author
    if meta.get("channel_url"):
        author_line = f"[{author}]({meta['channel_url']})" if author else meta["channel_url"]

    lines = [
        front,
        f"# {title}",
        "",
        f"![thumbnail]({thumb})",
        "",
        f"- **Author:** {author_line}" if author_line else "- **Author:**",
        f"- **URL:** {meta.get('url')}",
        f"- **Published:** {meta.get('published') or ''}",
        f"- **Views:** {format_views(views) if views is not None else ''}",
        f"- **Duration:** {format_duration(duration) if duration is not None else ''}",
        "",
        SUMMARY_MARK,
        "",
        (meta.get("summary") or "").strip() or "_No AI summary yet._",
        "",
        DESCRIPTION_MARK,
        "",
        (meta.get("description") or "").strip() or "_No description._",
        "",
        "## Links",
        "",
    ]
    links = extract_links(meta.get("description") or "")
    if links:
        lines.extend(f"- <{url}>" for url in links)
    else:
        lines.append("_No hyperlinks in the description._")
    lines.append("")
    lines.append("## Chapters")
    lines.append("")
    chapters = meta.get("chapters") or []
    if chapters:
        for chapter in chapters:
            clock = format_clock(chapter["start"])
            href = timestamp_link(video_id, chapter["start"])
            lines.append(f"- [{clock} {chapter['title']}]({href})")
    else:
        lines.append("_No chapters._")
    lines.append("")
    lines.append(TRANSCRIPT_MARK)
    lines.append("")
    transcript = (meta.get("transcript") or "").strip()
    if transcript:
        lines.append(transcript_box(transcript))
    else:
        err = meta.get("transcript_error")
        if err:
            lines.append(f"_Transcript unavailable: {err}_")
        else:
            lines.append("_Transcript unavailable._")
    lines.append("")
    lines.append(MY_NOTES_MARK)
    lines.append("")
    lines.append(my_notes.strip() if my_notes.strip() else "_Add notes here. Re-ingest preserves this section._")
    lines.append("")
    return "\n".join(lines)


def video_note_path(vault: Path, video_id: str) -> Path:
    return vault / VIDEO_REL_DIR / f"{video_id}.md"


def wiki_link(video_id: str, title: str) -> str:
    safe_title = (title or video_id).replace("|", "-").replace("]]", "")
    return f"[[{VIDEO_REL_DIR.as_posix()}/{video_id}|{safe_title}]]"


def capture_block(video_id: str, title: str) -> str:
    """Daily-note insert: clickable thumbnail plus a wiki-link for backlinks."""
    safe_title = (title or video_id).replace("|", "-").replace("]", "")
    return (
        f"[![{safe_title}]({thumbnail_url(video_id)})]({watch_url(video_id)})\n"
        f"{wiki_link(video_id, title)}"
    )


def frontmatter_scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}: (.*)$", text)
    if not match:
        return ""
    raw = match.group(1).strip()
    if raw.startswith('"'):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip('"')
        return loaded if isinstance(loaded, str) else raw
    return raw


def summary_is_missing(text: str) -> bool:
    body = section_body(text, SUMMARY_MARK)
    return not body or body.startswith("_No AI summary")


def usable_transcript(text: str) -> str:
    plain = plain_transcript(section_body(text, TRANSCRIPT_MARK))
    if plain.startswith("_Transcript"):
        return ""
    return plain


def refresh_video_note(path: Path, *, complete: Callable[[str], str] | None = None) -> str:
    """Fill a missing AI summary and box the transcript. Does not fetch YouTube."""
    from .summary import ollama_complete, summarize_video

    original = path.read_text(encoding="utf-8")
    text = original
    status = "unchanged"
    if summary_is_missing(text):
        try:
            summary = summarize_video(
                title=frontmatter_scalar(text, "title"),
                author=frontmatter_scalar(text, "author"),
                transcript=usable_transcript(text),
                description=section_body(text, DESCRIPTION_MARK),
                complete=complete or ollama_complete,
            )
            status = "summarized"
        except Exception:
            summary = "_No AI summary yet._"
            status = "failed"
        text = upsert_summary(text, summary)
    boxed = box_existing_transcript(text)
    if boxed != text and status == "unchanged":
        status = "boxed"
    text = boxed
    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
    return status


def refresh_youtube_notes(
    vault: Path,
    video_ids: list[str] | None = None,
    *,
    complete: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    folder = vault / VIDEO_REL_DIR
    if video_ids:
        paths = [video_note_path(vault, video_id) for video_id in video_ids]
    else:
        paths = sorted(folder.glob("*.md")) if folder.exists() else []
    results: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            results.append({"video_id": path.stem, "status": "missing"})
            continue
        print(f"summarize {path.stem}", file=sys.stderr, flush=True)
        status = refresh_video_note(path, complete=complete)
        print(f"summarize {path.stem} {status}", file=sys.stderr, flush=True)
        results.append({"video_id": path.stem, "status": status})
    return results


def write_video_note(vault: Path, meta: dict[str, Any], collected_at: datetime) -> Path:
    path = video_note_path(vault, meta["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    body = render_video_note(
        meta,
        collected_at=collected_at,
        my_notes=existing_my_notes(previous),
    )
    path.write_text(body, encoding="utf-8", newline="\n")
    return path
