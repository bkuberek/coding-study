/**
 * The Attempt view's file tree (docs/specs/web-ui.md#attempt-view): the attempt's files in their
 * folders, each with its origin and, in a project, its state, and the actions the attempt's kind
 * allows (`fileRules`): New file and New folder, Rename or move, Delete, and Restore, which is
 * `cstudy start --restore`. Each action opens from a row's menu button, a right click, Shift-F10
 * or the context menu key; F2 renames and Delete deletes. The tree is drawn again after every
 * change, so the states stay the ones `cstudy status` prints, keeping the folders the user closed
 * and the item that holds the focus.
 */

import "./files.css";

import { badge, h } from "./dom.ts";
import type { NameField } from "./fileDialogs.ts";
import { askNames, confirmAction } from "./fileQuestions.ts";
import { baseName, creates, fileActions, type FileScope, fileScope, joinPath, nameIssue, packageExtension, parentOf } from "./fileRules.ts";
import type { AttemptFiles } from "./files.ts";
import { fileBadge, originText } from "./format.ts";
import { messageOf } from "./states.ts";
import { type FileNode, fileTree, type TreeNode } from "./tree.ts";
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

interface MenuItem {
  readonly label: string;
  /** The key that does it from the tree, or the command it matches. */
  readonly hint: string;
  readonly destructive?: boolean;
  readonly run: () => void;
}

const ITEM = "[data-tree-item]";
const QUIET_ORIGINS = new Set(["yours", "stub", "notes"]);
const PROVIDED_ORIGINS = new Set(["starter", "level"]);

export class FileTreePanel {
  readonly element: HTMLElement;
  readonly #setup: TreeSetup;
  readonly #scope: FileScope;
  readonly #extension: string | null;
  readonly #notice: HTMLElement;
  readonly #menu = new TreeMenu();
  /** The folders the user closed, by path; every other folder shows open. */
  readonly #closed = new Set<string>();
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
    this.#menu.close();
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
    newFile.addEventListener("click", () => void this.#newFile(folder));
    const newFolder = allowed.folders ? h("button", { type: "button", class: "ghost tree-tool", title: "New folder" }, "+ folder") : null;
    newFolder?.addEventListener("click", () => void this.#newFolder(folder));
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
    more.addEventListener("click", () => this.#menu.open(more, actions, button));
    return h("span", { class: "tree-row" }, button, more);
  }

  #fileItems(entry: TreeEntry): MenuItem[] {
    const allowed = fileActions(this.#scope, entry);
    const items: MenuItem[] = [];
    if (allowed.restore) items.push({ label: "Restore", hint: "start --restore", run: () => void this.#restore(entry) });
    if (allowed.rename) {
      const label = this.#scope === "project" ? "Rename or move…" : "Rename…";
      items.push({ label, hint: "F2", run: () => void this.#rename(entry) });
    }
    if (allowed.delete) items.push({ label: "Delete…", hint: "Del", destructive: true, run: () => void this.#delete(entry) });
    return items;
  }

  #folderItems(folder: string): MenuItem[] {
    if (!creates(this.#scope).folders) return [];
    return [
      { label: "New file here…", hint: "", run: () => void this.#newFile(folder) },
      { label: "New folder here…", hint: "", run: () => void this.#newFolder(folder) },
    ];
  }

  #newFile(folder: string): Promise<void> {
    return this.#ask({
      title: "New file",
      fields: [this.#nameField("Name", folder, "")],
      action: "Create",
      submit: async ([name = ""]) => this.#create(joinPath(folder, name)),
    });
  }

  /** A folder holds files, so a new one comes with its first file. */
  #newFolder(folder: string): Promise<void> {
    return this.#ask({
      title: "New folder",
      note: "A folder exists once it holds a file: name its first one too.",
      fields: [this.#nameField("Folder", folder, ""), this.#nameField("First file", "", "")],
      action: "Create",
      submit: async ([name = "", file = ""]) => this.#create(joinPath(joinPath(folder, name), file)),
    });
  }

  async #create(path: string): Promise<null> {
    await this.#setup.tabs.files.create(path, "");
    this.#setup.announce(`created ${path}`);
    await this.refresh();
    void this.#setup.tabs.open(path);
    return null;
  }

  #rename(entry: TreeEntry): Promise<void> {
    const project = this.#scope === "project";
    const field = this.#nameField(project ? "New path" : "New name", "", entry.path);
    return this.#ask({
      title: project ? "Rename or move" : "Rename",
      ...(project ? { note: `Relative to ${this.#tree.root}; folders on the way are made. Now in ${parentOf(entry.path) || "the root"}.` } : {}),
      fields: [{ ...field, issue: (value) => (value === entry.path ? "type another name" : field.issue(value)) }],
      action: "Rename",
      submit: async ([to = ""]) => {
        const tabs = this.#setup.tabs;
        if (tabs.isModified(entry.path)) return `save or close ${entry.path} first: its tab has unsaved changes`;
        const { sha256 } = await tabs.files.read(entry.path);
        const moved = await tabs.files.move(entry.path, to, sha256);
        const wasOpen = tabs.isOpen(entry.path);
        tabs.discard(entry.path);
        this.#current = `file:${moved.path}`;
        this.#setup.announce(`renamed ${entry.path} to ${moved.path}`);
        await this.refresh();
        if (wasOpen) void tabs.open(moved.path);
        return null;
      },
    });
  }

  async #delete(entry: TreeEntry): Promise<void> {
    const tabs = this.#setup.tabs;
    const provided = PROVIDED_ORIGINS.has(entry.origin);
    const unsaved = tabs.isModified(entry.path) ? " Its tab's unsaved changes go too." : "";
    const confirmed = await confirmAction({
      title: `Delete ${baseName(entry.path)}?`,
      message: provided
        ? `${entry.path} is a ${originText(entry.origin, entry.level)} file: Restore writes it back as cstudy provides it.${unsaved}`
        : `${entry.path} is a file you added; the page cannot bring it back.${unsaved}`,
      action: "Delete",
      destructive: true,
    });
    if (!confirmed) return;
    await this.#act(`deleted ${entry.path}`, async () => {
      const { sha256 } = await tabs.files.read(entry.path);
      await tabs.files.remove(entry.path, sha256);
      tabs.discard(entry.path);
    });
  }

  async #restore(entry: TreeEntry): Promise<void> {
    const tabs = this.#setup.tabs;
    const command = `cstudy start ${this.#setup.attempt.slug} --restore ${entry.path}`;
    const loses = entry.state === "modified" || tabs.isModified(entry.path);
    if (loses) {
      const confirmed = await confirmAction({
        title: `Restore ${baseName(entry.path)}?`,
        message: `${entry.path} goes back to what cstudy provides now; your changes to it are replaced.`,
        action: "Restore",
        destructive: true,
        command,
      });
      if (!confirmed) return;
    }
    await this.#act(`restored ${entry.path}`, async () => {
      await tabs.files.restore(entry.path);
      if (tabs.isOpen(entry.path)) await tabs.reload(entry.path);
    });
  }

  /** Runs a change, then draws the tree again; a refusal shows above the tree. */
  async #act(done: string, change: () => Promise<void>): Promise<void> {
    try {
      await change();
      this.#show(null);
      this.#setup.announce(done);
    } catch (error) {
      this.#show(messageOf(error));
    }
    await this.refresh().catch((error: unknown) => this.#show(messageOf(error)));
  }

  async #ask(request: Parameters<typeof askNames>[0]): Promise<void> {
    this.#show(null);
    await askNames(request);
  }

  #nameField(label: string, folder: string, value: string): NameField {
    return { label, prefix: folder ? `${folder}/` : "", value, issue: (name) => nameIssue(this.#scope, this.#extension, name) };
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
    this.#menu.open(item, items, item, { x: event.clientX, y: event.clientY });
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
    if (opensMenu && items.length) this.#menu.open(item, items, item);
    else if (chosen) chosen.run();
    else return false;
    event.preventDefault();
    return true;
  }
}

/** One menu at a time, by the item it acts on; it closes on Escape, Tab, a choice or a click elsewhere. */
class TreeMenu {
  #element: HTMLElement | null = null;
  #anchor: HTMLElement | null = null;
  #returnFocus: HTMLElement | null = null;

  open(anchor: HTMLElement, items: readonly MenuItem[], returnFocus: HTMLElement, at?: { x: number; y: number }): void {
    this.close();
    const buttons = items.map((item) => {
      const button = h(
        "button",
        { type: "button", role: "menuitem", tabindex: "-1", class: item.destructive ? "is-destructive" : null },
        h("span", {}, item.label),
        item.hint ? h("span", { class: "tree-menu-hint" }, item.hint) : null,
      );
      button.addEventListener("click", () => {
        this.close(false);
        item.run();
      });
      return button;
    });
    const subject = returnFocus.dataset["path"] ?? returnFocus.dataset["folder"] ?? "the file";
    const menu = h("div", { class: "tree-menu", role: "menu", "aria-label": `Actions for ${subject}` }, ...buttons);
    menu.addEventListener("keydown", (event) => this.#onKey(event, buttons));
    document.body.append(menu);
    const rect = anchor.getBoundingClientRect();
    const x = Math.min(at?.x ?? rect.left, window.innerWidth - menu.offsetWidth - 8);
    const y = Math.min(at?.y ?? rect.bottom + 2, window.innerHeight - menu.offsetHeight - 8);
    menu.style.left = `${Math.max(x, 8)}px`;
    menu.style.top = `${Math.max(y, 8)}px`;
    this.#element = menu;
    this.#anchor = anchor;
    this.#returnFocus = returnFocus;
    if (anchor.hasAttribute("aria-haspopup")) anchor.setAttribute("aria-expanded", "true");
    document.addEventListener("pointerdown", this.#onPointer, true);
    buttons[0]?.focus();
  }

  close(restoreFocus = true): void {
    if (this.#element === null) return;
    this.#element.remove();
    this.#element = null;
    this.#anchor?.removeAttribute("aria-expanded");
    document.removeEventListener("pointerdown", this.#onPointer, true);
    if (restoreFocus) this.#returnFocus?.focus();
  }

  #onKey(event: KeyboardEvent, buttons: readonly HTMLButtonElement[]): void {
    const index = buttons.indexOf(event.target as HTMLButtonElement);
    const moves: Record<string, number | undefined> = {
      ArrowDown: (index + 1) % buttons.length,
      ArrowUp: (index - 1 + buttons.length) % buttons.length,
      Home: 0,
      End: buttons.length - 1,
    };
    if (event.key === "Escape" || event.key === "Tab") {
      event.preventDefault();
      this.close();
      return;
    }
    const target = moves[event.key];
    if (target === undefined) return;
    event.preventDefault();
    buttons[target]?.focus();
  }

  readonly #onPointer = (event: PointerEvent): void => {
    if (!this.#element?.contains(event.target as Node)) this.close(false);
  };
}
