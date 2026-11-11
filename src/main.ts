import { Plugin, PluginSettingTab, Setting, WorkspaceLeaf } from "obsidian";
import { DEFAULT_SETTINGS, type SignalsSettings } from "./ingest";
import { SignalsView, VIEW_TYPE } from "./view";

export default class SignalsPlugin extends Plugin {
  settings: SignalsSettings = { ...DEFAULT_SETTINGS };

  async onload(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    this.registerView(VIEW_TYPE, (leaf: WorkspaceLeaf) => new SignalsView(leaf, this));
    this.addRibbonIcon("radio", "Signals", () => {
      void this.activate();
    });
    this.addCommand({
      id: "open-signals",
      name: "Open signals",
      callback: () => {
        void this.activate();
      },
    });
    this.addSettingTab(new SignalsSettingTab(this.app, this));
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE);
  }

  async activate(): Promise<void> {
    const existing = this.app.workspace.getLeavesOfType(VIEW_TYPE);
    if (existing.length) {
      this.app.workspace.revealLeaf(existing[0]);
      return;
    }
    const leaf = this.app.workspace.getLeaf("tab");
    await leaf.setViewState({ type: VIEW_TYPE, active: true });
    this.app.workspace.revealLeaf(leaf);
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}

class SignalsSettingTab extends PluginSettingTab {
  plugin: SignalsPlugin;

  constructor(app: PluginSettingTab["app"], plugin: SignalsPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl)
      .setName("Python")
      .setDesc("Collector interpreter. Blank uses the repo .venv.")
      .addText((text) =>
        text.setPlaceholder(".venv\\Scripts\\python.exe").setValue(this.plugin.settings.pythonPath).onChange(async (value) => {
          this.plugin.settings.pythonPath = value.trim();
          await this.plugin.saveSettings();
        }),
      );
    new Setting(containerEl)
      .setName("Caption browser")
      .setDesc("Browser whose YouTube cookies fill transcripts when anonymous captions are rate-limited.")
      .addText((text) =>
        text.setPlaceholder("firefox").setValue(this.plugin.settings.cookiesBrowser).onChange(async (value) => {
          this.plugin.settings.cookiesBrowser = value.trim();
          await this.plugin.saveSettings();
        }),
      );
    new Setting(containerEl)
      .setName("Repo root")
      .setDesc("Folder that contains youtube_inbox. Blank uses the parent of this vault.")
      .addText((text) =>
        text.setPlaceholder("path/to/obsidian-signals/collector").setValue(this.plugin.settings.repoRoot).onChange(async (value) => {
          this.plugin.settings.repoRoot = value.trim();
          await this.plugin.saveSettings();
        }),
      );
    containerEl.createEl("p", { cls: "signals-version", text: `Signals ${this.plugin.manifest.version}` });
  }
}
