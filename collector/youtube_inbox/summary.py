from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_MODEL = "gemma4:e4b"
MAX_CHARS = 12000


def summary_model() -> str:
    return (os.environ.get("SIGNALS_SUMMARY_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def build_summary_prompt(*, title: str, author: str, transcript: str, description: str) -> str:
    source = (transcript or "").strip() or (description or "").strip()
    source = source[:MAX_CHARS]
    return (
        "Summarize this YouTube video for a personal notes vault.\n"
        f"Title: {title or 'Untitled'}\n"
        f"Author: {author or 'Unknown'}\n\n"
        "Write 2-4 sentences, then up to 5 bullets of concrete points. "
        "Plain markdown. No heading. No preamble.\n\n"
        f"{source}"
    )


def ollama_complete(prompt: str, *, model: str | None = None) -> str:
    payload = {
        "model": model or summary_model(),
        "stream": False,
        "think": False,
        "keep_alive": "2m",
        "options": {"temperature": 0.3, "num_predict": 500},
        "messages": [
            {"role": "system", "content": "You write short, concrete video summaries."},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama summary failed: {exc}") from exc
    text = ((body.get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError("Ollama returned an empty summary")
    return text


def clean_summary(text: str) -> str:
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\n", "", body)
        body = re.sub(r"\n```$", "", body).strip()
    lines = body.splitlines()
    while lines and lines[0].lstrip().startswith("#"):
        lines.pop(0)
    return "\n".join(lines).strip()


def summarize_video(
    *,
    title: str,
    author: str,
    transcript: str,
    description: str,
    complete=ollama_complete,
) -> str:
    source = (transcript or "").strip() or (description or "").strip()
    if not source:
        return "_No AI summary yet. Nothing to summarize._"
    prompt = build_summary_prompt(
        title=title,
        author=author,
        transcript=transcript,
        description=description,
    )
    cleaned = clean_summary(complete(prompt))
    if not cleaned:
        raise RuntimeError("Ollama returned an empty summary")
    return cleaned
