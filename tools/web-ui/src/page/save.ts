/**
 * Saving an open file (docs/specs/web-ui.md#file-api-rules, docs/specs/web-ui.md#editor): only
 * when asked, with Cmd or Ctrl-S, over the version the tab last read or saved. When the file
 * changed or went elsewhere since, the save is a conflict, and the tab offers to reload their
 * version or to overwrite it with the tab's on purpose. Unsaved files are tracked across the page,
 * so leaving the view or the page asks first.
 */

import { ApiError } from "./api.ts";
import { type Conflict, conflictOf, type SavedFile } from "./files.ts";
import type { FileDocument } from "./types.ts";

/** What `FileSaver` needs of the file API. */
export interface SavingFiles {
  save(path: string, text: string, sha256: string): Promise<SavedFile>;
  create(path: string, text: string): Promise<SavedFile>;
  read(path: string): Promise<FileDocument>;
}

/** What `FileSaver` needs of the editor: the editor module's `Editor` has all of it. */
export interface EditedText {
  readonly text: string;
  /** Whether the text differs from the text last set or marked saved. */
  readonly modified: boolean;
  markSaved(): void;
  /** Shows `text` in its place, changing only what differs, so the cursor stays put. */
  replaceText(text: string): void;
}

export type SaveOutcome =
  | { readonly kind: "saved"; readonly sha256: string }
  | { readonly kind: "unchanged" }
  /** The tab took the version on disk, which changed elsewhere. */
  | { readonly kind: "reloaded" }
  | { readonly kind: "conflict"; readonly conflict: Conflict };

const NOT_FOUND = "not_found";

/** One open file's saves. Any refusal but a conflict reaches the caller as an `ApiError`. */
export class FileSaver {
  readonly #files: SavingFiles;
  readonly #path: string;
  readonly #text: EditedText;
  #sha256: string;
  #conflict: Conflict | null = null;

  constructor(files: SavingFiles, path: string, sha256: string, text: EditedText) {
    this.#files = files;
    this.#path = path;
    this.#sha256 = sha256;
    this.#text = text;
  }

  /** The `ETag` of the version the tab last read or saved. */
  get sha256(): string {
    return this.#sha256;
  }

  /** The conflict the last save met; null once a save, an overwrite or a reload settles it. */
  get conflict(): Conflict | null {
    return this.#conflict;
  }

  save(): Promise<SaveOutcome> {
    if (!this.#text.modified && this.#conflict === null) return Promise.resolve({ kind: "unchanged" });
    const text = this.#text.text;
    return this.#store(text, () => this.#files.save(this.#path, text, this.#sha256));
  }

  /** Saves the tab's text over their version on purpose, or writes it again where theirs is gone. */
  overwrite(): Promise<SaveOutcome> {
    const text = this.#text.text;
    const theirs = this.#conflict?.theirs ?? null;
    if (theirs === null) return this.#store(text, () => this.#files.create(this.#path, text));
    return this.#store(text, () => this.#files.save(this.#path, text, theirs));
  }

  /** Shows their version in place of the tab's text; "gone" when no file is there any more. */
  async reloadTheirs(): Promise<"reloaded" | "gone"> {
    const document = await this.#theirs();
    if (document === null) return "gone";
    this.#take(document);
    return "reloaded";
  }

  /**
   * Follows a change on disk that a notification names by the SHA-256 of the file now: none
   * when the tab holds that version already, as after its own save; their version in place of
   * the tab's text when the tab has no unsaved edits; else a conflict, which keeps the edits.
   * A file gone from disk is always a conflict, so the tab's text stays until the user chooses.
   */
  async follow(theirs: string | null): Promise<SaveOutcome> {
    if (theirs === this.#sha256) return { kind: "unchanged" };
    if (theirs === null || this.#text.modified) return this.#conflicted(theirs);
    const document = await this.#theirs();
    if (document?.sha256 === this.#sha256) return { kind: "unchanged" };
    // Text typed while the file was read stays, and the change is then a conflict.
    if (document === null || this.#text.modified) return this.#conflicted(document?.sha256 ?? null);
    this.#take(document);
    return { kind: "reloaded" };
  }

  #conflicted(theirs: string | null): SaveOutcome {
    const message = theirs === null ? `${this.#path} was deleted on disk` : `${this.#path} changed on disk`;
    this.#conflict = { theirs, message };
    return { kind: "conflict", conflict: this.#conflict };
  }

  /** The version on disk; null when no file is there. */
  async #theirs(): Promise<FileDocument | null> {
    try {
      return await this.#files.read(this.#path);
    } catch (error) {
      if (error instanceof ApiError && error.code === NOT_FOUND) return null;
      throw error;
    }
  }

  #take(document: FileDocument): void {
    this.#text.replaceText(document.text ?? "");
    this.#text.markSaved();
    this.#sha256 = document.sha256;
    this.#conflict = null;
  }

  async #store(text: string, write: () => Promise<SavedFile>): Promise<SaveOutcome> {
    let saved: SavedFile;
    try {
      saved = await write();
    } catch (error) {
      const conflict = conflictOf(error);
      if (conflict === null) throw error;
      this.#conflict = conflict;
      return { kind: "conflict", conflict };
    }
    this.#sha256 = saved.sha256;
    this.#conflict = null;
    // Text typed while the save was on its way stays unsaved.
    if (this.#text.text === text) this.#text.markSaved();
    return { kind: "saved", sha256: saved.sha256 };
  }
}

/** The fields of a key press the save shortcut depends on. */
export type KeyPress = Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "shiftKey">;

export function isSaveShortcut(event: KeyPress): boolean {
  return (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "s";
}

/** `⌘S` on macOS, `Ctrl-S` elsewhere, from `navigator.platform`. */
export function saveShortcutLabel(platform: string): string {
  return /^Mac/.test(platform) ? "⌘S" : "Ctrl-S";
}

type UnsavedSource = () => readonly string[];

const unsavedSources = new Set<UnsavedSource>();

/** Counts the paths `source` names as unsaved in every warning; the function returned stops it. */
export function trackUnsaved(source: UnsavedSource): () => void {
  unsavedSources.add(source);
  return () => unsavedSources.delete(source);
}

export function unsavedPaths(): string[] {
  return [...unsavedSources].flatMap((source) => source());
}

/** The question before leaving with unsaved files; null when nothing is unsaved. */
export function leaveWarning(paths: readonly string[]): string | null {
  if (paths.length === 0) return null;
  const what = paths.length === 1 ? `${paths[0]} has` : `${paths.length} files have`;
  const which = paths.length === 1 ? "" : `: ${paths.join(", ")}`;
  return `${what} unsaved changes${which}. Leave and lose them?`;
}
