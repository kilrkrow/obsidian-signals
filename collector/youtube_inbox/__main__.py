from __future__ import annotations

import argparse
import json
import sys

from .ingest import ingest_raw
from .notes import refresh_youtube_notes
from .paths import vault_root
from .server import DEFAULT_HOST, DEFAULT_PORT, serve
from .watch import process_inbox, watch_inbox


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="youtube_inbox", description="YouTube capture for an Obsidian vault")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest_p = sub.add_parser("ingest", help="Capture one or more videos from URL/text")
    ingest_p.add_argument("raw", nargs="+", help="YouTube URL, thumbnail URL, or text containing either")

    serve_p = sub.add_parser("serve", help="Open the local thumbnail drop box")
    serve_p.add_argument("--host", default=DEFAULT_HOST)
    serve_p.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_p.add_argument("--no-browser", action="store_true")

    watch_p = sub.add_parser("watch", help="Process files dropped in Machine/Inbox/youtube")
    watch_p.add_argument("--once", action="store_true")
    watch_p.add_argument("--poll", type=float, default=2.0)

    sum_p = sub.add_parser("summarize", help="Add a missing AI summary and box the transcript")
    sum_p.add_argument("video_id", nargs="*", help="Video ids to refresh. Default: every YouTube note")

    args = parser.parse_args(argv)
    print(f"Vault: {vault_root()}", file=sys.stderr)

    if args.cmd == "ingest":
        batch = ingest_raw("\n".join(args.raw))
        if not batch.results:
            print("No YouTube video id found.", file=sys.stderr)
            return 2
        payload = [
            {
                "video_id": item.video_id,
                "title": item.title,
                "status": item.status,
                "note_path": item.note_path,
                "human_daily": item.human_daily,
                "error": item.error,
            }
            for item in batch.results
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if all(item.status != "failed" for item in batch.results) else 1

    if args.cmd == "serve":
        serve(host=args.host, port=args.port, open_browser=not args.no_browser)
        return 0

    if args.cmd == "summarize":
        results = refresh_youtube_notes(vault_root(), list(args.video_id) or None)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0 if all(item["status"] != "failed" for item in results) else 1

    if args.cmd == "watch":
        if args.once:
            process_inbox()
            return 0
        watch_inbox(poll_seconds=args.poll)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
