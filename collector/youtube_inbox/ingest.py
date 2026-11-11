from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from .daily import add_to_human_daily, add_to_machine_daily
from .fetch import FetchError, fetch_video
from .notes import section_body, video_note_path, wiki_link, write_video_note
from .summary import summarize_video
from .parse import extract_video_ids
from .paths import LOCAL_TZ, vault_root


@dataclass
class IngestResult:
    video_id: str
    title: str = ""
    author: str = ""
    url: str = ""
    note_path: str = ""
    human_daily: str = ""
    machine_daily: str = ""
    run_path: str = ""
    created_note: bool = False
    daily_added: bool = False
    status: str = "ok"
    error: str | None = None


@dataclass
class IngestBatch:
    results: list[IngestResult] = field(default_factory=list)

    @property
    def video_ids(self) -> list[str]:
        return [r.video_id for r in self.results]


def local_today(now: datetime | None = None) -> datetime:
    tz = ZoneInfo(LOCAL_TZ)
    current = now.astimezone(tz) if now else datetime.now(tz)
    return current


def write_run_record(
    vault: Path,
    *,
    result: IngestResult,
    started: datetime,
    finished: datetime,
) -> Path:
    local_day = started.astimezone(ZoneInfo(LOCAL_TZ)).date().isoformat()
    stamp = started.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = uuid4().hex[:8]
    folder = vault / "Machine" / "Runs" / local_day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}-youtube-inbox-{result.video_id}-{run_id}.md"
    body = f"""---
type: run
id: {run_id}
project: signals
agent: youtube-inbox
started_at: {started.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
finished_at: {finished.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: {result.status}
---

# YouTube inbox {result.video_id}

- Video: {wiki_link(result.video_id, result.title or result.video_id)}
- Note: `{result.note_path}`
- Human daily: `{result.human_daily}`
- Machine daily: `{result.machine_daily}`
- Error: {result.error or "_none_"}
"""
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def ingest_video_id(video_id: str, *, vault: Path | None = None) -> IngestResult:
    root = vault or vault_root()
    started = datetime.now(timezone.utc)
    result = IngestResult(video_id=video_id)
    try:
        meta = fetch_video(video_id)
        previous = ""
        previous_path = video_note_path(root, video_id)
        if previous_path.exists():
            previous = previous_path.read_text(encoding="utf-8")
        try:
            meta["summary"] = summarize_video(
                title=meta.get("title") or "",
                author=meta.get("author") or "",
                transcript=meta.get("transcript") or "",
                description=meta.get("description") or "",
            )
        except Exception:
            meta["summary"] = section_body(previous, "## AI summary")
        result.title = meta.get("title") or video_id
        result.author = meta.get("author") or ""
        result.url = meta.get("url") or ""
        note_path = write_video_note(root, meta, started)
        result.created_note = True
        result.note_path = str(note_path)
        result.status = "partial" if not meta.get("transcript") else "ok"
        day = local_today(started).date()
        human_path, human_added = add_to_human_daily(root, day, video_id, result.title)
        machine_path, machine_added = add_to_machine_daily(root, day, video_id, result.title)
        result.human_daily = str(human_path)
        result.machine_daily = str(machine_path)
        result.daily_added = human_added or machine_added
    except FetchError as exc:
        result.status = "failed"
        result.error = str(exc)
    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)
    finished = datetime.now(timezone.utc)
    try:
        run_path = write_run_record(root, result=result, started=started, finished=finished)
        result.run_path = str(run_path)
    except Exception:
        pass
    return result


def ingest_raw(raw: str, *, vault: Path | None = None) -> IngestBatch:
    ids = extract_video_ids(raw)
    batch = IngestBatch()
    if not ids:
        return batch
    for video_id in ids:
        batch.results.append(ingest_video_id(video_id, vault=vault))
    return batch


def ingest_file(path: Path, *, vault: Path | None = None) -> IngestBatch:
    text = path.read_text(encoding="utf-8", errors="replace")
    return ingest_raw(text, vault=vault)
