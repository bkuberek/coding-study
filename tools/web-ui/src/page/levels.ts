/**
 * Level passes on the page (docs/specs/progress-and-scheduling.md#level-passes): a pass through
 * level N of M is a pass, and each language keeps its best and the level to try next. The words are
 * those of `cstudy history`, `cstudy status` and `cstudy done`. Only the Problem view and the Done
 * dialog read this module, so it stays out of what loads before a file is editable.
 */

import type { AttemptStatus, History, PastAttempt } from "./types.ts";

const PASSED = "passed";
const ITEM = "item";
const PROJECT = "project";
const MOCK = "mock";
const GAVE_UP = "giving up grades again";

function through(passed: number, last: number): string {
  return `through level ${passed} of ${last}`;
}

/** `passed through level 2 of 4` for a pass below the last level, else the status. */
export function pastStatus(attempt: Pick<PastAttempt, "status" | "levels_passed" | "levels_total">): string {
  const { status, levels_passed: passed, levels_total: last } = attempt;
  if (status !== PASSED || passed === null || last === null || passed < 1 || passed >= last) return status;
  return `${status} ${through(passed, last)}`;
}

/** `python through level 2 of 4 · kotlin through level 4 of 4`; null before any pass. */
export function bestLine(levels: History["levels"]): string | null {
  if (levels === null) return null;
  const passed = levels.languages.flatMap((mastery) => (mastery.best === null ? [] : [`${mastery.language} ${through(mastery.best, levels.last)}`]));
  return passed.length ? passed.join(" · ") : null;
}

/** `python: last time: through level 2 of 4; try level 3`, for each language with a level to try. */
export function goalLines(levels: History["levels"]): string[] {
  if (levels === null) return [];
  return levels.languages.flatMap(({ language, last_time: lastTime, try_level: next }) =>
    lastTime === null || next === null ? [] : [`${language}: last time: ${through(lastTime, levels.last)}; try level ${next}`],
  );
}

/** What a rating takes, as `cstudy done` refuses it: a mock keeps every case. */
export function ratingRule(status: Pick<AttemptStatus, "kind" | "mode"> & { readonly levels: object | null }): string {
  if (status.kind === ITEM) return "an item takes a rating only, graded by it alone";
  if (status.levels === null || status.mode === MOCK) return `a rating needs the latest run to pass every case; ${GAVE_UP}`;
  const latest = status.kind === PROJECT ? "the latest submission of every unlocked level to pass level 1" : "the latest run to pass every case of level 1 at least";
  return `a rating needs ${latest}, and passes the attempt through the levels it passed; ${GAVE_UP}`;
}
