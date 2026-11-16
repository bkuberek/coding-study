/** What the Settings view's bar says of unsaved changes and of a Save (docs/specs/web-ui.md#settings-view). */

import { FOLDER_OF, practiceFiles } from "./removal-model.ts";

/** A word of a line that leads to a view: `Health` in `next: Fix in Health installs it`. */
export interface LineLink {
  readonly text: string;
  readonly href: string;
}

/** How one store's part of a Save ended; null when it held no change. */
export type StoreOutcome =
  | { readonly saved: string; readonly notes?: readonly string[]; readonly link?: LineLink }
  | { readonly error: string }
  | null;

export interface SaveLine {
  readonly text: string;
  readonly failed: boolean;
  readonly link?: LineLink;
}

export function changesText(count: number): string {
  return count === 1 ? "1 change" : `${count} changes`;
}

/** One line per store that held a change, so a failure in one says which and the other its result;
 * in the order a Save writes them. */
export function saveLines(config: StoreOutcome, credentials: StoreOutcome, languages: StoreOutcome, preferences: StoreOutcome): readonly SaveLine[] {
  return [lineOf("config.toml", config), lineOf("credentials.toml", credentials), lineOf("languages", languages), lineOf("preferences", preferences)].flat();
}

function lineOf(store: string, outcome: StoreOutcome): readonly SaveLine[] {
  if (outcome === null) return [];
  if ("error" in outcome) return [{ text: `${store} not saved: ${outcome.error}`, failed: true }];
  const line: SaveLine = { text: `${store} ${outcome.saved}`, failed: false, ...(outcome.link === undefined ? {} : { link: outcome.link }) };
  return [line, ...(outcome.notes ?? []).map((note) => ({ text: note, failed: false }))];
}

/** A line's text in the parts its link splits it into; one plain part for a line with none. */
export function lineParts(line: SaveLine): readonly { readonly text: string; readonly href?: string }[] {
  const at = line.link === undefined ? -1 : line.text.indexOf(line.link.text);
  if (line.link === undefined || at < 0) return [{ text: line.text }];
  const { text, href } = line.link;
  return [{ text: line.text.slice(0, at) }, { text, href }, { text: line.text.slice(at + text.length) }].filter((part) => part.text !== "");
}

/** The workspace's languages as they are (`GET /api/v1/languages`). */
export interface LanguagesRead {
  readonly languages: readonly string[];
  readonly chosen: boolean;
}

/** What `POST /api/v1/languages` answers. */
export interface LanguagesChanged extends LanguagesRead {
  readonly added: readonly string[];
  readonly removed: readonly string[];
  readonly deleted: readonly { readonly path: string; readonly files: number }[];
  /** The CLI's note for each attempt in progress in a removed language. */
  readonly notes: readonly string[];
}

export interface LanguageChange {
  readonly add: readonly string[];
  readonly remove: readonly string[];
}

/** What staging the boxes `now` adds to and removes from the workspace's languages `base`, each
 * in the order of `order` (the order `cstudy lang` keeps). */
export function languageChange(base: readonly string[], now: readonly string[], order: readonly string[]): LanguageChange {
  return {
    add: order.filter((language) => now.includes(language) && !base.includes(language)),
    remove: order.filter((language) => base.includes(language) && !now.includes(language)),
  };
}

/** The commands a Save runs for the staged languages, which keep a removed folder. */
export function languageCommands({ add, remove }: LanguageChange): readonly string[] {
  return [...(add.length > 0 ? [`cstudy lang add ${add.join(" ")}`] : []), ...(remove.length > 0 ? [`cstudy lang remove ${remove.join(" ")}`] : [])];
}

const HEALTH: LineLink = { text: "Health", href: "#/health" };
const TOOLCHAIN = "next: Fix in Health installs its toolchain files";

/** What a saved change of languages says: what was added, and for each removed language what
 * became of its folder, with a way to the Health view after an add. */
export function languagesSaved(changed: LanguagesChanged): { readonly saved: string; readonly notes?: readonly string[]; readonly link?: LineLink } {
  const added = changed.added.length > 0 ? [`added ${changed.added.join(", ")}`] : [];
  const removed = changed.removed.map((language) => {
    const folder = FOLDER_OF[language] ?? `${language}/`;
    const gone = changed.deleted.find((entry) => entry.path === folder);
    return gone === undefined ? `${language} removed: ${folder} stays on disk` : `${language} removed: ${folder} deleted (${practiceFiles(gone.files)})`;
  });
  const items = [...added, ...removed, ...(changed.added.length > 0 ? [TOOLCHAIN] : [])];
  return {
    saved: `saved in .cs/workspace.toml: ${items.join(" · ")}`,
    ...(changed.notes.length > 0 ? { notes: changed.notes.map((note) => `note: ${note}`) } : {}),
    ...(changed.added.length > 0 ? { link: HEALTH } : {}),
  };
}
