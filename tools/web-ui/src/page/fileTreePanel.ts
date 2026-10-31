/**
 * The Attempt view's file tree (docs/specs/web-ui.md#attempt-view): the attempt's files in their
 * folders, each with its origin and, in a project, its state. It is drawn again after every
 * change the page makes, so the states stay the ones `cstudy status` prints, and it keeps the
 * folders the user closed and the item that holds the focus.
 */

import "./files.css";

import { badge, h } from "./dom.ts";
import type { AttemptFiles } from "./files.ts";
import { fileBadge, originText } from "./format.ts";
import { type FileNode, fileTree, type TreeNode } from "./tree.ts";
import type { Tree, TreeEntry } from "./types.ts";

const ITEM = "[data-tree-item]";
const QUIET_ORIGINS = new Set(["yours", "stub", "notes"]);

export class FileTreePanel {
  readonly element: HTMLElement;
  readonly #files: AttemptFiles;
  readonly #open: (path: string) => void;
  /** The folders the user closed, by path; every other folder shows open. */
  readonly #closed = new Set<string>();
  #tree: Tree;
  /** The `data-tree-item` key of the item that holds the tree's one Tab stop. */
  #current: string | null = null;

  constructor(tree: Tree, files: AttemptFiles, open: (path: string) => void) {
    this.#tree = tree;
    this.#files = files;
    this.#open = open;
    this.element = h("nav", { class: "files", "aria-label": "Files" });
    this.element.addEventListener("keydown", (event) => this.#onKey(event));
    this.element.addEventListener("focusin", (event) => this.#onFocus(event));
    this.#render();
  }

  /** Reads the tree again and draws it, as after a change to a file. */
  async refresh(): Promise<void> {
    this.#tree = await this.#files.tree();
    this.#render();
  }

  #render(): void {
    const hadFocus = this.element.contains(document.activeElement);
    const { root, entries } = this.#tree;
    this.element.replaceChildren(
      h("p", { class: "files-root eyebrow", title: root }, root),
      entries.length ? this.#list(fileTree(entries), 0) : h("p", { class: "quiet" }, "no files"),
    );
    const items = this.#items();
    const current = items.find((item) => item.dataset["treeItem"] === this.#current) ?? items[0];
    current?.setAttribute("tabindex", "0");
    if (hadFocus) current?.focus();
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
    const button = h(
      "button",
      {
        type: "button",
        class: `tree-file${missing ? " is-missing" : ""}`,
        "data-tree-item": `file:${entry.path}`,
        "data-path": entry.path,
        tabindex: "-1",
        "aria-disabled": missing ? "true" : null,
        title: `${entry.path} · ${origin}${missing ? " · missing on disk" : ""}`,
      },
      h("span", { class: "tree-name" }, node.name),
      h("span", { class: "tree-origin" }, QUIET_ORIGINS.has(origin) ? "" : origin),
      state ? badge(state.glyph, state.text, `${state.tone} compact`) : null,
    );
    button.addEventListener("click", () => {
      if (!missing) this.#open(entry.path);
    });
    return button;
  }

  /** The items a user can reach: those inside closed folders aside. */
  #items(): HTMLElement[] {
    return [...this.element.querySelectorAll<HTMLElement>(ITEM)].filter((item) => item.getClientRects().length > 0);
  }

  #onFocus(event: FocusEvent): void {
    const item = (event.target as Element).closest<HTMLElement>(ITEM);
    if (!item) return;
    for (const other of this.element.querySelectorAll<HTMLElement>(`${ITEM}[tabindex="0"]`)) other.tabIndex = -1;
    item.tabIndex = 0;
    this.#current = item.dataset["treeItem"] ?? null;
  }

  /** One item takes the Tab stop; the arrow keys, Home and End move between the visible ones. */
  #onKey(event: KeyboardEvent): void {
    const current = (event.target as Element).closest<HTMLElement>(ITEM);
    if (!current) return;
    const visible = this.#items();
    const index = visible.indexOf(current);
    const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
    const target = event.key === "Home" ? visible[0] : event.key === "End" ? visible.at(-1) : step ? visible[index + step] : undefined;
    if (!target) return;
    event.preventDefault();
    target.focus();
  }
}
