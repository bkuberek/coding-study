/**
 * One file open in an editor tab (docs/specs/web-ui.md#attempt-view): a writable editor for text
 * the page edits, saved only when asked; the unsaved mark on its tab; and the banners above it:
 * a conflict with the version on disk, offering Reload theirs and Overwrite; a refused save; and
 * the note on a generated test file.
 */

import "./files.css";

import type { Editor } from "../editor.ts";
import { ApiError } from "./api.ts";
import { badge, h, nodes } from "./dom.ts";
import type { AttemptFiles, Conflict } from "./files.ts";
import { originText } from "./format.ts";
import { FileSaver, type SaveOutcome } from "./save.ts";
import { messageOf } from "./states.ts";
import type { FileDocument } from "./types.ts";

export interface EditorFileEvents {
  /** The tab's text now differs from the file on disk, or no longer does. */
  readonly modified: (modified: boolean) => void;
  /** The file on disk changed: a save or an overwrite. */
  readonly saved: () => void;
  /** The file is gone, and the tab has nothing to show. */
  readonly gone: () => void;
  /** Read by screen readers without moving the focus. */
  readonly announce: (message: string) => void;
}

const ATTEMPT_ENDED = "attempt_ended";
const GENERATED_ORIGIN = "level";

export class EditorFile {
  readonly path: string;
  /** Where the editor goes. */
  readonly host: HTMLElement;
  readonly #banner: HTMLElement;
  readonly #files: AttemptFiles;
  readonly #events: EditorFileEvents;
  readonly #sha256: string;
  #editor: Editor | null = null;
  #saver: FileSaver | null = null;
  #busy = false;

  constructor(panel: HTMLElement, document: FileDocument, files: AttemptFiles, events: EditorFileEvents) {
    this.path = document.path;
    this.#sha256 = document.sha256;
    this.#files = files;
    this.#events = events;
    this.#banner = h("div", { class: "file-banner", hidden: true });
    this.host = h("div", { class: "editor-host" });
    panel.replaceChildren(...nodes([this.#banner, generatedNote(document), this.host]));
  }

  /** Connects the editor made in `host`. */
  attach(editor: Editor): void {
    this.#editor = editor;
    this.#saver = new FileSaver(this.#files, this.path, this.#sha256, editor);
    editor.onChange(() => this.#events.modified(editor.modified));
  }

  get modified(): boolean {
    return this.#editor?.modified ?? false;
  }

  save(): Promise<void> {
    return this.#run((saver) => saver.save());
  }

  /** Shows the file as it is on disk now, as after a restore, dropping the tab's changes. */
  reload(): Promise<void> {
    return this.#run(async (saver) => {
      if ((await saver.reloadTheirs()) === "gone") this.#events.gone();
      return { kind: "unchanged" };
    });
  }

  async #run(step: (saver: FileSaver) => Promise<SaveOutcome>): Promise<void> {
    const saver = this.#saver;
    if (saver === null || this.#busy) return;
    this.#busy = true;
    this.host.parentElement?.setAttribute("aria-busy", "true");
    try {
      this.#settle(await step(saver));
    } catch (error) {
      this.#refused(error);
    } finally {
      this.#busy = false;
      this.host.parentElement?.removeAttribute("aria-busy");
      this.#events.modified(this.modified);
    }
  }

  #settle(outcome: SaveOutcome): void {
    switch (outcome.kind) {
      case "saved":
        this.#hideBanner();
        this.#events.saved();
        this.#events.announce(`saved ${this.path}`);
        return;
      case "unchanged":
        this.#hideBanner();
        return;
      case "conflict":
        this.#showConflict(outcome.conflict);
        this.#events.announce(`not saved: ${outcome.conflict.message}`);
    }
  }

  #showConflict(conflict: Conflict): void {
    const gone = conflict.theirs === null;
    const reload = h("button", { type: "button" }, gone ? "Close the tab" : "Reload theirs");
    const overwrite = h("button", { type: "button", class: "button primary" }, gone ? "Save mine again" : "Overwrite");
    reload.addEventListener("click", () => void this.reload());
    overwrite.addEventListener("click", () => void this.#run((saver) => saver.overwrite()));
    this.#showBanner(
      "conflict",
      h(
        "p",
        { class: "banner-text" },
        badge("!", gone ? "deleted on disk" : "changed on disk", "warn"),
        " ",
        h("strong", {}, this.path),
        gone
          ? " was deleted since this tab opened it, by your editor, the terminal or another tab."
          : " changed since this tab opened it, in your editor, the terminal or another tab.",
      ),
      h("div", { class: "banner-actions" }, reload, overwrite),
      h(
        "p",
        { class: "banner-help quiet" },
        gone
          ? "Close the tab drops your changes; Save mine again writes the file back with them."
          : "Reload theirs drops your changes; Overwrite saves yours over the version on disk.",
      ),
    );
    overwrite.focus();
  }

  #refused(error: unknown): void {
    const ended = error instanceof ApiError && error.code === ATTEMPT_ENDED;
    if (ended) this.#editor?.setReadOnly(true);
    this.#showBanner(
      "refused",
      h("p", { class: "banner-text" }, badge("✕", "not saved", "fail"), " ", messageOf(error), ended ? "; this tab is read-only now" : ""),
    );
    this.#events.announce(`not saved: ${messageOf(error)}`);
  }

  #showBanner(kind: string, ...content: Node[]): void {
    this.#banner.className = `file-banner is-${kind}`;
    this.#banner.setAttribute("role", "alert");
    this.#banner.replaceChildren(...content);
    this.#banner.hidden = false;
  }

  #hideBanner(): void {
    this.#banner.hidden = true;
    this.#banner.removeAttribute("role");
    this.#banner.replaceChildren();
  }
}

/** The tab's mark of unsaved changes: a dot in place of its close button, until hovered. */
export function markTab(tab: HTMLElement, path: string, modified: boolean): void {
  tab.classList.toggle("is-modified", modified);
  const name = path.slice(path.lastIndexOf("/") + 1);
  tab.setAttribute("aria-label", modified ? `${name}, unsaved changes` : name);
  tab.title = modified ? `${path} · unsaved changes` : path;
  if (modified && !tab.querySelector(".tab-dot")) {
    tab.querySelector(".tab-close")?.before(h("span", { class: "tab-dot", "aria-hidden": "true" }, "●"));
  }
}

function generatedNote(document: FileDocument): HTMLElement | null {
  if (document.origin !== GENERATED_ORIGIN) return null;
  return h(
    "p",
    { class: "file-note" },
    h("span", { class: "file-note-origin" }, originText(document.origin, document.level)),
    " generated by cstudy: edit it as you like, it never changes a grade",
  );
}
