from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .notes import capture_block

CAPTURED_HEADING = "## Captured"
HUMAN_TEMPLATE = """---
type: daily
date: {day}
layer: human
---

# {day}

## Focus

## Captured

## Notes
"""
MACHINE_TEMPLATE = """---
type: daily
date: {day}
layer: machine
---

# {day} (machine)

## Captured
"""


def _ensure_captured_section(text: str, heading: str = CAPTURED_HEADING) -> str:
    if heading in text:
        return text
    return text.rstrip() + f"\n\n{heading}\n"


def _split_captured(text: str, heading: str = CAPTURED_HEADING) -> tuple[str, str, str]:
    text = _ensure_captured_section(text, heading)
    pre, rest = text.split(heading, 1)
    match = re.search(r"\n## ", rest)
    if match:
        return pre, rest[: match.start()], rest[match.start() :]
    return pre, rest, ""


def _insert_block(text: str, video_id: str, title: str, heading: str = CAPTURED_HEADING) -> tuple[str, bool]:
    block = capture_block(video_id, title)
    pre, captured, post = _split_captured(text, heading)
    if block in captured:
        return text, False
    kept = [line for line in captured.splitlines() if video_id not in line]
    while kept and kept[0].strip() == "":
        kept.pop(0)
    while kept and kept[-1].strip() == "":
        kept.pop()
    new_captured = "\n\n" + block + "\n"
    if kept:
        new_captured += "\n" + "\n".join(kept) + "\n"
    updated = pre + heading + new_captured
    if post:
        if not updated.endswith("\n"):
            updated += "\n"
        updated += post if post.startswith("\n") else "\n" + post
    elif not updated.endswith("\n"):
        updated += "\n"
    return updated, updated != text


def append_capture(path: Path, *, day: date, video_id: str, title: str, template: str) -> tuple[Path, bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = template.format(day=day.isoformat())
    updated, changed = _insert_block(text, video_id, title)
    if changed or not path.exists():
        path.write_text(updated, encoding="utf-8", newline="\n")
    return path, changed


def add_to_human_daily(vault: Path, day: date, video_id: str, title: str) -> tuple[Path, bool]:
    path = vault / "Human" / "Daily" / f"{day.isoformat()}.md"
    return append_capture(path, day=day, video_id=video_id, title=title, template=HUMAN_TEMPLATE)


def add_to_machine_daily(vault: Path, day: date, video_id: str, title: str) -> tuple[Path, bool]:
    path = vault / "Machine" / "Daily" / f"{day.isoformat()}.md"
    return append_capture(path, day=day, video_id=video_id, title=title, template=MACHINE_TEMPLATE)
