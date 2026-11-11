import { ItemView, TFile, WorkspaceLeaf } from "obsidian";
import type SignalsPlugin from "./main";
import { cardFromNote, pillLabel, sortCards, youtubeIdFromDrop, type VideoCard } from "./cards";
import { runIngest } from "./ingest";

export const VIEW_TYPE = "signals";

interface PendingCard {
  key: string;
  id: string;
  title: string;
  status: string;
}

export class SignalsView extends ItemView {
  private plugin: SignalsPlugin;
  private selected = "";
  private statusText = "";
  private pending: PendingCard[] = [];
  private chain: Promise<void> = Promise.resolve();
  private dropArmed = false;

  constructor(leaf: WorkspaceLeaf, plugin: SignalsPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Signals";
  }

  getIcon(): string {
    return "radio";
  }

  async onOpen(): Promise<void> {
    this.contentEl.empty();
    this.contentEl.addClass("signals");
    this.armExternalDrop();
    await this.render();
  }

  async onClose(): Promise<void> {
    this.contentEl.empty();
  }

  private overPane(event: DragEvent): boolean {
    const point = document.elementFromPoint(event.clientX, event.clientY);
    return !!point && this.contentEl.contains(point);
  }

  private armExternalDrop(): void {
    if (this.dropArmed) return;
    this.dropArmed = true;
    const hot = (on: boolean) => {
      this.contentEl.querySelector(".signals-drop")?.classList.toggle("is-hot", on);
    };
    this.registerDomEvent(
      window,
      "dragover",
      (event: DragEvent) => {
        if (!this.overPane(event)) {
          hot(false);
          return;
        }
        event.preventDefault();
        if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
        hot(true);
      },
      true,
    );
    this.registerDomEvent(
      window,
      "drop",
      (event: DragEvent) => {
        if (!this.overPane(event)) return;
        event.preventDefault();
        event.stopPropagation();
        hot(false);
        void this.acceptDrop(event);
      },
      true,
    );
  }

  private async acceptDrop(event: DragEvent): Promise<void> {
    const data = event.dataTransfer;
    const parts: string[] = [];
    for (const type of ["text/uri-list", "text/plain", "text/html", "URL", "text/x-moz-url"]) {
      const value = data?.getData(type);
      if (value) parts.push(value);
    }
    const reads: Promise<string>[] = [];
    if (parts.length === 0 && data?.items) {
      for (const item of Array.from(data.items)) {
        if (item.kind !== "string") continue;
        reads.push(new Promise((resolve) => item.getAsString((value) => resolve(value || ""))));
      }
    }
    if (data?.files) {
      for (const file of Array.from(data.files)) {
        const name = file.name.toLowerCase();
        const textLike = /\.(url|txt|html|htm|webloc|md)$/.test(name) || file.type.startsWith("text/");
        if (!textLike || file.size > 256_000) continue;
        reads.push(file.text());
      }
    }
    const extra = await Promise.all(reads);
    this.enqueue([...parts, ...extra].filter(Boolean).join("\n"));
  }

  private enqueue(raw: string): void {
    const trimmed = raw.trim();
    if (!trimmed) {
      this.statusText = "That drop did not include a URL.";
      void this.render();
      return;
    }
    const id = youtubeIdFromDrop(trimmed) || "pending";
    const key = `${Date.now()}-${id}`;
    this.pending.unshift({
      key,
      id,
      title: id === "pending" ? "Dropped signal" : id,
      status: "capturing",
    });
    this.statusText = "Capturing…";
    void this.render();
    this.chain = this.chain
      .then(() => this.capture(key, trimmed))
      .catch((error: unknown) => {
        this.pending = this.pending.filter((card) => card.key !== key);
        this.statusText = error instanceof Error ? error.message : String(error);
        return this.render();
      });
  }

  private async capture(key: string, raw: string): Promise<void> {
    const items = await runIngest(this.app, this.plugin.settings, raw);
    this.pending = this.pending.filter((card) => card.key !== key);
    const failed = items.filter((item) => item.status === "failed" || item.error);
    if (!items.length) {
      this.statusText = "No YouTube video id found.";
    } else if (failed.length) {
      this.statusText = failed.map((item) => item.error || item.video_id).join(" ");
    } else {
      const titles = items.map((item) => item.title || item.video_id).join(", ");
      this.statusText = `Wrote ${titles} and pinned today's daily note.`;
    }
    await this.render();
  }

  private async loadCards(): Promise<VideoCard[]> {
    const files = this.app.vault
      .getMarkdownFiles()
      .filter((file) => file.path.startsWith("Machine/Reference/YouTube/") && file.extension === "md");
    const cards: VideoCard[] = [];
    for (const file of files) {
      cards.push(cardFromNote(file.path, await this.app.vault.cachedRead(file)));
    }
    return sortCards(cards);
  }

  private renderGen = 0;

  private async render(): Promise<void> {
    const gen = ++this.renderGen;
    const cards = await this.loadCards();
    if (gen !== this.renderGen) return;
    const root = this.contentEl;
    root.empty();
    root.addClass("signals");

    root.createEl("p", { cls: "signals-kicker", text: "Content" });
    const drop = root.createDiv({ cls: "signals-drop" });
    drop.createEl("h2", { text: "Drop signals here" });
    drop.createEl("p", {
      cls: "signals-lede",
      text: "YouTube will not drag the picture. Drag the address bar, or the video title link, onto this pane.",
    });
    drop.createEl("p", {
      cls: "signals-sub",
      text: "Writes Machine/Reference/YouTube/<id> and pins a thumbnail on today's daily note.",
    });

    const row = drop.createDiv({ cls: "signals-row" });
    const input = row.createEl("input", { type: "text", placeholder: "https://www.youtube.com/watch?v=…" });
    const button = row.createEl("button", { text: "Capture", cls: "mod-cta" });
    button.addEventListener("click", () => this.enqueue(input.value));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") this.enqueue(input.value);
    });

    const vault = root.createDiv({ cls: "signals-vault" });
    vault.createEl("p", { cls: "signals-kicker", text: "In the vault" });
    const grid = vault.createDiv({ cls: "signals-grid" });

    for (const card of this.pending) {
      grid.appendChild(this.cardEl(card.id, card.title, "", card.status, null));
    }
    for (const card of cards) {
      grid.appendChild(this.cardEl(card.id, card.title, card.author, card.status, card.path));
    }

    root.createEl("p", { cls: "signals-status", text: this.statusText });
    root.createEl("p", {
      cls: "signals-foot",
      text: "Plugin calls the collector when you drop. No sidecar server.",
    });
    root.createEl("p", { cls: "signals-version", text: `Signals ${this.plugin.manifest.version}` });
  }

  private cardEl(id: string, title: string, author: string, status: string, path: string | null): HTMLElement {
    const card = document.createElement("div");
    card.className = "signals-card" + (this.selected === (path || id) ? " is-selected" : "");
    card.setAttribute("role", "button");
    card.tabIndex = 0;
    if (/^[A-Za-z0-9_-]{11}$/.test(id)) {
      const img = document.createElement("img");
      img.className = "signals-thumb";
      img.alt = "";
      img.src = `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
      card.appendChild(img);
    } else {
      card.createDiv({ cls: "signals-ph" });
    }
    const meta = card.createDiv({ cls: "signals-meta" });
    meta.createDiv({ cls: "signals-title", text: title });
    meta.createDiv({ cls: "signals-author", text: author });
    const pill = meta.createEl("span", { cls: `signals-pill is-${status}`, text: pillLabel(status) });
    pill.setAttr("data-status", status);
    const open = () => {
      this.selected = path || id;
      if (path) {
        const file = this.app.vault.getAbstractFileByPath(path);
        if (file instanceof TFile) {
          void this.app.workspace.getLeaf("tab").openFile(file);
        }
        this.statusText = `Open ${path}`;
      }
      void this.render();
    };
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
    return card;
  }
}
