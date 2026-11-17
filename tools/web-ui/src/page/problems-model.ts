/** The pure rules of the Problems view (docs/specs/web-ui.md#problems-view). */

import { statusWords } from "./format.ts";

/** `cstudy list --search`: the slug or the title holds the text, in any case. */
export function matchesSearch(entry: { readonly slug: string; readonly title: string }, text: string): boolean {
  const wanted = text.trim().toLowerCase();
  return entry.slug.toLowerCase().includes(wanted) || entry.title.toLowerCase().includes(wanted);
}

/** A filter's value in words: `in_progress` reads `in progress`, and its value stays in the route. */
export function choiceWords(key: string, value: string): string {
  return key === "status" ? statusWords(value) : value;
}

/** `1 problem`, `8 problems`. */
export function counted(number: number, word: string): string {
  return `${number} ${word}${number === 1 ? "" : "s"}`;
}

/** `8 of 292`; just what shows, when the whole list could not be read. */
export function countWords(shown: number, whole: number | null): string {
  return whole === null ? String(shown) : `${shown} of ${whole}`;
}

/** The columns the table can show, in its order (`domain/preferences.py` holds the same). */
export const PROBLEM_COLUMNS = ["checked_by", "problem", "difficulty", "pattern", "kind", "scope", "domain", "role", "status", "due", "languages", "sets"] as const;
export type ProblemColumn = (typeof PROBLEM_COLUMNS)[number];
export const DEFAULT_COLUMNS: readonly ProblemColumn[] = ["checked_by", "problem", "difficulty", "pattern", "status", "due", "languages", "sets"];
const REQUIRED_COLUMNS: readonly ProblemColumn[] = ["problem", "status"];

/** A column's name in the header and the columns menu: `checked_by` reads `checked by`. */
export function columnLabel(column: ProblemColumn): string {
  return column.replaceAll("_", " ");
}

/** What the Checked by column shows of `checked_by`: `tests`, `tests + rubric` or `rubric + AI review`. */
export function checkedWords(checkedBy: readonly string[]): string {
  return checkedBy.map((how) => (how === "ai-review" ? "AI review" : how)).join(" + ");
}

export function canHide(column: ProblemColumn): boolean {
  return !REQUIRED_COLUMNS.includes(column);
}

/** What the table shows of the stored columns: in its order, and always the required ones. */
export function shownColumns(stored: readonly string[]): readonly ProblemColumn[] {
  return PROBLEM_COLUMNS.filter((column) => !canHide(column) || stored.includes(column));
}

export function withColumn(stored: readonly string[], column: ProblemColumn, shown: boolean): readonly ProblemColumn[] {
  return shownColumns(shown ? [...stored, column] : stored.filter((found) => found !== column));
}
