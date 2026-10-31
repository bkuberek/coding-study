/**
 * The `cstudy` command each view mirrors, shown above it, so the page always says what the terminal
 * would run (docs/specs/web-ui.md#keyboard-and-accessibility: each control names its command).
 */

import { FILTER_KEYS, type FilterKey, type Filters } from "./routes.ts";

const LIST_FLAGS: Readonly<Record<FilterKey, string>> = {
  track: "--track",
  kind: "--kind",
  lang: "--lang",
  difficulty: "--difficulty",
  status: "--status",
  content: "--content",
  pattern: "--pattern",
};

/** The filters `cstudy next` takes from the list's: track, pattern, difficulty and language. */
export const NEXT_FILTERS: readonly FilterKey[] = ["track", "pattern", "difficulty", "lang"];

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

function withFlags(command: string, filters: Filters, keys: readonly FilterKey[]): string {
  const flags = keys.flatMap((key) => {
    const value = filters[key];
    return value ? [`${LIST_FLAGS[key]} ${quoted(value)}`] : [];
  });
  return [command, ...flags].join(" ");
}

/** A value as a shell takes it: quoted only when it holds anything but safe characters. */
export function quoted(value: string): string {
  return /^[\w.,:/@+-]+$/.test(value) ? value : `'${value.replaceAll("'", "'\\''")}'`;
}
