export interface VideoCard {
  id: string;
  title: string;
  author: string;
  status: string;
  collectedAt: string;
  path: string;
}

export function parseFrontmatter(text: string): Record<string, string> {
  if (!text.startsWith("---")) return {};
  const end = text.indexOf("\n---", 3);
  if (end < 0) return {};
  const out: Record<string, string> = {};
  for (const line of text.slice(4, end).split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!match) continue;
    let value = match[2].trim();
    if (value.startsWith('"')) {
      try {
        value = JSON.parse(value) as string;
      } catch {
        /* keep the raw scalar */
      }
    }
    out[match[1]] = value;
  }
  return out;
}

export function cardFromNote(path: string, text: string): VideoCard {
  const meta = parseFrontmatter(text);
  const id = meta.id || path.replace(/^.*\//, "").replace(/\.md$/, "");
  return {
    id,
    title: meta.title || id,
    author: meta.author || "",
    status: meta.collection_status || "ok",
    collectedAt: meta.collected_at || "",
    path,
  };
}

export function sortCards(cards: VideoCard[]): VideoCard[] {
  return [...cards].sort((a, b) => b.collectedAt.localeCompare(a.collectedAt) || a.title.localeCompare(b.title));
}

const ID_RE = /(?:v=|youtu\.be\/|\/shorts\/|\/embed\/|\/vi\/|\/vi_webp\/)([A-Za-z0-9_-]{11})/;

export function youtubeIdFromDrop(raw: string): string | null {
  const match = ID_RE.exec(raw || "");
  return match ? match[1] : null;
}

export function pillLabel(status: string): string {
  if (status === "ok") return "captured";
  if (status === "partial") return "partial";
  if (status === "failed") return "failed";
  if (status === "capturing") return "capturing";
  if (status === "queued") return "queued";
  return status || "captured";
}
