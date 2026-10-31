/**
 * The Attempt view's editor tabs (docs/specs/web-ui.md#attempt-view): one CodeMirror view per open
 * file, fetched with the editor module the first time a file opens. Text the page edits opens
 * writable and saves with Cmd or Ctrl-S (`EditorFile`); a tab with unsaved changes asks before it
 * closes, and so do the view and the page.
 */

import type { Editor } from "../editor.ts";
import type { PageContext } from "./context.ts";
import { h } from "./dom.ts";
import { EditorFile, markTab } from "./editorFile.ts";
import { confirmAction } from "./fileDialogs.ts";
import { AttemptFiles } from "./files.ts";
import { isSaveShortcut, saveShortcutLabel, trackUnsaved } from "./save.ts";
import { failure, loading } from "./states.ts";
import type { FileDocument, Preferences } from "./types.ts";

let editorModule: Promise<typeof import("../editor.ts")> | null = null;

function loadEditorModule(): Promise<typeof import("../editor.ts")> {
  editorModule ??= import("../editor.ts");
  return editorModule;
}

interface OpenFile {
  readonly tab: HTMLButtonElement;
  readonly panel: HTMLElement;
  editor: Editor | null;
  view: EditorFile | null;
}

export type SavedListener = (path: string) => void;

export class EditorTabs {
  readonly element: HTMLElement;
  readonly files: AttemptFiles;
  readonly #context: PageContext;
  readonly #tablist: HTMLElement;
  readonly #panels: HTMLElement;
  readonly #placeholder: HTMLElement;
  readonly #open = new Map<string, OpenFile>();
  readonly #savedListeners = new Set<SavedListener>();
  readonly #untrack: () => void;
  #active: string | null = null;
  #destroyed = false;

  constructor(context: PageContext, attemptId: number) {
    this.#context = context;
    this.files = new AttemptFiles(context.api, attemptId);
    const shortcut = saveShortcutLabel(navigator.platform);
    this.#tablist = h("div", { class: "tablist", role: "tablist", "aria-label": "Open files" });
    this.#placeholder = h(
      "div",
      { class: "editor-empty" },
      h("p", {}, "Open a file from the tree."),
      h("p", { class: "quiet" }, `${shortcut} saves the open file; the page never saves on its own.`),
    );
    this.#panels = h("div", { class: "panels" }, this.#placeholder);
    this.#tablist.addEventListener("keydown", (event) => this.#onTabKey(event));
    this.element = h(
      "section",
      { class: "editors", "aria-label": "Editor" },
      h("div", { class: "tabbar" }, this.#tablist, h("span", { class: "chip save-hint", title: "Save the open file" }, h("kbd", {}, shortcut), " save")),
      this.#panels,
    );
    document.addEventListener("keydown", this.#onSaveKey);
    window.addEventListener("beforeunload", this.#onUnload);
    this.#untrack = trackUnsaved(() => this.unsavedPaths());
  }

  async open(path: string): Promise<void> {
    const opened = this.#open.get(path);
    if (opened) {
      this.#activate(path);
      opened.editor?.focus();
      return;
    }
    const file = this.#addTab(path);
    this.#activate(path);
    try {
      const document = await this.files.read(path);
      if (this.#destroyed) return;
      await this.#show(file, document);
    } catch (error) {
      file.panel.replaceChildren(failure(error));
    }
  }

  isOpen(path: string): boolean {
    return this.#open.has(path);
  }

  isModified(path: string): boolean {
    return this.#open.get(path)?.view?.modified ?? false;
  }

  unsavedPaths(): string[] {
    return [...this.#open].filter(([, file]) => file.view?.modified).map(([path]) => path);
  }

  /** Saves the file of the active tab. */
  async saveActive(): Promise<void> {
    if (this.#active !== null) await this.#open.get(this.#active)?.view?.save();
  }

  /** Shows the file as it is on disk now, dropping the tab's changes. */
  async reload(path: string): Promise<void> {
    await this.#open.get(path)?.view?.reload();
  }

  /** Closes the file's tab without asking, dropping its changes. */
  discard(path: string): void {
    this.#remove(path);
  }

  /** Calls the listener with the path of every file a tab saves. */
  onSaved(listener: SavedListener): () => void {
    this.#savedListeners.add(listener);
    return () => this.#savedListeners.delete(listener);
  }

  applyPreferences(preferences: Preferences): void {
    for (const { editor } of this.#open.values()) {
      editor?.setTheme(preferences.theme);
      void editor?.setVim(preferences.vim);
    }
  }

  destroy(): void {
    this.#destroyed = true;
    document.removeEventListener("keydown", this.#onSaveKey);
    window.removeEventListener("beforeunload", this.#onUnload);
    this.#untrack();
    this.#savedListeners.clear();
    for (const { editor } of this.#open.values()) editor?.destroy();
    this.#open.clear();
  }

  async #show(file: OpenFile, document: FileDocument): Promise<void> {
    if (document.text === null) {
      file.panel.replaceChildren(
        h("div", { class: "editor-empty" }, h("p", {}, `${document.path} is not UTF-8 text or is over 1 MiB, so it opens read-only without its text.`)),
      );
      return;
    }
    const path = document.path;
    const view = new EditorFile(file.panel, document, this.files, {
      modified: (modified) => markTab(file.tab, path, modified),
      saved: () => {
        for (const listener of this.#savedListeners) listener(path);
      },
      gone: () => this.#remove(path),
      announce: (message) => this.#context.shell.announce(message),
    });
    const { createEditor } = await loadEditorModule();
    const preferences = this.#context.preferences();
    const editor = await createEditor({
      parent: view.host,
      path,
      text: document.text,
      nonce: this.#context.nonce,
      theme: preferences.theme,
      readOnly: false,
      vim: preferences.vim,
    });
    if (this.#destroyed || !this.#open.has(path)) {
      editor.destroy();
      return;
    }
    file.editor = editor;
    file.view = view;
    view.attach(editor);
  }

  #addTab(path: string): OpenFile {
    const id = `tab-${this.#open.size}-${path.replace(/[^\w-]/g, "_")}`;
    const name = path.slice(path.lastIndexOf("/") + 1);
    const close = h("span", { class: "tab-close", "aria-hidden": "true", title: "Close" }, "×");
    const tab = h(
      "button",
      { type: "button", role: "tab", id, "aria-selected": "false", "aria-controls": `${id}-panel`, title: path, tabindex: "-1" },
      h("span", { class: "tab-name" }, name),
      close,
    );
    const panel = h("div", { role: "tabpanel", id: `${id}-panel`, "aria-labelledby": id, class: "panel", hidden: true }, loading(`opening ${path}…`));
    tab.addEventListener("click", (event) => {
      if ((event.target as Element).closest(".tab-close, .tab-dot")) void this.#close(path);
      else this.#activate(path);
    });
    tab.addEventListener("auxclick", (event) => {
      if (event.button === 1) void this.#close(path);
    });
    this.#tablist.append(tab);
    this.#panels.append(panel);
    const file: OpenFile = { tab, panel, editor: null, view: null };
    this.#open.set(path, file);
    return file;
  }

  #activate(path: string): void {
    this.#active = path;
    this.#placeholder.hidden = true;
    for (const [openPath, { tab, panel }] of this.#open) {
      const active = openPath === path;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      panel.hidden = !active;
    }
  }

  /** Closes the tab, once its unsaved changes, if any, may go. */
  async #close(path: string): Promise<void> {
    if (this.isModified(path)) {
      const close = await confirmAction({
        title: "Close with unsaved changes?",
        message: `${path} has changes the page has not saved. Closing its tab loses them.`,
        action: "Close and lose them",
        destructive: true,
      });
      if (!close) return;
    }
    this.#remove(path);
  }

  #remove(path: string): void {
    const file = this.#open.get(path);
    if (!file) return;
    const paths = [...this.#open.keys()];
    const index = paths.indexOf(path);
    file.editor?.destroy();
    file.tab.remove();
    file.panel.remove();
    this.#open.delete(path);
    if (this.#active !== path) return;
    const next = paths[index + 1] ?? paths[index - 1];
    if (next !== undefined && next !== path) {
      this.#activate(next);
      this.#open.get(next)?.tab.focus();
    } else {
      this.#active = null;
      this.#placeholder.hidden = false;
    }
  }

  #onTabKey(event: KeyboardEvent): void {
    const paths = [...this.#open.keys()];
    const index = this.#active === null ? -1 : paths.indexOf(this.#active);
    const moves: Record<string, number | undefined> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: paths.length - 1 };
    if (event.key === "Delete" && this.#active !== null) {
      event.preventDefault();
      void this.#close(this.#active);
      return;
    }
    const target = moves[event.key];
    const path = target === undefined ? undefined : paths[target];
    if (path === undefined) return;
    event.preventDefault();
    this.#activate(path);
    this.#open.get(path)?.tab.focus();
  }

  /** Cmd or Ctrl-S anywhere in the view saves the active tab, never the browser's page. */
  readonly #onSaveKey = (event: KeyboardEvent): void => {
    if (!isSaveShortcut(event) || this.#active === null) return;
    event.preventDefault();
    void this.saveActive();
  };

  readonly #onUnload = (event: BeforeUnloadEvent): void => {
    if (this.unsavedPaths().length > 0) event.preventDefault();
  };
}
