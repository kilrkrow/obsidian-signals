from __future__ import annotations

import time
from pathlib import Path

from .ingest import ingest_file
from .paths import vault_root

WATCHABLE = {".url", ".txt", ".md", ".html", ".webloc"}


def inbox_dir(vault: Path | None = None) -> Path:
    root = vault or vault_root()
    path = root / "Machine" / "Inbox" / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path


def processed_dir(vault: Path | None = None) -> Path:
    path = inbox_dir(vault) / "_processed"
    path.mkdir(parents=True, exist_ok=True)
    return path


def process_inbox(vault: Path | None = None) -> list[str]:
    folder = inbox_dir(vault)
    done = processed_dir(vault)
    handled: list[str] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in WATCHABLE:
            continue
        if path.name.lower() == "readme.md":
            continue
        batch = ingest_file(path, vault=vault)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        path.rename(done / f"{stamp}-{path.name}")
        handled.append(path.name)
        print(f"processed {path.name}: {[r.video_id for r in batch.results]}")
    return handled


def watch_inbox(poll_seconds: float = 2.0, vault: Path | None = None) -> None:
    print(f"Watching {inbox_dir(vault)}")
    try:
        while True:
            process_inbox(vault)
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\nStopping watch")
