/**
 * The code of an attempt that is over, read-only (docs/specs/web-ui.md#past-attempt-files): under
 * an attempt of the Problem view's History, where its files come from and a button that opens them
 * in a dialog, in the editor with its highlighting but read-only, with no save and no run. It is a
 * chunk of its own, fetched when the row of an attempt that is over is first opened (NFR-12).
 */

import "./pastFiles.css";

import type { Editor, EditorOptions } from "../editor.ts";
import type { Api } from "./api.ts";
import type { PageContext } from "./context.ts";
import { openSheet } from "./dialogs.ts";
import { badge, type Child, h, nodes } from "./dom.ts";
import { failure, loading } from "./states.ts";
import type { FilesSource, PastAttempt, PastFileDocument, PastFilesDocument } from "./types.ts";

const ATTEMPTS = "/api/v1/attempts";

export function pastFilesUrl(attemptId: number): string {
  return `${ATTEMPTS}/${attemptId}/past-files`;
}

export function pastFileUrl(attemptId: number, path: string): string {
  return `${pastFilesUrl(attemptId)}/${path.split("/").map(encodeURIComponent).join("/")}`;
}

/** Where the files come from, said after the mark's word. */
export function sourceDetail(files: Pick<PastFilesDocument, "source" | "root">): string {
  switch (files.source) {
    case "archive":
      return `moved to ${files.root ?? ".archive/"} when the next attempt started`;
    case "current":
      return "they may have been edited after this attempt ended";
    case "missing":
      return "they were never archived, or were deleted";
  }
}

/** The mark of where the files come from: a word and a glyph, never colour alone. */
export function sourceBadge(source: FilesSource): { readonly glyph: string; readonly text: string; readonly tone: string } {
  switch (source) {
    case "archive":
      return { glyph: "", text: "archived", tone: "info" };
    case "current":
      return { glyph: "!", text: "current files", tone: "warn" };
    case "missing":
      return { glyph: "", text: "not available", tone: "quiet" };
  }
}

/** What the button that opens the files says: the file's name, or how many there are. */
export function openText(entries: PastFilesDocument["entries"]): string {
  const [only, ...more] = entries;
  return only !== undefined && more.length === 0 ? `View ${only.path}` : `View code · ${entries.length} files`;
}

/** The dialog's title. */
export function viewerTitle(slug: string, attempt: Pick<PastAttempt, "attempt_id" | "language">): string {
  return ["code", slug, `attempt ${attempt.attempt_id}`, attempt.language].filter(Boolean).join(" · ");
}

/** What shows in place of a file the editor cannot show. */
export function withoutTextNote(file: Pick<PastFileDocument, "path" | "size">): string {
  return `${file.path} is not UTF-8 text or is over 1 MiB (${file.size} bytes), so it opens read-only without its text.`;
}

/** The editor of a past file: always read-only, with the page's theme and Vim keybindings. */
export function viewerOptions(
  parent: HTMLElement,
  file: PastFileDocument & { readonly text: string },
  page: Pick<PageContext, "nonce" | "preferences">,
): EditorOptions {
  const { theme, vim } = page.preferences();
  return { parent, path: file.path, text: file.text, nonce: page.nonce, theme, vim, readOnly: true };
}

export function readPastFiles(api: Api, attemptId: number): Promise<PastFilesDocument> {
  return api.get(pastFilesUrl(attemptId));
}

export function readPastFile(api: Api, attemptId: number, path: string): Promise<PastFileDocument> {
  return api.get(pastFileUrl(attemptId, path));
}

/** Fills `host`, the files block under a History row, with where the attempt's files come from
 * and the button that opens them. */
export function showPastFiles(context: PageContext, slug: string, attempt: PastAttempt, host: HTMLElement): void {
  host.replaceChildren(loading("looking for the files…"));
  readPastFiles(context.api, attempt.attempt_id)
    .then((files) => host.replaceChildren(filesBlock(context, slug, attempt, files)))
    .catch((error: unknown) => host.replaceChildren(failure(error)));
}

/** The mark of the files' source and where they come from, after any `before`. */
function sourceLine(className: string, files: PastFilesDocument, ...before: Child[]): HTMLElement {
  const mark = sourceBadge(files.source);
  return h("p", { class: className }, ...before.flatMap((child) => [child, " "]), badge(mark.glyph, mark.text, mark.tone), " ", sourceDetail(files));
}

function filesBlock(context: PageContext, slug: string, attempt: PastAttempt, files: PastFilesDocument): HTMLElement {
  const open = h("button", { type: "button", class: "button" }, openText(files.entries));
  open.addEventListener("click", () => openViewer(context, viewerTitle(slug, attempt), attempt.attempt_id, files));
  return h(
    "div",
    { class: "past-block" },
    sourceLine("past-source", files),
    files.entries.length > 0 ? h("p", { class: "past-open" }, open) : null,
  );
}

/** A dialog with the attempt's files: a picker when there are several, and the file open in a
 * read-only editor. */
function openViewer(context: PageContext, title: string, attemptId: number, files: PastFilesDocument): void {
  const sheet = openSheet(title, true);
  const message = h("div", { class: "past-message", hidden: true });
  const host = h("div", { class: "past-editor" });
  const picks = files.entries.map(({ path }) => {
    const button = h("button", { type: "button", class: "button past-pick", "aria-pressed": "false" }, path);
    button.addEventListener("click", () => void show(path));
    return { path, button };
  });
  const picker =
    picks.length > 1
      ? h("ul", { class: "plain past-picker", "aria-label": "Files of this attempt" }, ...picks.map(({ button }) => h("li", {}, button)))
      : null;
  let editor: Editor | null = null;
  let requested = 0;
  let closed = false;

  function showMessage(...content: Child[]): void {
    message.replaceChildren(...nodes(content));
    message.hidden = false;
    host.hidden = true;
  }

  async function show(path: string): Promise<void> {
    const request = ++requested;
    for (const pick of picks) pick.button.setAttribute("aria-pressed", String(pick.path === path));
    try {
      const file = await readPastFile(context.api, attemptId, path);
      if (request !== requested || closed) return;
      if (file.text === null) {
        showMessage(withoutTextNote(file));
        return;
      }
      const shown = { ...file, text: file.text };
      message.hidden = true;
      host.hidden = false;
      if (editor === null) {
        const { createEditor } = await import("../editor.ts");
        const created = await createEditor(viewerOptions(host, shown, context));
        if (closed || request !== requested) {
          created.destroy();
          return;
        }
        editor = created;
      } else {
        await editor.setDocument(shown.path, shown.text);
      }
      context.shell.announce(`${file.path} shown, read-only`);
    } catch (error) {
      if (request === requested && !closed) showMessage(failure(error));
    }
  }

  const note = sourceLine("file-note past-note", files, badge("", "read-only", "quiet"));
  sheet.body.append(...nodes([note, picker, message, host]));
  const followPreferences = context.onPreferences((preferences) => {
    editor?.setTheme(preferences.theme);
    void editor?.setVim(preferences.vim);
  });
  const leave = () => sheet.close();
  window.addEventListener("hashchange", leave);
  void sheet.closed.then(() => {
    closed = true;
    followPreferences();
    window.removeEventListener("hashchange", leave);
    editor?.destroy();
  });
  const first = picks[0];
  if (first !== undefined) void show(first.path);
}
