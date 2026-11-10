# Signals

Signals is a desktop-only Obsidian plugin. Drop or paste a YouTube link into
the Signals pane, and it runs the local collector (`python -m youtube_inbox
ingest <url>`). The collector writes one note per video (with its transcript)
and pins a deduplicated thumbnail under `## Captured` in your daily note. Each
link shows as captured, partial, or failed. Signals coordinates the capture
and stays out of playback, transcripts-as-UI, templates, and AI summaries;
other plugins cover those.

> Status: Phase 0 scaffold. The plugin source and collector have not been
> imported yet. Every `TODO(source)` marker below gets filled in from the
> real source when it lands.

## Prerequisites

- Obsidian desktop, version TODO(source: minimum version, from
  `manifest.json` `minAppVersion`). Mobile is not supported
  (`isDesktopOnly: true`).
- Python 3.11 or newer, with this repo's collector available in one of two
  ways:
  - `pip install -e collector/` (recommended), or
  - `collector/` on `PYTHONPATH`.
- Python packages the collector needs: TODO(source: list from the
  collector's real imports, for example in `collector/pyproject.toml`).

## Manual install

1. Build the plugin (`npm ci`, then `npm run build`), or download `main.js`,
   `manifest.json` and `styles.css` from a release.
2. Copy those three files into `<your vault>/.obsidian/plugins/signals/`.
3. In Obsidian, open Settings > Community plugins, then enable **Signals**.
4. Install the collector (see Prerequisites).

### Migrating from the old `shineup-signals` folder

TODO(source: confirm wording after the id rename.) The plugin id is now
`signals`. You can disable the old `shineup-signals` plugin and delete its
folder by hand. Settings do not carry over.

## Settings

TODO(source: list each setting with its default once the source is
imported.) Signals ships no default hotkeys; bind its commands under
Settings > Hotkeys.

## Privacy

Signals and its collector run locally. Signals sends nothing to its own
servers (it has none). The collector contacts YouTube only to fetch data for
the links you submit. TODO(source: confirm every network call the collector
makes.)

## Supported OS

- Windows: primary and tested.
- macOS and Linux: expected to work, untested. Paths and the Python command
  are configurable.

## Development

- Plugin: `npm ci`, `npm run build`, `npm test`.
- Collector: `pip install -e collector/`, then `pytest collector/tests`.
- CI runs both on every push and pull request.

## License

MIT. Copyright (c) 2026 kilrkrow. See [LICENSE](LICENSE).
