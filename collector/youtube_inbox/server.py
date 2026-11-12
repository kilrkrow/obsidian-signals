from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .ingest import ingest_raw
from .paths import vault_root

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787


def _json_bytes(payload: dict, status: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return status, body, "application/json; charset=utf-8"


class InboxHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print("[%s] %s" % (self.log_date_time_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            html = (STATIC_DIR / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/api/health":
            status, body, ctype = _json_bytes({"ok": True, "vault": str(vault_root())})
            self._send(status, body, ctype)
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/ingest":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length") or "0")
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            status, body, ctype = _json_bytes({"error": "invalid JSON"}, 400)
            self._send(status, body, ctype)
            return
        raw = payload.get("raw") or payload.get("url") or ""
        if not str(raw).strip():
            status, body, ctype = _json_bytes({"error": "empty drop", "results": []}, 400)
            self._send(status, body, ctype)
            return
        batch = ingest_raw(str(raw), vault=vault_root())
        status, body, ctype = _json_bytes(
            {
                "results": [
                    {
                        "video_id": item.video_id,
                        "title": item.title,
                        "author": item.author,
                        "url": item.url,
                        "note_path": item.note_path,
                        "human_daily": item.human_daily,
                        "machine_daily": item.machine_daily,
                        "status": item.status,
                        "error": item.error,
                        "daily_added": item.daily_added,
                    }
                    for item in batch.results
                ]
            }
        )
        self._send(status, body, ctype)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    httpd = ThreadingHTTPServer((host, port), InboxHandler)
    url = f"http://{host}:{port}/"
    print(f"YouTube inbox drop box at {url}")
    print(f"Vault: {vault_root()}")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping drop box")
        httpd.server_close()
