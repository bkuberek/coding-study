/**
 * The Attempt view's file tree (docs/specs/web-ui.md#attempt-view): the attempt's files in their
 * folders, each with its origin and, in a project, its state, and the actions the attempt's kind
 * allows (`fileRules`): New file and New folder, Rename or move, Delete, and Restore, which is
 * `cstudy start --restore`. Each action opens from a row's menu button, a right click, Shift-F10
 * or the context menu key; F2 renames and Delete deletes. The tree is drawn again after every
 * change, so the states stay the ones `cstudy status` prints, keeping the folders the user closed
 * and the item that holds the focus.
 *
 * What an action does, and the menu that offers it, is `treeActions.ts`, a chunk of its own
 * fetched the first time a menu opens or an action runs, so the page loads less before a file is
 * editable (NFR-12).
 */

import { badge, h } from "./dom.ts";
import { creates, fileActions, type FileScope, fileScope, packageExtension } from "./fileRules.ts";
import type { AttemptFiles } from "./files.ts";
import { fileBadge, originText } from "./format.ts";
import { fetchChunk } from "./lazy.ts";
import { type FileNode, fileTree, type TreeNode } from "./tree.ts";
import type { TreeActions, TreeHost } from "./treeActions.ts";
import type { AttemptStatus, Tree, TreeEntry } from "./types.ts";

/** What the tree needs of the editor tabs: `EditorTabs` has all of it. */
export interface TreeTabs {
  readonly files: AttemptFiles;
  open(path: string): Promise<void>;
  isOpen(path: string): boolean;
  isModified(path: string): boolean;
  /** Closes the file's tab without asking. */
  discard(path: string): void;
  /** Shows the file as it is on disk now. */
  reload(path: string): Promise<void>;
}

export interface TreeSetup {
  readonly attempt: AttemptStatus;
  readonly tree: Tree;
  readonly tabs: TreeTabs;
  /** Read by screen readers without moving the focus. */
  readonly announce: (message: string) => void;
}

export interface MenuItem {
  readonly label: string;
  /** The key that does it from the tree, or the command it matches. */
  readonly hint: string;
  readonly destructive?: boolean;
  readonly run: () => void;
}

const ITEM = "[data-tree-item]";
const QUIET_ORIGINS = new Set(["yours", "stub", "notes"]);

export class FileTreePanel {
  readonly element: HTMLElement;
  readonly #setup: TreeSetup;
  readonly #scope: FileScope;
  readonly #extension: string | null;
  readonly #notice: HTMLElement;
  /** The folders the user closed, by path; every other folder shows open. */
  readonly #closed = new Set<string>();
  #actions: Promise<TreeActions | null> | null = null;
  #destroyed = false;
  #tree: Tree;
  /** The `data-tree-item` key of the item that holds the tree's one Tab stop. */
  #current: string | null = null;

  constructor(setup: TreeSetup) {
    this.#setup = setup;
    this.#tree = setup.tree;
    this.#scope = fileScope(setup.attempt);
    this.#extension = packageExtension(setup.attempt);
    this.#notice = h("p", { class: "tree-notice", role: "status", hidden: true });
    this.element = h("nav", { class: "files", "aria-label": "Files" });
    this.element.addEventListener("keydown", (event) => this.#onKey(event));
    this.element.addEventListener("focusin", (event) => this.#onFocus(event));
    this.element.addEventListener("contextmenu", (event) => this.#onContextMenu(event));
    this.#render();
  }

  /** Reads the tree again and draws it, as after a change to a file. */
  async refresh(): Promise<void> {
    this.show(await this.#setup.tabs.files.tree());
  }

  /** Draws a tree the caller already read. */
  show(tree: Tree): void {
    this.#tree = tree;
    this.#render();
  }

  /** Whether the tree, as last drawn, lists the file. */
  has(path: string): boolean {
    return this.#tree.entries.some((entry) => entry.path === path);
  }

  destroy(): void {
    this.#destroyed = true;
    void this.#actions?.then((actions) => actions?.menu.close());
  }

  #render(): void {
    const hadFocus = this.element.contains(document.activeElement);
    const { root, entries } = this.#tree;
    this.element.replaceChildren(
      h("div", { class: "files-head" }, h("p", { class: "files-root eyebrow", title: root }, root), this.#toolbar("")),
      this.#notice,
      entries.length ? this.#list(fileTree(entries), 0) : h("p", { class: "quiet" }, "no files"),
    );
    const items = this.#items();
    const current = items.find((item) => item.dataset["treeItem"] === this.#current) ?? items[0];
    current?.setAttribute("tabindex", "0");
    if (hadFocus) current?.focus();
  }

  #toolbar(folder: string): HTMLElement | null {
    const allowed = creates(this.#scope);
    if (!allowed.files) return null;
    const newFile = h("button", { type: "button", class: "ghost tree-tool", title: "New file" }, "+ file");
    newFile.addEventListener("click", () => this.#lazily((actions) => actions.newFile(folder)));
    const newFolder = allowed.folders ? h("button", { type: "button", class: "ghost tree-tool", title: "New folder" }, "+ folder") : null;
    newFolder?.addEventListener("click", () => this.#lazily((actions) => actions.newFolder(folder)));
    return h("span", { class: "tree-tools" }, newFile, newFolder);
  }

  #list(nodes: readonly TreeNode<TreeEntry>[], depth: number): HTMLElement {
    return h(
      "ul",
      { class: depth === 0 ? "tree" : "tree-children", role: depth === 0 ? "list" : null },
      ...nodes.map((node) => h("li", {}, node.kind === "folder" ? this.#folder(node.path, node.name, node.children, depth) : this.#file(node))),
    );
  }

  #folder(path: string, name: string, children: readonly TreeNode<TreeEntry>[], depth: number): HTMLElement {
    const details = h(
      "details",
      { open: !this.#closed.has(path) },
      h("summary", { class: "tree-folder", "data-tree-item": `folder:${path}`, "data-folder": path, tabindex: "-1" }, name),
      this.#list(children, depth + 1),
    );
    details.addEventListener("toggle", () => {
      if (details.open) this.#closed.delete(path);
      else this.#closed.add(path);
    });
    return details;
  }

  #file(node: FileNode<TreeEntry>): HTMLElement {
    const entry = node.file;
    const state = fileBadge(entry.state === "unchanged" ? null : entry.state);
    const origin = originText(entry.origin, entry.level);
    const missing = entry.size === null;
    const actions = this.#fileItems(entry);
    const button = h(
      "button",
      {
        type: "button",
        class: `tree-file${missing ? " is-missing" : ""}`,
        "data-tree-item": `file:${entry.path}`,
        "data-path": entry.path,
        tabindex: "-1",
        "aria-disabled": missing ? "true" : null,
        "aria-keyshortcuts": actions.length ? "Shift+F10" : null,
        title: `${entry.path} · ${origin}${missing ? " · missing on disk" : ""}${actions.length ? " · Shift-F10 for actions" : ""}`,
      },
      h("span", { class: "tree-name" }, node.name),
      h("span", { class: "tree-origin" }, QUIET_ORIGINS.has(origin) ? "" : origin),
      state ? badge(state.glyph, state.text, `${state.tone} compact`) : null,
    );
    button.addEventListener("click", () => {
      if (!missing) void this.#setup.tabs.open(entry.path);
    });
    if (!actions.length) return button;
    const more = h(
      "button",
      { type: "button", class: "tree-more", tabindex: "-1", "aria-haspopup": "menu", "aria-label": `Actions for ${entry.path}`, title: "Actions" },
      "⋯",
    );
    more.addEventListener("click", () => this.#openMenu(more, actions, button));
    return h("span", { class: "tree-row" }, button, more);
  }

  #fileItems(entry: TreeEntry): MenuItem[] {
    const allowed = fileActions(this.#scope, entry);
    const items: MenuItem[] = [];
    if (allowed.restore) items.push({ label: "Restore", hint: "start --restore", run: () => this.#lazily((actions) => actions.restore(entry)) });
    if (allowed.rename) {
      const label = this.#scope === "project" ? "Rename or move…" : "Rename…";
      items.push({ label, hint: "F2", run: () => this.#lazily((actions) => actions.rename(entry)) });
    }
    if (allowed.delete) items.push({ label: "Delete…", hint: "Del", destructive: true, run: () => this.#lazily((actions) => actions.delete(entry)) });
    return items;
  }

  #folderItems(folder: string): MenuItem[] {
    if (!creates(this.#scope).folders) return [];
    return [
      { label: "New file here…", hint: "", run: () => this.#lazily((actions) => actions.newFile(folder)) },
      { label: "New folder here…", hint: "", run: () => this.#lazily((actions) => actions.newFolder(folder)) },
    ];
  }

  #openMenu(anchor: HTMLElement, items: readonly MenuItem[], returnFocus: HTMLElement, at?: { x: number; y: number }): void {
    this.#lazily((actions) => actions.menu.open(anchor, items, returnFocus, at));
  }

  /** Does `act` with the tree's actions, which are fetched the first time one is needed. */
  #lazily(act: (actions: TreeActions) => unknown): void {
    this.#actions ??= this.#fetchActions();
    void this.#actions.then((actions) => {
      if (actions !== null && !this.#destroyed) void act(actions);
    });
  }

  async #fetchActions(): Promise<TreeActions | null> {
    const module = await fetchChunk(this.#setup.announce, () => import("./sheets.ts"));
    if (module === null) {
      this.#actions = null;
      return null;
    }
    return new module.TreeActions(this.#host());
  }

  #host(): TreeHost {
    const tree = () => this.#tree;
    return {
      attempt: this.#setup.attempt,
      tabs: this.#setup.tabs,
      scope: this.#scope,
      extension: this.#extension,
      get root() {
        return tree().root;
      },
      announce: this.#setup.announce,
      refresh: () => this.refresh(),
      show: (refusal) => this.#show(refusal),
      select: (key) => {
        this.#current = key;
      },
    };
  }

  #show(refusal: string | null): void {
    this.#notice.hidden = refusal === null;
    this.#notice.textContent = refusal === null ? "" : `✕ ${refusal}`;
  }

  /** The items a user can reach: those inside closed folders aside. */
  #items(): HTMLElement[] {
    return [...this.element.querySelectorAll<HTMLElement>(ITEM)].filter((item) => item.getClientRects().length > 0);
  }

  #itemsOf(item: HTMLElement): MenuItem[] {
    const folder = item.dataset["folder"];
    if (folder !== undefined) return this.#folderItems(folder);
    const entry = this.#tree.entries.find((found) => found.path === item.dataset["path"]);
    return entry ? this.#fileItems(entry) : [];
  }

  #onFocus(event: FocusEvent): void {
    const item = (event.target as Element).closest<HTMLElement>(ITEM);
    if (!item) return;
    for (const other of this.element.querySelectorAll<HTMLElement>(`${ITEM}[tabindex="0"]`)) other.tabIndex = -1;
    item.tabIndex = 0;
    this.#current = item.dataset["treeItem"] ?? null;
  }

  #onContextMenu(event: MouseEvent): void {
    const item = (event.target as Element).closest<HTMLElement>(ITEM) ?? (event.target as Element).closest(".tree-row")?.querySelector<HTMLElement>(ITEM);
    const items = item ? this.#itemsOf(item) : [];
    if (!item || !items.length) return;
    event.preventDefault();
    this.#openMenu(item, items, item, { x: event.clientX, y: event.clientY });
  }

  /** One item takes the Tab stop; the arrow keys, Home and End move between the visible ones. */
  #onKey(event: KeyboardEvent): void {
    const current = (event.target as Element).closest<HTMLElement>(ITEM);
    if (!current) return;
    if (this.#onActionKey(event, current)) return;
    const visible = this.#items();
    const index = visible.indexOf(current);
    const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
    const target = event.key === "Home" ? visible[0] : event.key === "End" ? visible.at(-1) : step ? visible[index + step] : undefined;
    if (!target) return;
    event.preventDefault();
    target.focus();
  }

  /** Shift-F10 and the context menu key open the item's menu; F2 renames and Delete deletes. */
  #onActionKey(event: KeyboardEvent, item: HTMLElement): boolean {
    const items = this.#itemsOf(item);
    const opensMenu = event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey);
    const direct = { F2: "F2", Delete: "Del" }[event.key];
    const chosen = direct === undefined ? undefined : items.find((found) => found.hint === direct);
    if (opensMenu && items.length) this.#openMenu(item, items, item);
    else if (chosen) chosen.run();
    else return false;
    event.preventDefault();
    return true;
  }
}
