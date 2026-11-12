"""Fake `python -m youtube_inbox` for Signals tests and live checks.

Point the plugin's "Repo root" setting at test/fixtures/fake_youtube_inbox.
It loads the REAL collector from ../../../collector/youtube_inbox, replaces
only the network parts (yt-dlp fetch and the AI summary) with fixture data,
then runs the real CLI. Notes and daily pins are written by the real code.

SIGNALS_FAKE_MODE (environment) picks the outcome:
  ok    (default) real ingest with fixture metadata, exit 0
  fail  every video fails, exit 1
  none  behave as if no video id was found, exit 2
  hang  sleep forever (timeout tests)
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REAL_PKG = HERE.parents[3] / "collector" / "youtube_inbox"
META = HERE.parent / "video_meta.json"


def _load_real():
    spec = importlib.util.spec_from_file_location(
        "real_youtube_inbox",
        REAL_PKG / "__init__.py",
        submodule_search_locations=[str(REAL_PKG)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["real_youtube_inbox"] = module
    spec.loader.exec_module(module)
    return importlib.import_module("real_youtube_inbox.ingest"), importlib.import_module(
        "real_youtube_inbox.__main__"
    )


def main() -> int:
    mode = (os.environ.get("SIGNALS_FAKE_MODE") or "ok").strip().lower()
    if mode == "hang":
        while True:
            time.sleep(3600)
    if mode == "none":
        print("No YouTube video id found.", file=sys.stderr)
        return 2
    ingest, cli = _load_real()
    template = json.loads(META.read_text(encoding="utf-8"))

    def fake_fetch(video_id: str) -> dict:
        if mode == "fail":
            raise ingest.FetchError(f"fake collector: forced failure for {video_id}")
        meta = dict(template)
        meta["id"] = video_id
        meta["url"] = f"https://www.youtube.com/watch?v={video_id}"
        meta["thumbnail"] = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        return meta

    def fake_summary(**_kwargs) -> str:
        return template.get("summary") or "Fixture summary."

    ingest.fetch_video = fake_fetch
    ingest.summarize_video = fake_summary
    return cli.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
