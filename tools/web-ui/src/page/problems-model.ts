/** The pure rules of the Problems view (docs/specs/web-ui.md#problems-view). */

import { statusWords } from "./format.ts";
import { FILTER_KEYS, type FilterKey, type Filters } from "./routes.ts";

/** `cstudy list --search`: the slug or the title holds the text, in any case. */
export function matchesSearch(entry: { readonly slug: string; readonly title: string }, text: string): boolean {
  const wanted = text.trim().toLowerCase();
  return entry.slug.toLowerCase().includes(wanted) || entry.title.toLowerCase().includes(wanted);
}

export interface ActiveFilter {
  readonly key: FilterKey;
  readonly value: string;
  /** `domain: security`, as its chip reads. */
  readonly words: string;
}

/** A filter's value in words: `in_progress` reads `in progress`, and its value stays in the route. */
export function choiceWords(key: FilterKey, value: string): string {
  return key === "status" ? statusWords(value) : value;
}

/** Each filter that shows as a chip. The search has none: its field already shows it. */
export function activeFilters(filters: Filters): readonly ActiveFilter[] {
  return FILTER_KEYS.flatMap((key) => {
    const value = filters[key];
    return key === "search" || !value ? [] : [{ key, value, words: `${key}: ${choiceWords(key, value)}` }];
  });
}

/** `8 of 292`; just what shows, when the whole list could not be read. */
export function countWords(shown: number, whole: number | null): string {
  return whole === null ? String(shown) : `${shown} of ${whole}`;
}

/** The columns the table can show, in its order (`domain/preferences.py` holds the same). */
export const PROBLEM_COLUMNS = ["id", "problem", "difficulty", "pattern", "kind", "scope", "domain", "role", "status", "due", "languages", "sets"] as const;
export type ProblemColumn = (typeof PROBLEM_COLUMNS)[number];
export const DEFAULT_COLUMNS: readonly ProblemColumn[] = ["id", "problem", "difficulty", "pattern", "status", "due", "languages"];
const REQUIRED_COLUMNS: readonly ProblemColumn[] = ["problem", "status"];

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
