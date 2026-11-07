/** What the Sets view words and checks (docs/specs/web-ui.md#sets-view). */

import type { SetStanding } from "./types.ts";

const SET_NAME = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;
const SET_NAME_LENGTH = 64;

/** Why `name` can't name a set, as the page says it while typing; the server checks it too. */
export function setNameIssue(name: string): string | null {
  if (name === "") return "name the set";
  if (SET_NAME.test(name) && name.length <= SET_NAME_LENGTH) return null;
  return "use lowercase letters, digits and hyphens, starting with a letter, such as backend-loop";
}

/** `1 of 3 passed · 1 missing`, as `cstudy set list` writes it. */
export function standingWords(standing: SetStanding): string {
  const counts = `${standing.passed} of ${standing.total} passed`;
  return standing.missing.length ? `${counts} · ${standing.missing.length} missing` : counts;
}

/** The positions a row can move to, one step up or down; null at either end. */
export function movesOf(position: number, count: number): { readonly up: number | null; readonly down: number | null } {
  return { up: position > 1 ? position - 1 : null, down: position < count ? position + 1 : null };
}
