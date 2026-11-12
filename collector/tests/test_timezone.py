from __future__ import annotations

from datetime import datetime, timezone

from youtube_inbox.ingest import local_today
from youtube_inbox.paths import to_local

# 2026-01-01 20:00 UTC is already 2026-01-02 in Tokyo (UTC+9) and still
# 2026-01-01 in Honolulu (UTC-10, no DST).
MOMENT = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)


def test_signals_tz_override(monkeypatch) -> None:
    monkeypatch.setenv("SIGNALS_TZ", "Asia/Tokyo")
    assert to_local(MOMENT).date().isoformat() == "2026-01-02"
    assert local_today(MOMENT).utcoffset().total_seconds() == 9 * 3600
    monkeypatch.setenv("SIGNALS_TZ", "Pacific/Honolulu")
    assert to_local(MOMENT).date().isoformat() == "2026-01-01"


def test_default_is_system_local_zone(monkeypatch) -> None:
    monkeypatch.delenv("SIGNALS_TZ", raising=False)
    expected = MOMENT.astimezone()
    got = to_local(MOMENT)
    assert got == expected
    assert got.utcoffset() == expected.utcoffset()
    assert to_local().tzinfo is not None


def test_blank_override_falls_back_to_system(monkeypatch) -> None:
    monkeypatch.setenv("SIGNALS_TZ", "  ")
    assert to_local(MOMENT).utcoffset() == MOMENT.astimezone().utcoffset()
