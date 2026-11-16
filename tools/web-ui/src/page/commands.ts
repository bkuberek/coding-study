/**
 * The `cstudy` command each view mirrors, shown above it, so the page always says what the terminal
 * would run (docs/specs/web-ui.md#keyboard-and-accessibility: each control names its command).
 */

import { DIMENSIONS, type Dimension, LABEL_DIMENSIONS, widenFlags } from "./filter-model.ts";
import { FILTER_KEYS, type FilterKey, type Filters, type GuideFilterKey, type GuideFilters } from "./routes.ts";

/** The filters `cstudy next` takes from the list's: set, track, pattern, difficulty, language, the
 * labels and the widening, which names roles and domains only: a pick starts in a workspace language. */
export const NEXT_FILTERS: readonly FilterKey[] = ["set", "track", "widen", "pattern", "difficulty", "lang", "domain", "role", "scope"];

/** The Guides view's filters that `cstudy learn` takes; its path has no flag, since `--path` shows
 * a path's steps. */
export const LEARN_FILTERS: readonly GuideFilterKey[] = ["domain", "role", "widen", "level", "status", "search"];

export function listCommand(filters: Filters): string {
  return withFlags("cstudy list", filters, FILTER_KEYS, DIMENSIONS);
}

export function nextCommand(filters: Filters): string {
  return withFlags("cstudy next", filters, NEXT_FILTERS, LABEL_DIMENSIONS);
}

export function learnCommand(filters: GuideFilters): string {
  return withFlags("cstudy learn", filters, LEARN_FILTERS, LABEL_DIMENSIONS);
}

/** `cstudy start <slug>`, with `--lang` unless the problem has no choice of language. */
export function startCommand(slug: string, language: string | null): string {
  return language === null ? `cstudy start ${slug}` : `cstudy start ${slug} --lang ${language}`;
}

/** The flag of a filter whose key is shorter than it: the page's `checked` is `--checked-by`. */
const FLAG_NAMES: Readonly<Record<string, string>> = { checked: "checked-by" };

/** Each filter is the flag of its key (`track`, `--track`) or of its entry in `FLAG_NAMES`, which a
 * test holds to the real flags; the widening is one `--widen` per dimension the command `takes`
 * that the route drops, or `--widen all`, at the place of `widen` among the keys. */
function withFlags<Key extends string>(command: string, filters: Partial<Record<Key, string>>, keys: readonly Key[], takes: readonly Dimension[]): string {
  const flags = keys.flatMap((key) => {
    if (key === "widen") return widenFlags(filters, takes);
    const value = filters[key];
    return value ? [`--${FLAG_NAMES[key] ?? key} ${quoted(value)}`] : [];
  });
  return [command, ...flags].join(" ");
}

/** A value as a shell takes it: quoted only when it holds anything but safe characters. */
export function quoted(value: string): string {
  return /^[\w.,:/@+-]+$/.test(value) ? value : `'${value.replaceAll("'", "'\\''")}'`;
}
