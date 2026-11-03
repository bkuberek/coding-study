/**
 * The read-only tabs of library files (docs/specs/web-ui.md#go-to-definition): the standard
 * library, typeshed, `node_modules`, `.venv`, which a jump into them opens. A tab has a `library`
 * badge and the file's path, no language session and no save; it closes like any tab. The editors
 * are this class's own, not the tabs': a library file is never a file of the attempt, so nothing
 * that follows the attempt's editors (a run's diagnostics, a session) takes it for one.
 */

import type { Extension } from "@codemirror/state";

import type { LibraryFile } from "../code-intelligence.ts";
import type { Editor } from "../editor.ts";
import type { PageContext } from "./context.ts";
import { badge, h } from "./dom.ts";
import type { Preferences } from "./types.ts";
import type { EditorTabs } from "./workbench.ts";

import "./library-tabs.css";

interface Library {
  readonly key: string;
  readonly editor: Editor;
}

/** The key of a library file's tab; no path of the attempt's tree starts with it. */
export function libraryKey(path: string): string {
  return `library:${path}`;
}

export class LibraryTabs {
  readonly #tabs: EditorTabs;
  readonly #context: PageContext;
  readonly #libraries = new Map<string, Library>();

  constructor(tabs: EditorTabs, context: PageContext) {
    this.#tabs = tabs;
    this.#context = context;
  }

  /** Opens the file in a tab of its own, or refreshes and brings forward the tab it has. */
  async open(file: LibraryFile, extension: Extension): Promise<Editor | null> {
    const key = libraryKey(file.path);
    const found = this.show(file.uri);
    if (found !== null) {
      found.replaceText(file.text);
      return found;
    }
    const { tab, panel } = this.#tabs.addTab(key);
    tab.title = file.path;
    tab.querySelector(".tab-name")?.after(badge("", "library", "info"));
    const host = h("div", { class: "editor-host" });
    panel.replaceChildren(
      h("p", { class: "file-note library-note" }, badge("", "library", "info"), " ", h("strong", {}, file.path), " · read-only"),
      host,
    );
    this.#tabs.activate(key);
    const { createEditor } = await import("../editor.ts");
    const preferences = this.#context.preferences();
    // Read-only content is named by its path; `aria-readonly` says the rest to a screen reader.
    const editor = await createEditor({
      parent: host,
      path: file.path,
      text: file.text,
      nonce: this.#context.nonce,
      theme: preferences.theme,
      readOnly: true,
      vim: preferences.vim,
    });
    if (!this.#tabs.isOpen(key)) {
      editor.destroy();
      return null;
    }
    editor.setIntelligence(extension);
    this.#libraries.set(file.uri, { key, editor });
    editor.focus();
    return editor;
  }

  /** Brings the tab of the file forward; null when it was closed. */
  show(uri: string): Editor | null {
    const found = this.#libraries.get(uri);
    if (found === undefined || !this.#tabs.isOpen(found.key)) return null;
    this.#tabs.activate(found.key);
    return found.editor;
  }

  /** A tab was closed: its editor goes if it was a library's. */
  closed(key: string): void {
    for (const [uri, library] of this.#libraries) {
      if (library.key !== key) continue;
      library.editor.destroy();
      this.#libraries.delete(uri);
    }
  }

  /** The theme and Vim follow the preferences, as in the attempt's own editors. */
  apply(preferences: Preferences): void {
    for (const { editor } of this.#libraries.values()) {
      editor.setTheme(preferences.theme);
      void editor.setVim(preferences.vim);
    }
  }

  /** Takes Back out of every library tab, as when code intelligence turns off. */
  release(): void {
    for (const { editor } of this.#libraries.values()) editor.setIntelligence([]);
  }

  /** The view ends; the tabs go with it, and the editors with them. */
  destroy(): void {
    for (const { editor } of this.#libraries.values()) editor.destroy();
    this.#libraries.clear();
  }
}
