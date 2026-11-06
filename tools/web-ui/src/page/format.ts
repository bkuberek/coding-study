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

/** The glyph and tone that mark a word, by the word: a status of `cstudy list` or a file's state. */
type Marks = Readonly<Record<string, readonly [glyph: string, tone: string]>>;

const PROBLEM_STATUSES: Marks = {
  new: ["○", "quiet"],
  in_progress: ["▸", "info"],
  attempted: ["◐", "warn"],
  passed: ["✓", "ok"],
  due: ["●", "fail"],
  mastered: ["◆", "info"],
};

const FILE_STATES: Marks = {
  unchanged: ["", "quiet"],
  modified: ["M", "warn"],
  added: ["A", "ok"],
  deleted: ["D", "fail"],
};

const CHECKS: Readonly<Record<string, Badge>> = {
  ok: { glyph: "✓", text: "ok", tone: "ok" },
  warn: { glyph: "!", text: "WARN", tone: "warn" },
  fail: { glyph: "✕", text: "FAIL", tone: "fail" },
};

/** The badge of a word as the CLI writes it; a word the table does not know gets `unknown` as its glyph. */
function wordBadge(marks: Marks, word: string, unknown: string): Badge {
  const [glyph, tone] = marks[word] ?? [unknown, "quiet"];
  return { glyph, text: word, tone };
}

/** A `cstudy list` status. */
export function problemBadge(status: string): Badge {
  return wordBadge(PROBLEM_STATUSES, status, "·");
}

/** A project file's state against what `cstudy` provided, or none for other attempts. */
export function fileBadge(state: string | null): Badge | null {
  return state === null ? null : wordBadge(FILE_STATES, state, "?");
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

/** `41m 02s`, `1h 05m` or `42s`, as `cstudy done` and `cstudy history` write a solve time. */
export function solveTime(totalSeconds: number): string {
  const seconds = Math.floor(totalSeconds);
  const hours = Math.floor(seconds / SECONDS_PER_HOUR);
  const minutes = Math.floor((seconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
  const pad = (value: number) => String(value).padStart(2, "0");
  if (hours > 0) return `${hours}h ${pad(minutes)}m`;
  if (minutes > 0) return `${minutes}m ${pad(seconds % SECONDS_PER_MINUTE)}s`;
  return `${seconds}s`;
}

/** A piece of a fix hint: plain text, or a web link whose `href` is its text. */
export interface FixPart {
  readonly text: string;
  readonly href?: string;
}

const WEB_LINK = /https?:\/\/[^\s<>"']+/g;
const LINK_TAIL = /[.,;:!?)\]]+$/;

/** A fix hint (`known.fix` of an error, a `doctor` row's `fix`) cut into text and links, the
 * punctuation after a link left out of it. */
export function fixParts(fix: string): FixPart[] {
  const parts: FixPart[] = [];
  let from = 0;
  for (const match of fix.matchAll(WEB_LINK)) {
    const href = match[0].replace(LINK_TAIL, "");
    if (match.index > from) parts.push({ text: fix.slice(from, match.index) });
    parts.push({ text: href, href });
    from = match.index + href.length;
  }
  if (from < fix.length) parts.push({ text: fix.slice(from) });
  return parts;
}

/** `2026-10-24 09:12` in local time. */
export function localMinute(instant: string): string {
  const date = new Date(instant);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
