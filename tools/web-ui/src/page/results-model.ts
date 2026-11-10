/**
 * The results panel's model (docs/specs/web-ui.md#attempt-view): a run's events folded into rows
 * as they come, and what the panel shows of them, in the terminal report's order and words
 * (docs/specs/cli.md#cstudy-test). Pure, so a replayed stream draws the same panel as a live one.
 */

import { timerText } from "./format.ts";
import type {
  CaseResult,
  CaseStatus,
  Closed,
  Diagnostic,
  LevelResult,
  LevelUnlocked,
  PerfResult,
  RunEnd,
  RunEvent,
  RunStart,
  StackState,
  StressResult,
  StressRun,
  TestResult,
} from "./run-events.ts";

export type RowStatus = CaseStatus | "running";

export interface CaseRow {
  readonly id: string;
  readonly visible: boolean;
  readonly oracle: boolean;
  readonly seed: number | null;
  readonly n: number | null;
  readonly level: number | null;
  readonly status: RowStatus;
  readonly result: CaseResult | null;
}

export interface TestRow {
  readonly id: string;
  readonly status: RowStatus;
  readonly result: TestResult | null;
}

export interface StressGroup {
  readonly id: string;
  readonly variant: string;
  /** A project's stress case in a submission: its level; null for a concurrent problem's. */
  readonly level: number | null;
  /** Each run's status by its number, filled in as runs end. */
  readonly runs: RowStatus[];
  readonly failures: StressRun[];
  result: StressResult | null;
}

export type ViewItem =
  | { readonly kind: "case"; readonly row: CaseRow }
  | { readonly kind: "test"; readonly row: TestRow }
  | { readonly kind: "file"; readonly path: string }
  /** Rows of one status counted instead of listed: `PASS  10 hidden cases`. */
  | { readonly kind: "count"; readonly status: RowStatus; readonly text: string }
  | { readonly kind: "more"; readonly text: string }
  | { readonly kind: "stress"; readonly group: StressGroup }
  | { readonly kind: "level"; readonly result: LevelResult };

/** A service project's stack as the run's notices left it. */
export interface StackStanding {
  readonly state: StackState;
  /** The startup once the stack was ready, which no limit or result counts. */
  readonly startup_s: number | null;
  /** Down, after the run, a failure or a cancel. */
  readonly down: boolean;
}

export interface Summary {
  readonly tone: "ok" | "warn" | "fail";
  readonly text: string;
  readonly notes: readonly string[];
}

export interface ResultsView {
  readonly items: readonly ViewItem[];
  /** The cases and tests started but not ended: the work in progress. */
  readonly running: readonly string[];
  readonly notice: string | null;
  readonly progress: { readonly done: number; readonly planned: number | null };
  readonly summary: Summary | null;
}

/** The report's words for a status. */
export const STATUS_WORDS: Readonly<Record<RowStatus, string>> = {
  pass: "PASS",
  fail: "FAIL",
  error: "ERROR",
  timeout: "TIMEOUT",
  tle: "TLE",
  invalid: "INVALID",
  stalled: "STALLED",
  not_run: "NOT RUN",
  skip: "SKIP",
  running: "RUN",
};

const SUMMARY_COUNTS: readonly (readonly [CaseStatus, string, string])[] = [
  ["fail", "failed", "failed"],
  ["invalid", "invalid", "invalid"],
  ["error", "error", "errors"],
  ["timeout", "timeout", "timeouts"],
  ["stalled", "stalled", "stalled"],
  ["tle", "tle", "tle"],
  ["not_run", "not run", "not run"],
];
const SHOWN_ORACLE_FAILURES = 3;
/** The one test of a service project's `cstudy test`. */
const SERVICE_TEST_ID = "commands.test";
const NOT_A_PROOF = "stress runs found no race (not a proof of thread safety)";

/** A run's events folded as they come; `close` takes the server's last message. */
export class RunModel {
  start: RunStart | null = null;
  build: { readonly seconds: number; readonly note: string | null } | null = null;
  end: RunEnd | null = null;
  closed: Closed | null = null;
  perf: PerfResult | null = null;
  unlocked: LevelUnlocked | null = null;
  notice: string | null = null;
  /** A service project's stack, from the stages its notices name; null for any other run. */
  stack: StackStanding | null = null;
  readonly diagnostics: Diagnostic[] = [];
  readonly levels: LevelResult[] = [];
  readonly cases = new Map<string, CaseRow>();
  readonly tests = new Map<string, TestRow>();
  readonly stress = new Map<string, StressGroup>();

  apply(event: RunEvent): void {
    switch (event.type) {
      case "run_start":
        this.start = event;
        return;
      case "output":
        this.notice = event.text;
        if (event.stack) this.stack = stackStanding(this.stack, event.stack, event.startup_s);
        return;
      case "build":
        this.build = event;
        return;
      case "case_start":
        this.notice = null;
        this.cases.set(event.id, {
          id: event.id,
          visible: event.visible,
          oracle: event.oracle === true,
          seed: event.seed ?? null,
          n: event.n ?? null,
          level: event.level,
          status: "running",
          result: null,
        });
        return;
      case "case_result":
      case "case_revised":
        this.notice = null;
        this.cases.set(event.id, caseRow(event));
        return;
      case "test_start":
        this.notice = null;
        this.tests.set(event.id, { id: event.id, status: "running", result: null });
        return;
      case "test_result":
        this.notice = null;
        this.tests.set(event.id, { id: event.id, status: event.status, result: event });
        return;
      case "stress_run_start":
        this.#group(event.id, event.variant, event.level).runs[event.run] = "running";
        return;
      case "stress_run": {
        const group = this.#group(event.id, event.variant, event.level);
        group.runs[event.run] = event.status;
        if (event.status !== "pass") group.failures.push(event);
        return;
      }
      case "stress_result":
        this.#group(event.id, event.variant, event.level).result = event;
        return;
      case "diagnostic":
        this.diagnostics.push(event);
        return;
      case "level_result":
        this.levels.push(event);
        return;
      case "level_unlocked":
        this.unlocked = event;
        return;
      case "perf_result":
        this.perf = event;
        return;
      case "run_end":
        this.end = event;
        this.notice = null;
    }
  }

  close(closed: Closed): void {
    this.closed = closed;
    this.notice = null;
  }

  #group(id: string, variant: string, level: number | undefined): StressGroup {
    const key = `${id}\u0000${variant}`;
    let group = this.stress.get(key);
    if (!group) {
      group = { id, variant, level: level ?? null, runs: [], failures: [], result: null };
      this.stress.set(key, group);
    }
    return group;
  }
}

/** The stack after a notice names `stage`: one that failed to start stays failed once it is down, and one that was ready keeps its startup. */
export function stackStanding(before: StackStanding | null, stage: StackState, startup_s: number | undefined): StackStanding {
  if (stage === "stopped" && before?.state === "failed") return { ...before, down: true };
  return { state: stage, startup_s: startup_s ?? before?.startup_s ?? null, down: stage === "stopped" };
}

const STAGE_WORDS: Readonly<Record<StackState, string>> = {
  docker: "starting Docker",
  pulling: "pulling images",
  installing: "installing dependencies",
  starting: "starting",
  ready: "ready",
  failed: "did not become ready",
  stopped: "down",
};

/** `ready after 2.4 s, not counted`: what the results panel says of the stack. */
export function stackText(stack: StackStanding): string {
  const startup = stack.startup_s === null ? null : `ready after ${stack.startup_s.toFixed(1)} s, not counted`;
  switch (stack.state) {
    case "ready":
      return startup ?? STAGE_WORDS.ready;
    case "stopped":
      return startup ? `${STAGE_WORDS.stopped} · it was ${startup}` : STAGE_WORDS.stopped;
    case "failed":
      return stack.down ? `${STAGE_WORDS.failed} · ${STAGE_WORDS.stopped}` : STAGE_WORDS.failed;
    default:
      return STAGE_WORDS[stack.state];
  }
}

function caseRow(event: CaseResult): CaseRow {
  return {
    id: event.id,
    visible: event.visible,
    oracle: event.oracle === true,
    seed: event.seed ?? null,
    n: event.n ?? null,
    level: event.level,
    status: event.status,
    result: event,
  };
}

/** What the panel shows: `showAll` lists the passing hidden cases and every oracle input. */
export function resultsView(model: RunModel, showAll: boolean): ResultsView {
  const cases = [...model.cases.values()];
  const tests = [...model.tests.values()];
  const running = [...cases, ...tests].filter((row) => row.status === "running").map((row) => row.id);
  const ended = cases.filter((row) => !row.oracle && row.status !== "running");
  const groups = [...model.stress.values()];
  return {
    items: [
      ...(groups.some((group) => group.level !== null) ? levelGroupItems(ended, groups, showAll) : caseItems(ended, showAll)),
      ...oracleItems(cases.filter((row) => row.oracle && row.status !== "running"), showAll),
      ...groups.filter((group) => group.level === null).map((group): ViewItem => ({ kind: "stress", group })),
      ...testItems(tests.filter((row) => row.status !== "running")),
      ...model.levels.map((result): ViewItem => ({ kind: "level", result })),
    ],
    running,
    notice: model.notice,
    progress: { done: finishedCount(model), planned: plannedCount(model.start) },
    summary: summary(model),
  };
}

/** A submission with stress cases, level by level: the level's cases, then its stress cases. */
function levelGroupItems(rows: readonly CaseRow[], groups: readonly StressGroup[], showAll: boolean): ViewItem[] {
  const levels = [...new Set([...rows.map((row) => row.level), ...groups.map((group) => group.level)])].sort((a, b) => (a ?? 0) - (b ?? 0));
  return levels.flatMap((level) => [
    ...caseItems(rows.filter((row) => row.level === level), showAll),
    ...groups.filter((group) => group.level === level).map((group): ViewItem => ({ kind: "stress", group })),
  ]);
}

function caseItems(rows: readonly CaseRow[], showAll: boolean): ViewItem[] {
  const collapsed = showAll ? [] : rows.filter((row) => !row.visible && row.status === "pass");
  const items: ViewItem[] = rows.filter((row) => !collapsed.includes(row)).map((row) => ({ kind: "case", row }));
  if (collapsed.length) items.push({ kind: "count", status: "pass", text: counted(collapsed.length, "hidden case", "hidden cases") });
  return items;
}

/** Failing oracle inputs smallest `n` first, three of them, then a count of the rest and of the passing ones. */
function oracleItems(rows: readonly CaseRow[], showAll: boolean): ViewItem[] {
  if (showAll) return [...rows].sort((a, b) => (a.seed ?? 0) - (b.seed ?? 0)).map((row) => ({ kind: "case", row }));
  const failing = rows.filter((row) => row.status !== "pass").sort((a, b) => (a.n ?? 0) - (b.n ?? 0) || (a.seed ?? 0) - (b.seed ?? 0));
  const passing = rows.length - failing.length;
  const items: ViewItem[] = failing.slice(0, SHOWN_ORACLE_FAILURES).map((row) => ({ kind: "case", row }));
  const more = failing.length - SHOWN_ORACLE_FAILURES;
  if (more > 0) items.push({ kind: "more", text: `${more} more ${more === 1 ? "oracle input" : "oracle inputs"} did not pass` });
  if (passing) items.push({ kind: "count", status: "pass", text: counted(passing, "oracle input", "oracle inputs") });
  return items;
}

/** Tests under a heading per file, in the suite's order; a service project's `commands.test` names no file. */
function testItems(rows: readonly TestRow[]): ViewItem[] {
  const items: ViewItem[] = [];
  let file: string | null = null;
  for (const row of rows) {
    const path = testFile(row.id);
    if (row.id !== SERVICE_TEST_ID && path !== file) {
      items.push({ kind: "file", path });
      file = path;
    }
    items.push({ kind: "test", row });
  }
  return items;
}

/** `tests/test_level_1.py` of `tests/test_level_1.py::test_ex1`. */
export function testFile(id: string): string {
  const at = id.indexOf("::");
  return at < 0 ? id : id.slice(0, at);
}

function finishedCount(model: RunModel): number {
  const rows = [...model.cases.values(), ...model.tests.values()];
  const stressRuns = [...model.stress.values()].flatMap((group) => group.runs).filter((status) => status !== "running");
  return rows.filter((row) => row.status !== "running").length + stressRuns.length;
}

function plannedCount(start: RunStart | null): number | null {
  const planned = start?.planned;
  if (!planned) return null;
  const stress = planned.stress ? planned.stress.cases * planned.stress.variants * planned.stress.runs : 0;
  return planned.cases + planned.oracle_inputs + stress;
}

/** `two-sum · python · 16 cases (2 visible, 13 hidden, 1 generated) · time limit 5x · timer 12:31 / 25:00`. */
export function headerText(start: RunStart): string {
  const parts = [start.slug, start.language];
  const levels = start.levels;
  if (levels) {
    const covered = levels.up_to === 1 ? `level 1 of ${levels.last}` : `levels 1-${levels.up_to} of ${levels.last}`;
    parts.push(start.command === "submit" ? `submit ${covered}` : covered);
  }
  const planned = start.planned;
  if (planned) {
    parts.push(`${counted(planned.cases, "case", "cases")} (${planned.visible} visible, ${planned.hidden} hidden, ${planned.generated} generated)`);
    if (planned.oracle_inputs) parts.push(counted(planned.oracle_inputs, "oracle input", "oracle inputs"));
    const stress = planned.stress;
    if (stress) {
      parts.push(`${stress.cases} stress × ${counted(stress.variants, "variant", "variants")} × ${counted(stress.runs, "run", "runs")}`);
    }
  }
  if (start.time_limit) parts.push(`time limit ${start.time_limit}`);
  if (start.timer) parts.push(`timer ${timerText(start.timer.elapsed_s, start.timer.limit_s)}`);
  return parts.join(" · ");
}

function summary(model: RunModel): Summary | null {
  const end = model.end;
  if (end) return endSummary(model, end);
  const closed = model.closed;
  if (!closed) return null;
  const text = closed.signal ? `cstudy was stopped by ${closed.signal}` : `cstudy exited ${closed.exit_code}`;
  return { tone: "fail", text, notes: closed.stderr };
}

function endSummary(model: RunModel, end: RunEnd): Summary {
  switch (end.outcome) {
    case "interrupted":
      return { tone: "warn", text: "interrupted", notes: [] };
    case "error":
      return { tone: "fail", text: `error: ${end.message ?? "the run stopped"}`, notes: [] };
    case "build_failed":
      return { tone: "fail", text: "BUILD FAILED", notes: [] };
    case "load_failed": {
      const error = end.summary?.load_error;
      return { tone: "fail", text: "LOAD FAILED", notes: error ? [`${error.type}: ${error.message}`] : [] };
    }
    case "passed":
    case "failed": {
      const text = [...tally(model), ...duration(end)];
      if (end.outcome === "passed") text.push("all passed");
      const notes = end.outcome === "passed" && model.stress.size ? [NOT_A_PROOF] : [];
      return { tone: end.outcome === "passed" ? "ok" : "fail", text: text.join(" · "), notes };
    }
  }
}

/** `12/14 passed · 1 failed · 1 tle`: a submission's level tallies, else the shown statuses. */
function tally(model: RunModel): string[] {
  if (model.levels.length) {
    const total = model.levels.reduce((sum, level) => sum + level.total, 0);
    const passed = model.levels.reduce((sum, level) => sum + level.passed, 0);
    return [`${passed}/${total} passed`, ...(total > passed ? [`${total - passed} failed`] : [])];
  }
  const statuses = [
    ...[...model.cases.values()].map((row) => row.status),
    ...[...model.tests.values()].map((row) => row.status).filter((status) => status !== "skip"),
    ...[...model.stress.values()].map((group) => group.result?.status ?? "running"),
  ];
  const count = (status: RowStatus) => statuses.filter((found) => found === status).length;
  return [
    `${count("pass")}/${statuses.length} passed`,
    ...SUMMARY_COUNTS.flatMap(([status, one, many]) => {
      const found = count(status);
      return found ? [`${found} ${found === 1 ? one : many}`] : [];
    }),
  ];
}

function duration(end: RunEnd): string[] {
  const seconds = end.summary?.duration_s;
  return seconds === undefined ? [] : [`total ${seconds.toFixed(1)}s`];
}

function counted(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}
