/**
 * The Attempt view's file tree and editor tabs (docs/specs/web-ui.md#attempt-view): one CodeMirror
 * view per open file, fetched with the editor module the first time a file opens. Until the page
 * saves files, every editor is read-only.
 */

import type { Editor } from "../editor.ts";
import type { PageContext } from "./context.ts";
import { badge, h } from "./dom.ts";
import { fileBadge, originText } from "./format.ts";
import { failure, loading } from "./states.ts";
import { type FileNode, fileTree, type TreeNode } from "./tree.ts";
import type { FileDocument, Preferences, Tree, TreeEntry } from "./types.ts";

const READ_ONLY_NOTE = "Read-only: the page does not save files yet; edit them in your editor.";

let editorModule: Promise<typeof import("../editor.ts")> | null = null;

function loadEditorModule(): Promise<typeof import("../editor.ts")> {
  editorModule ??= import("../editor.ts");
  return editorModule;
}

interface OpenFile {
  readonly tab: HTMLButtonElement;
  readonly panel: HTMLElement;
  editor: Editor | null;
}

/** The tree of the attempt's files; `open` is called with a file's path. */
export function fileTreeView(tree: Tree, open: (path: string) => void): HTMLElement {
  const list = treeList(fileTree(tree.entries), open, 0);
  const view = h(
    "nav",
    { class: "files", "aria-label": "Files" },
    h("p", { class: "files-root eyebrow", title: tree.root }, tree.root),
    tree.entries.length ? list : h("p", { class: "quiet" }, "no files"),
  );
  rovingFocus(view);
  return view;
}

function treeList(nodes: readonly TreeNode<TreeEntry>[], open: (path: string) => void, depth: number): HTMLElement {
  return h(
    "ul",
    { class: depth === 0 ? "tree" : "tree-children", role: depth === 0 ? "list" : null },
    ...nodes.map((node) =>
      node.kind === "folder"
        ? h(
            "li",
            {},
            h(
              "details",
              { open: true },
              h("summary", { class: "tree-folder", "data-tree-item": true, tabindex: "-1" }, node.name),
              treeList(node.children, open, depth + 1),
            ),
          )
        : h("li", {}, fileButton(node, open)),
    ),
  );
}

function fileButton(node: FileNode<TreeEntry>, open: (path: string) => void): HTMLButtonElement {
  const entry = node.file;
  const state = fileBadge(entry.state === "unchanged" ? null : entry.state);
  const origin = originText(entry.origin, entry.level);
  const missing = entry.size === null;
  const button = h(
    "button",
    {
      type: "button",
      class: `tree-file${missing ? " is-missing" : ""}`,
      "data-tree-item": true,
      "data-path": entry.path,
      tabindex: "-1",
      disabled: missing,
      title: `${entry.path} · ${origin}${missing ? " · missing on disk" : ""}`,
    },
    h("span", { class: "tree-name" }, node.name),
    h("span", { class: "tree-origin" }, origin === "yours" || origin === "stub" || origin === "notes" ? "" : origin),
    state ? badge(state.glyph, state.text, `${state.tone} compact`) : null,
  );
  button.addEventListener("click", () => open(entry.path));
  return button;
}

/** One tree item takes the Tab stop; the arrow keys move between the visible ones. */
function rovingFocus(view: HTMLElement): void {
  const items = () =>
    [...view.querySelectorAll<HTMLElement>("[data-tree-item]")].filter(
      (item) => item.getClientRects().length > 0 && !(item as HTMLButtonElement).disabled,
    );
  const first = items()[0] ?? view.querySelector<HTMLElement>("[data-tree-item]");
  first?.setAttribute("tabindex", "0");
  view.addEventListener("keydown", (event) => {
    const current = (event.target as Element).closest<HTMLElement>("[data-tree-item]");
    if (!current) return;
    const visible = items();
    const index = visible.indexOf(current);
    const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
    const target =
      event.key === "Home" ? visible[0] : event.key === "End" ? visible.at(-1) : step ? visible[index + step] : undefined;
    if (!target) return;
    event.preventDefault();
    current.setAttribute("tabindex", "-1");
    target.setAttribute("tabindex", "0");
    target.focus();
  });
}

export class EditorTabs {
  readonly element: HTMLElement;
  readonly #context: PageContext;
  readonly #attemptId: number;
  readonly #tablist: HTMLElement;
  readonly #panels: HTMLElement;
  readonly #placeholder: HTMLElement;
  readonly #open = new Map<string, OpenFile>();
  #active: string | null = null;
  #destroyed = false;

  constructor(context: PageContext, attemptId: number) {
    this.#context = context;
    this.#attemptId = attemptId;
    this.#tablist = h("div", { class: "tablist", role: "tablist", "aria-label": "Open files" });
    this.#placeholder = h("div", { class: "editor-empty" }, h("p", {}, "Open a file from the tree."), h("p", { class: "quiet" }, READ_ONLY_NOTE));
    this.#panels = h("div", { class: "panels" }, this.#placeholder);
    this.#tablist.addEventListener("keydown", (event) => this.#onTabKey(event));
    this.element = h(
      "section",
      { class: "editors", "aria-label": "Editor" },
      h("div", { class: "tabbar" }, this.#tablist, h("span", { class: "chip", title: READ_ONLY_NOTE }, "read-only")),
      this.#panels,
    );
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
      const document = await this.#context.api.get<FileDocument>(
        `/api/v1/attempts/${this.#attemptId}/files/${path.split("/").map(encodeURIComponent).join("/")}`,
      );
      if (this.#destroyed) return;
      await this.#show(file, document);
    } catch (error) {
      file.panel.replaceChildren(failure(error));
    }
  }

  applyPreferences(preferences: Preferences): void {
    for (const { editor } of this.#open.values()) {
      editor?.setTheme(preferences.theme);
      void editor?.setVim(preferences.vim);
    }
  }

  destroy(): void {
    this.#destroyed = true;
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
    file.panel.replaceChildren();
    const { createEditor } = await loadEditorModule();
    const preferences = this.#context.preferences();
    file.editor = await createEditor({
      parent: file.panel,
      path: document.path,
      text: document.text,
      nonce: this.#context.nonce,
      theme: preferences.theme,
      readOnly: true,
      vim: preferences.vim,
    });
    if (this.#destroyed) file.editor.destroy();
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
      if (event.target === close) this.#close(path);
      else this.#activate(path);
    });
    tab.addEventListener("auxclick", (event) => {
      if (event.button === 1) this.#close(path);
    });
    this.#tablist.append(tab);
    this.#panels.append(panel);
    const file: OpenFile = { tab, panel, editor: null };
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

  #close(path: string): void {
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
      this.#close(this.#active);
      return;
    }
    const target = moves[event.key];
    const path = target === undefined ? undefined : paths[target];
    if (path === undefined) return;
    event.preventDefault();
    this.#activate(path);
    this.#open.get(path)?.tab.focus();
  }
}
