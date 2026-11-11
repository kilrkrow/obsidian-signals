import type { App } from "obsidian";
import { spawn } from "child_process";
import { existsSync } from "fs";
import { dirname, join } from "path";

export interface IngestItem {
  video_id: string;
  title: string;
  status: string;
  note_path: string;
  error: string | null;
}

export interface SignalsSettings {
  pythonPath: string;
  cookiesBrowser: string;
  repoRoot: string;
}

export const DEFAULT_SETTINGS: SignalsSettings = {
  pythonPath: "",
  cookiesBrowser: "firefox",
  repoRoot: "",
};

export function vaultBasePath(app: App): string {
  const adapter = app.vault.adapter as { getBasePath?: () => string };
  if (!adapter.getBasePath) {
    throw new Error("Signals needs the Obsidian desktop app.");
  }
  return adapter.getBasePath();
}

export function resolveRepo(vaultPath: string, configured: string): string {
  return configured.trim() || dirname(vaultPath);
}

export function resolvePython(repo: string, configured: string): string {
  const explicit = configured.trim();
  if (explicit) return explicit;
  const win = join(repo, ".venv", "Scripts", "python.exe");
  if (existsSync(win)) return win;
  const unix = join(repo, ".venv", "bin", "python");
  if (existsSync(unix)) return unix;
  return "python";
}

export function runIngest(app: App, settings: SignalsSettings, raw: string): Promise<IngestItem[]> {
  const vaultPath = vaultBasePath(app);
  const repo = resolveRepo(vaultPath, settings.repoRoot);
  const python = resolvePython(repo, settings.pythonPath);
  const browser = settings.cookiesBrowser.trim() || "firefox";

  return new Promise((resolve, reject) => {
    const child = spawn(python, ["-m", "youtube_inbox", "ingest", raw], {
      cwd: repo,
      windowsHide: true,
      env: {
        ...process.env,
        SIGNALS_VAULT: vaultPath,
        SIGNALS_YT_COOKIES_BROWSER: browser,
        PYTHONIOENCODING: "utf-8",
      },
    });
    let out = "";
    let err = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      out += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      err += chunk;
    });
    child.on("error", (error) => {
      reject(error);
    });
    child.on("close", (code) => {
      const start = out.indexOf("[");
      const end = out.lastIndexOf("]");
      if (start >= 0 && end > start) {
        try {
          resolve(JSON.parse(out.slice(start, end + 1)) as IngestItem[]);
          return;
        } catch {
          /* fall through */
        }
      }
      const detail = (err || out || `ingest exited ${code}`).trim();
      reject(new Error(detail));
    });
  });
}
