/**
 * The `cstudy` command each view mirrors, shown above it, so the page always says what the terminal
 * would run (docs/specs/web-ui.md#keyboard-and-accessibility: each control names its command).
 */

import { FILTER_KEYS, type FilterKey, type Filters } from "./routes.ts";

/** The filters `cstudy next` takes from the list's: track, pattern, difficulty, language and the labels. */
export const NEXT_FILTERS: readonly FilterKey[] = ["track", "pattern", "difficulty", "lang", "domain", "role", "scope"];

export function listCommand(filters: Filters): string {
  return withFlags("cstudy list", filters, FILTER_KEYS);
}

export function nextCommand(filters: Filters): string {
  return withFlags("cstudy next", filters, NEXT_FILTERS);
}

/** `cstudy start <slug>`, with `--lang` unless the problem has no choice of language. */
export function startCommand(slug: string, language: string | null): string {
  return language === null ? `cstudy start ${slug}` : `cstudy start ${slug} --lang ${language}`;
}

/** Each filter is the flag of its key (`track`, `--track`), which a test holds to the real flags. */
function withFlags(command: string, filters: Filters, keys: readonly FilterKey[]): string {
  const flags = keys.flatMap((key) => {
    const value = filters[key];
    return value ? [`--${key} ${quoted(value)}`] : [];
  });
  return [command, ...flags].join(" ");
}

/** A value as a shell takes it: quoted only when it holds anything but safe characters. */
export function quoted(value: string): string {
  return /^[\w.,:/@+-]+$/.test(value) ? value : `'${value.replaceAll("'", "'\\''")}'`;
}
