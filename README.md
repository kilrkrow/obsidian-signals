# Signals

Signals is a desktop-only Obsidian plugin. Drop or paste a YouTube link into
the Signals pane, and it runs the local collector (`python -m youtube_inbox
ingest <url>`). The collector writes one note per video (metadata,
description, links, chapters and transcript) and pins a deduplicated
thumbnail under `## Captured` in today's daily note. Each drop shows as
captured, partial (no transcript), or failed. Signals coordinates the
capture; playback, transcript panels and metadata templates are left to other
plugins.

## Prerequisites

- Obsidian desktop 1.7.0 or newer (`minAppVersion`). Mobile is not supported
  (`isDesktopOnly: true`).
- Python 3.11 or newer, with this repo's collector available in one of two
  ways:
  - `pip install -e collector/` (recommended), or
  - `collector/` on `PYTHONPATH`, or set the plugin's **Repo root** setting
    to the `collector/` folder (the plugin runs Python from that folder).
- Python packages (installed by `pip install -e collector/`):
  - `yt-dlp` (video metadata and captions)
  - `tzdata` (time zone data, needed on Windows)

## Manual install

1. Build the plugin (`npm ci`, then `npm run build`), or download `main.js`,
   `manifest.json` and `styles.css` from a release.
2. Copy those three files into `<your vault>/.obsidian/plugins/signals/`.
3. In Obsidian, open Settings > Community plugins, then enable **Signals**.
4. Install the collector (see Prerequisites).
5. Open the pane with the radio ribbon icon or the command
   **Signals: Open signals**.

Developers can set `SIGNALS_DEV_VAULT` to a vault folder before
`npm run build`; the build then copies the three files into
`<SIGNALS_DEV_VAULT>/.obsidian/plugins/signals/`. Without it, the build only
writes `main.js` in the repo.

### Migrating from the old `shineup-signals` folder

The plugin id is now `signals`. You can disable the old `shineup-signals`
plugin and delete its folder by hand. Settings do not carry over.

## Settings

| Setting | Default | What it does |
|---|---|---|
| Python | blank | Collector interpreter. Blank uses `<repo root>/.venv/Scripts/python.exe` or `<repo root>/.venv/bin/python` if present, else `python`. |
| Caption browser | `firefox` | Browser whose YouTube cookies yt-dlp may use to fetch captions when anonymous captions are rate-limited. |
| Repo root | blank | Folder the collector runs from (it must contain `youtube_inbox`, for example this repo's `collector/`). Blank uses the parent folder of the vault. |

Signals ships no default hotkeys; bind its command under Settings > Hotkeys.
The settings tab and the pane show the plugin version (`Signals <version>`).

### Collector environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SIGNALS_VAULT` | `<collector>/vault` | Vault to write into. The plugin always sets it to the open vault. |
| `SIGNALS_YT_COOKIES_BROWSER` | tries `firefox`, `edge`, `chrome` | Browser cookies for captions. The plugin sets it from **Caption browser**. |
| `SIGNALS_TZ` | `America/Los_Angeles` | Time zone used to pick "today" for daily notes and run records. |
| `SIGNALS_SUMMARY_MODEL` | `gemma4:e4b` | Local Ollama model for the optional summary (see below). |

### What the collector writes (relative to the vault)

- `Machine/Reference/YouTube/<video id>.md`: the video note. Re-ingesting
  keeps your `## My notes` section.
- `Human/Daily/<YYYY-MM-DD>.md` and `Machine/Daily/<YYYY-MM-DD>.md`: a
  thumbnail pin under `## Captured` (one per video, newest first).
- `Machine/Runs/<YYYY-MM-DD>/...-youtube-inbox-<id>-<run>.md`: a run record.

## Privacy

- Signals has no server. The plugin only starts the local collector and
  shows thumbnails from `i.ytimg.com`.
- The collector contacts YouTube (through `yt-dlp`) for the links you submit:
  video metadata and captions.
- To get captions when anonymous requests are blocked, `yt-dlp` can read
  YouTube cookies from a local browser profile (Caption browser setting).
  The cookies stay on your machine and are only sent to YouTube.
- The collector tries a summary through a local Ollama server at
  `127.0.0.1:11434`. If none is running, the note says "No AI summary yet".
  Nothing is sent to a cloud AI service.
- Notes are written only inside your vault.

## Supported OS

- Windows: primary and tested.
- macOS and Linux: expected to work, untested. Paths and the Python command
  are configurable.

## Development

- Plugin: `npm ci`, `npm run build`, `npm test`.
- Collector: `pip install -e collector/`, then `pytest collector/tests`.
- `test/fixtures/fake_youtube_inbox/` is a fake collector for tests and live
  checks: point **Repo root** at it, and it runs the real collector code with
  fixture metadata instead of contacting YouTube. `SIGNALS_FAKE_MODE`
  (`ok`, `fail`, `none`, `hang`) picks the outcome.
- CI runs both on every push and pull request.

## License

MIT. Copyright (c) 2026 kilrkrow. See [LICENSE](LICENSE).
