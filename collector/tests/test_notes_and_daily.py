from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from youtube_inbox.daily import add_to_human_daily, add_to_machine_daily
from youtube_inbox.notes import (
    existing_my_notes,
    render_video_note,
    video_note_path,
    write_video_note,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "video_meta.json"
COLLECTED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def load_meta() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_render_frontmatter_and_sections() -> None:
    meta = load_meta()
    text = render_video_note(meta, collected_at=COLLECTED)
    assert text.startswith("---\ntype: youtube\nid: fixture0001\n")
    assert 'title: "Fixture: a test video"' in text
    assert 'collected_at: "2026-01-02T03:04:05Z"' in text
    assert "collection_status: ok" in text
    for heading in ("## AI summary", "## Description", "## Links", "## Chapters", "## Transcript", "## My notes"):
        assert heading in text
    assert "- <https://example.com/one>" in text
    assert "[00:00 Intro](https://www.youtube.com/watch?v=fixture0001&t=0s)" in text
    assert "[01:30 Main part](https://www.youtube.com/watch?v=fixture0001&t=90s)" in text
    assert "yt-transcript-box" in text
    assert "a &lt;b&gt; c" in text


def test_partial_without_transcript() -> None:
    meta = load_meta()
    meta["transcript"] = None
    meta["transcript_error"] = "captions disabled"
    text = render_video_note(meta, collected_at=COLLECTED)
    assert "collection_status: partial" in text
    assert "_Transcript unavailable: captions disabled_" in text


def test_write_preserves_my_notes(tmp_path: Path) -> None:
    meta = load_meta()
    path = write_video_note(tmp_path, meta, COLLECTED)
    assert path == video_note_path(tmp_path, "fixture0001")
    assert path.as_posix().endswith("Machine/Reference/YouTube/fixture0001.md")
    edited = path.read_text(encoding="utf-8").replace(
        "_Add notes here. Re-ingest preserves this section._", "My own thoughts."
    )
    path.write_text(edited, encoding="utf-8")
    assert existing_my_notes(edited).strip() == "My own thoughts."
    write_video_note(tmp_path, meta, COLLECTED)
    assert "My own thoughts." in path.read_text(encoding="utf-8")


def test_daily_pin_is_created_and_deduped(tmp_path: Path) -> None:
    day = date(2026, 1, 2)
    path, added = add_to_human_daily(tmp_path, day, "fixture0001", "Fixture video")
    assert added
    assert path.as_posix().endswith("Human/Daily/2026-01-02.md")
    first = path.read_text(encoding="utf-8")
    assert "## Captured" in first
    assert "fixture0001" in first
    _, added_again = add_to_human_daily(tmp_path, day, "fixture0001", "Fixture video")
    assert not added_again
    assert path.read_text(encoding="utf-8") == first


def test_daily_newest_pin_first(tmp_path: Path) -> None:
    day = date(2026, 1, 2)
    add_to_machine_daily(tmp_path, day, "aaaaaaaaaaa", "First")
    path, _ = add_to_machine_daily(tmp_path, day, "bbbbbbbbbbb", "Second")
    text = path.read_text(encoding="utf-8")
    assert "layer: machine" in text
    assert text.index("bbbbbbbbbbb") < text.index("aaaaaaaaaaa")
