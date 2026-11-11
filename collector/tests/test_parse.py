from __future__ import annotations

import pytest

from youtube_inbox.parse import extract_video_ids, is_video_id, video_id_from_url

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "raw",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?v={VID}&t=90s",
        f"https://m.youtube.com/watch?v={VID}&list=PL123&index=2",
        f"https://www.youtube.com/watch?v={VID}&si=abcdef",
        f"https://youtu.be/{VID}",
        f"https://youtu.be/{VID}?si=abcdef",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"https://www.youtube.com/live/{VID}",
        f"https://i.ytimg.com/vi/{VID}/hqdefault.jpg",
        f"https://i.ytimg.com/vi_webp/{VID}/maxresdefault.webp",
        f"//www.youtube.com/watch?v={VID}",
        VID,
    ],
)
def test_video_id_from_url_forms(raw: str) -> None:
    assert video_id_from_url(raw) == VID


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "https://example.com/watch?x=1",
        "https://www.youtube.com/@somechannel",
        "https://www.youtube.com/results?search_query=test",
        "not a url",
        "tooshort",
    ],
)
def test_video_id_from_url_rejects(raw: str) -> None:
    assert video_id_from_url(raw) is None


def test_is_video_id() -> None:
    assert is_video_id(VID)
    assert not is_video_id(VID + "x")
    assert not is_video_id("bad id char")


def test_extract_from_html_drop_dedupes_in_order() -> None:
    html = (
        f'<a href="https://www.youtube.com/watch?v={VID}">'
        f'<img src="https://i.ytimg.com/vi/{VID}/hqdefault.jpg"></a>'
        '<a href="https://youtu.be/aaaaaaaaaaa">second</a>'
    )
    assert extract_video_ids(html) == [VID, "aaaaaaaaaaa"]


def test_extract_from_windows_url_shortcut() -> None:
    shortcut = f"[InternetShortcut]\nURL=https://www.youtube.com/watch?v={VID}\n"
    assert extract_video_ids(shortcut) == [VID]


def test_extract_from_plain_text_with_noise() -> None:
    text = f"look at this (https://youtu.be/{VID}) and https://example.com/x"
    assert extract_video_ids(text) == [VID]


def test_extract_nothing() -> None:
    assert extract_video_ids("no links here", None, "") == []
