from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COLLECTOR = REPO / "collector"
FAKE = REPO / "test" / "fixtures" / "fake_youtube_inbox"
VID = "dQw4w9WgXcQ"


def run(cwd: Path, *args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwd)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-m", "youtube_inbox", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_real_cli_help() -> None:
    proc = run(COLLECTOR, "--help")
    assert proc.returncode == 0
    for cmd in ("ingest", "serve", "watch", "summarize"):
        assert cmd in proc.stdout


def test_real_cli_uses_signals_vault_env(tmp_path: Path) -> None:
    proc = run(COLLECTOR, "ingest", "no video here", env_extra={"SIGNALS_VAULT": str(tmp_path)})
    assert proc.returncode == 2
    assert f"Vault: {tmp_path.resolve()}" in proc.stderr


def test_fake_collector_writes_note_and_pin(tmp_path: Path) -> None:
    proc = run(FAKE, "ingest", f"https://youtu.be/{VID}", env_extra={"SIGNALS_VAULT": str(tmp_path)})
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout[proc.stdout.index("[") :])
    assert payload[0]["video_id"] == VID
    assert payload[0]["status"] == "ok"
    note = tmp_path / "Machine" / "Reference" / "YouTube" / f"{VID}.md"
    assert note.exists()
    assert "title: Signals fake collector video" in note.read_text(encoding="utf-8")
    dailies = list((tmp_path / "Human" / "Daily").glob("*.md"))
    assert len(dailies) == 1
    assert VID in dailies[0].read_text(encoding="utf-8")


def test_fake_collector_fail_and_none(tmp_path: Path) -> None:
    fail = run(FAKE, "ingest", VID, env_extra={"SIGNALS_VAULT": str(tmp_path), "SIGNALS_FAKE_MODE": "fail"})
    assert fail.returncode == 1
    assert json.loads(fail.stdout[fail.stdout.index("[") :])[0]["status"] == "failed"
    none = run(FAKE, "ingest", VID, env_extra={"SIGNALS_VAULT": str(tmp_path), "SIGNALS_FAKE_MODE": "none"})
    assert none.returncode == 2
