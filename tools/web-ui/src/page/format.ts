/** How the page writes times and statuses: the terminal's wording, never colour alone. */

const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;

/** `12:31`, or `1:02:03` from an hour on. */
export function clock(totalSeconds: number): string {
  const seconds = Math.max(Math.floor(totalSeconds), 0);
  const hours = Math.floor(seconds / SECONDS_PER_HOUR);
  const minutes = Math.floor((seconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
  const rest = String(seconds % SECONDS_PER_MINUTE).padStart(2, "0");
  return hours > 0 ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

/** The attempt's timer (docs/specs/web-ui.md#attempt-view): `12:31 / 25:00`, `over by 3:10` past
 * the time box, or the elapsed time alone without one. */
export function timerText(elapsedSeconds: number, limitSeconds: number | null): string {
  if (limitSeconds === null) return clock(elapsedSeconds);
  if (elapsedSeconds > limitSeconds) return `over by ${clock(elapsedSeconds - limitSeconds)}`;
  return `${clock(elapsedSeconds)} / ${clock(limitSeconds)}`;
}

/** Seconds from an ISO instant to `now`. */
export function secondsSince(instant: string, now: number): number {
  return Math.max((now - Date.parse(instant)) / 1000, 0);
}

export interface Badge {
  /** A glyph beside the text; the text alone carries the meaning. */
  readonly glyph: string;
  readonly text: string;
  /** The stylesheet's tone: `ok`, `warn`, `fail`, `info` or `quiet`. */
  readonly tone: string;
}

const PROBLEM_STATUSES: Readonly<Record<string, Badge>> = {
  new: { glyph: "○", text: "new", tone: "quiet" },
  attempted: { glyph: "◐", text: "attempted", tone: "warn" },
  passed: { glyph: "✓", text: "passed", tone: "ok" },
  due: { glyph: "●", text: "due", tone: "fail" },
  mastered: { glyph: "◆", text: "mastered", tone: "info" },
};

const FILE_STATES: Readonly<Record<string, Badge>> = {
  unchanged: { glyph: "", text: "unchanged", tone: "quiet" },
  modified: { glyph: "M", text: "modified", tone: "warn" },
  added: { glyph: "A", text: "added", tone: "ok" },
  deleted: { glyph: "D", text: "deleted", tone: "fail" },
};

const CHECKS: Readonly<Record<string, Badge>> = {
  ok: { glyph: "✓", text: "ok", tone: "ok" },
  warn: { glyph: "!", text: "WARN", tone: "warn" },
  fail: { glyph: "✕", text: "FAIL", tone: "fail" },
};

/** A `cstudy list` status. */
export function problemBadge(status: string): Badge {
  return PROBLEM_STATUSES[status] ?? { glyph: "·", text: status, tone: "quiet" };
}

/** A project file's state against what `cstudy` provided, or none for other attempts. */
export function fileBadge(state: string | null): Badge | null {
  if (state === null) return null;
  return FILE_STATES[state] ?? { glyph: "?", text: state, tone: "quiet" };
}

/** A `cstudy doctor` row's status. */
export function checkBadge(status: string): Badge {
  return CHECKS[status] ?? { glyph: "?", text: status, tone: "quiet" };
}

/** Where a file comes from, as the tree says it: `starter`, `level 2 test`, `yours`. */
export function originText(origin: string, level: number | null): string {
  if (origin === "level") return level === null ? "level test" : `level ${level} test`;
  return origin;
}

/** `41m 02s`, as `cstudy done` and `cstudy history` write a solve time. */
export function solveTime(seconds: number): string {
  const minutes = Math.floor(seconds / SECONDS_PER_MINUTE);
  return `${minutes}m ${String(seconds % SECONDS_PER_MINUTE).padStart(2, "0")}s`;
}

/** `2026-10-24 09:12` in local time. */
export function localMinute(instant: string): string {
  const date = new Date(instant);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
