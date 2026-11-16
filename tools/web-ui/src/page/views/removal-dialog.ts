/**
 * The question a Save that removes a language asks before any store is written
 * (docs/specs/web-ui.md#settings-view): keep the language's folder, which has the focus, delete it,
 * or cancel. Deleting turns the dialog into a second confirmation that shows, from
 * `GET /api/v1/languages/removal`, what goes, what stays and why, as `cstudy lang remove
 * --delete-folder` prints it before it asks.
 */

import type { PageContext } from "../context.ts";
import { command, h, nodes } from "../dom.ts";
import {
  deleteAction,
  deleteLines,
  FOLDER_OF,
  foldersOf,
  keepLines,
  removalCommand,
  type RemovalPreview,
  removalTitle,
  removalUrl,
  staysLine,
} from "../removal-model.ts";
import { failure, loading } from "../states.ts";
import type { LanguageSave } from "./profile-section.ts";

/** What the learner chose: how the removal goes on, or null for Cancel and Escape, which write nothing. */
export async function askRemoval(context: PageContext, languages: readonly string[]): Promise<LanguageSave | null> {
  let chunk: typeof import("../sheets.ts");
  try {
    chunk = await import("../sheets.ts");
  } catch (error) {
    context.shell.announce(`could not open: ${error instanceof Error ? error.message : String(error)}`);
    return null;
  }
  const sheet = chunk.openSheet(removalTitle(languages));
  let choice: LanguageSave | null = null;
  const choose = (save: LanguageSave) => {
    choice = save;
    sheet.close();
  };
  const cancel = () => h("button", { type: "button", class: "button", onclick: () => sheet.close() }, "Cancel");
  /** Each step takes the dialog's body, and the focus goes to its safe button. */
  let step = 0;
  const first = () => {
    step += 1;
    const keep = h("button", { type: "button", class: "button primary", onclick: () => choose({ deleteFolders: false }) }, "Keep the folder");
    const remove = h("button", { type: "button", class: "button", onclick: () => void second() }, "Delete the folder…");
    sheet.body.replaceChildren(
      ...nodes([
      h("p", { class: "question" }, languages.length === 1 ? "The folder holds your practice files." : "The folders hold your practice files."),
      h("p", { class: "sheet-command quiet" }, "as ", command(removalCommand(languages, false))),
      languages.length === 1 ? null : h("ul", { class: "plain" }, ...languages.map((language) => h("li", {}, `${language}: ${FOLDER_OF[language] ?? `${language}/`}`))),
      h("div", { class: "sheet-actions" }, cancel(), remove, keep),
      ]),
    );
    keep.focus();
  };
  const second = async () => {
    const mine = ++step;
    const back = h("button", { type: "button", class: "button", onclick: first }, "Back");
    const shown = (...content: (Node | null)[]) => {
      if (mine !== step) return;
      sheet.body.replaceChildren(...nodes(content));
      back.focus();
    };
    sheet.body.replaceChildren(loading("reading what goes…"));
    let preview: RemovalPreview;
    try {
      preview = await context.api.get<RemovalPreview>(removalUrl(languages));
    } catch (error) {
      shown(failure(error), h("div", { class: "sheet-actions" }, cancel(), back));
      return;
    }
    const blocked = preview.blocked.length > 0;
    const reasons = h("div", { id: "removal-blocked" }, ...preview.blocked.map((reason) => h("p", { class: "removal-reason" }, reason)));
    const remove = h(
      "button",
      { type: "button", class: "button danger", disabled: blocked, "aria-describedby": blocked ? reasons.id : null, onclick: () => choose({ deleteFolders: true }) },
      deleteAction(preview, languages),
    );
    const goes = deleteLines(preview);
    shown(
      h("p", { class: "sheet-command quiet" }, "as ", command(removalCommand(languages, true))),
      goes.length === 0
        ? h("p", { class: "question" }, `There is no folder to delete: ${foldersOf(languages).join(", ")} ${foldersOf(languages).length === 1 ? "is" : "are"} not there.`)
        : h("ul", { class: "plain removal-goes" }, ...goes.map((line) => h("li", {}, line))),
      preview.keep.length === 0 ? null : h("ul", { class: "plain removal-keeps" }, ...keepLines(preview).map((line) => h("li", {}, line))),
      h("p", { class: "quiet" }, staysLine(preview)),
      blocked ? reasons : null,
      goes.length === 0 ? null : h("p", { class: "question" }, "This can't be undone."),
      h("div", { class: "sheet-actions" }, cancel(), back, remove),
    );
  };
  first();
  await sheet.closed;
  return choice;
}
