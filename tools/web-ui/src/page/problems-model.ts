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
