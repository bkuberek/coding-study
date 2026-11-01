/**
 * What the file tree does when an action runs (docs/specs/web-ui.md#attempt-view): New file and New
 * folder, Rename or move, Delete and Restore, with the menu that offers them. It is a chunk of its
 * own, fetched the first time a menu opens or an action runs (`FileTreePanel`), so the page loads
 * less before a file is editable (NFR-12).
 */

import "./treeActions.css";

import { h } from "./dom.ts";
import { askNames, confirmAction, type NameField } from "./dialogs.ts";
import type { MenuItem, TreeTabs } from "./fileTreePanel.ts";
import { baseName, type FileScope, joinPath, nameIssue, parentOf } from "./fileRules.ts";
import { originText } from "./format.ts";
import { messageOf } from "./states.ts";
import type { AttemptStatus, TreeEntry } from "./types.ts";

const PROVIDED_ORIGINS = new Set(["starter", "level"]);

/** What the actions need of the panel they act for. */
export interface TreeHost {
  readonly attempt: AttemptStatus;
  readonly tabs: TreeTabs;
  readonly scope: FileScope;
  /** `.java`, `.kt` or `.go` for a package's files; null for other attempts. */
  readonly extension: string | null;
  /** The attempt's folder, as the tree last showed it. */
  readonly root: string;
  announce(message: string): void;
  /** Reads the tree again and draws it. */
  refresh(): Promise<void>;
  /** Shows a refusal above the tree, or clears it with null. */
  show(refusal: string | null): void;
  /** Gives the tree's Tab stop to the item with this key. */
  select(key: string): void;
}

export class TreeActions {
  readonly menu = new TreeMenu();
  readonly #host: TreeHost;

  constructor(host: TreeHost) {
    this.#host = host;
  }

  newFile(folder: string): Promise<void> {
    return this.#ask({
      title: "New file",
      fields: [this.#nameField("Name", folder, "")],
      action: "Create",
      submit: async ([name = ""]) => this.#create(joinPath(folder, name)),
    });
  }

  /** A folder holds files, so a new one comes with its first file. */
  newFolder(folder: string): Promise<void> {
    return this.#ask({
      title: "New folder",
      note: "A folder exists once it holds a file: name its first one too.",
      fields: [this.#nameField("Folder", folder, ""), this.#nameField("First file", "", "")],
      action: "Create",
      submit: async ([name = "", file = ""]) => this.#create(joinPath(joinPath(folder, name), file)),
    });
  }

  rename(entry: TreeEntry): Promise<void> {
    const project = this.#host.scope === "project";
    const field = this.#nameField(project ? "New path" : "New name", "", entry.path);
    return this.#ask({
      title: project ? "Rename or move" : "Rename",
      ...(project ? { note: `Relative to ${this.#host.root}; folders on the way are made. Now in ${parentOf(entry.path) || "the root"}.` } : {}),
      fields: [{ ...field, issue: (value) => (value === entry.path ? "type another name" : field.issue(value)) }],
      action: "Rename",
      submit: async ([to = ""]) => {
        const tabs = this.#host.tabs;
        if (tabs.isModified(entry.path)) return `save or close ${entry.path} first: its tab has unsaved changes`;
        const { sha256 } = await tabs.files.read(entry.path);
        const moved = await tabs.files.move(entry.path, to, sha256);
        const wasOpen = tabs.isOpen(entry.path);
        tabs.discard(entry.path);
        this.#host.select(`file:${moved.path}`);
        this.#host.announce(`renamed ${entry.path} to ${moved.path}`);
        await this.#host.refresh();
        if (wasOpen) void tabs.open(moved.path);
        return null;
      },
    });
  }

  async delete(entry: TreeEntry): Promise<void> {
    const tabs = this.#host.tabs;
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

  async restore(entry: TreeEntry): Promise<void> {
    const tabs = this.#host.tabs;
    const command = `cstudy start ${this.#host.attempt.slug} --restore ${entry.path}`;
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

  async #create(path: string): Promise<null> {
    await this.#host.tabs.files.create(path, "");
    this.#host.announce(`created ${path}`);
    await this.#host.refresh();
    void this.#host.tabs.open(path);
    return null;
  }

  /** Runs a change, then draws the tree again; a refusal shows above the tree. */
  async #act(done: string, change: () => Promise<void>): Promise<void> {
    try {
      await change();
      this.#host.show(null);
      this.#host.announce(done);
    } catch (error) {
      this.#host.show(messageOf(error));
    }
    await this.#host.refresh().catch((error: unknown) => this.#host.show(messageOf(error)));
  }

  async #ask(request: Parameters<typeof askNames>[0]): Promise<void> {
    this.#host.show(null);
    await askNames(request);
  }

  #nameField(label: string, folder: string, value: string): NameField {
    return { label, prefix: folder ? `${folder}/` : "", value, issue: (name) => nameIssue(this.#host.scope, this.#host.extension, name) };
  }
}

/** One menu at a time, by the item it acts on; it closes on Escape, Tab, a choice or a click elsewhere. */
export class TreeMenu {
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
    // Inside the main landmark with the tree, so a screen reader finds it where it acts.
    (anchor.closest("main") ?? document.body).append(menu);
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
