/**
 * The Settings view's Profile section (docs/specs/web-ui.md#settings-view): the workspace's
 * languages as checkboxes, which stage an add or a removal until the bar's Save, then the config
 * form's roles and domains, drawn by the same code as the rest of `config.toml`.
 */

import type { PageContext } from "../context.ts";
import { command, h } from "../dom.ts";
import { type LanguageChange, languageChange, languageCommands, type LanguagesChanged, languagesSaved, type StoreOutcome } from "../settings-model.ts";

const LANGUAGES = "/api/v1/languages";
const NEEDS_ONE = "a workspace needs at least one language";
const ALL_SIX = "all six (none chosen)";
const MARKER_FILE = ".cs/workspace.toml";

/** What a Save asks of the languages: whether a removal also deletes the folders, once the second
 * confirmation said so. */
export interface LanguageSave {
  readonly deleteFolders: boolean;
}

export interface LanguagesStage {
  readonly element: HTMLElement;
  /** What the boxes stage against the workspace's languages. */
  changes(): LanguageChange;
  /** How many boxes differ, for the bar's count. */
  count(): number;
  /** Brings what follows from the boxes up to them: the marks, the last box, the notes. */
  sync(): void;
  /** Puts the boxes back to the workspace's languages. */
  undo(): void;
  /** Takes the page's copy of the profile as the workspace's languages, unless boxes are staged. */
  follow(): void;
  /** Writes the staged change through `POST /api/v1/languages` and says what became of it. A
   * refusal rejects, and the boxes stay as they are. */
  save(how: LanguageSave): Promise<Extract<StoreOutcome, { saved: string }>>;
}

export function languagesStage(context: PageContext): LanguagesStage {
  const order = context.session.languages;
  let base = [...context.session.profile.languages];
  let chosen = context.session.profile.languages_chosen;
  const note = h("p", { id: "profile-languages-note", class: "quiet" }, NEEDS_ONE);
  const everything = h("span", { class: "profile-chosen quiet" }, ALL_SIX);
  const boxes = new Map(
    order.map((language) => [language, h("input", { type: "checkbox", id: `profile-lang-${language}`, value: language, checked: base.includes(language) })]),
  );
  const strip = h("p", { class: "profile-commands quiet" });
  const element = h(
    "fieldset",
    { class: "profile-group", id: "profile-languages" },
    h("legend", {}, "Languages ", everything),
    h("p", { class: "quiet" }, "this workspace: ", h("code", { class: "config-name" }, MARKER_FILE), ", as ", command("cstudy lang"), " does"),
    h("div", { class: "profile-options" }, ...[...boxes].map(([language, box]) => h("div", { class: "profile-option" }, box, h("label", { for: box.id }, language)))),
    note,
    strip,
  );
  const checked = () => [...boxes].filter(([, box]) => box.checked).map(([language]) => language);
  const changes = () => languageChange(base, checked(), order);
  const count = () => {
    const { add, remove } = changes();
    return add.length + remove.length;
  };
  const sync = () => {
    const held = [...boxes.values()].filter((box) => box.checked);
    // The last one cannot go: a workspace needs a language.
    const last = held.length === 1 ? held[0] : undefined;
    for (const box of boxes.values()) {
      box.disabled = box === last;
      if (box === last) box.setAttribute("aria-describedby", note.id);
      else box.removeAttribute("aria-describedby");
    }
    note.hidden = last === undefined;
    everything.hidden = chosen || held.length < boxes.size;
    element.classList.toggle("changed", count() > 0);
    const commands = languageCommands(changes());
    strip.hidden = commands.length === 0;
    strip.replaceChildren("Save runs ", ...commands.flatMap((text, index) => [index > 0 ? " · " : "", command(text)]));
  };
  const draw = () => {
    for (const [language, box] of boxes) box.checked = base.includes(language);
  };
  return {
    element,
    changes,
    count,
    sync,
    undo: draw,
    follow() {
      if (count() > 0) return;
      base = [...context.session.profile.languages];
      chosen = context.session.profile.languages_chosen;
      draw();
      sync();
    },
    async save({ deleteFolders }) {
      const { add, remove } = changes();
      const changed = await context.api.post<LanguagesChanged>(LANGUAGES, { add, remove, delete_folders: deleteFolders, confirm: deleteFolders });
      base = [...changed.languages];
      chosen = changed.chosen;
      // The Problems, Guides and Mock views drawn after this one use the new profile.
      await context.refreshProfile().catch(() => undefined);
      draw();
      return languagesSaved(changed);
    },
  };
}
