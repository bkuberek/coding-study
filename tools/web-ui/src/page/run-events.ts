/**
 * The events of a run as the server relays them (docs/specs/cli.md#events, schemas/events.schema.json),
 * and the server's own `closed`. Only the fields the results panel reads are typed; a reader ignores
 * the types and fields it does not know, as the stream's version rules allow.
 */

export type CaseStatus = "pass" | "fail" | "error" | "timeout" | "tle" | "invalid" | "stalled" | "not_run" | "skip";

export interface Levels {
  readonly up_to: number;
  readonly unlocked: number;
  readonly last: number;
}

export interface Planned {
  readonly cases: number;
  readonly visible: number;
  readonly hidden: number;
  readonly generated: number;
  readonly oracle_inputs: number;
  readonly stress: { readonly cases: number; readonly variants: number; readonly runs: number } | null;
}

export interface RunStart {
  readonly type: "run_start";
  readonly command: "test" | "submit";
  readonly slug: string;
  readonly language: string;
  readonly attempt_id: number;
  readonly mode: string;
  readonly levels: Levels | null;
  readonly kind?: string;
  readonly timer?: { readonly elapsed_s: number; readonly limit_s: number } | null;
  readonly time_limit?: string | null;
  readonly planned?: Planned | null;
}

/** Where a service project's stack stands (docs/specs/cli.md#events). */
export type StackState = "docker" | "pulling" | "installing" | "starting" | "ready" | "failed" | "stopped";

export interface Output {
  readonly type: "output";
  readonly text: string;
  /** A service project: the stage its stack reached with this notice. */
  readonly stack?: StackState;
  /** With `ready`: the startup, which no limit or result counts. */
  readonly startup_s?: number;
}

export interface Build {
  readonly type: "build";
  readonly seconds: number;
  readonly note: string | null;
}

export interface ErrorDetail {
  readonly type: string;
  readonly message: string;
  readonly trace?: string;
}

/** A case's result, as `cases` of `cstudy test --json` holds it. */
export interface CaseResult {
  readonly type: "case_result" | "case_revised";
  readonly id: string;
  readonly visible: boolean;
  readonly generated: boolean;
  readonly status: CaseStatus;
  readonly duration_ns: number;
  readonly level: number | null;
  readonly oracle?: true;
  readonly seed?: number;
  readonly n?: number;
  readonly input?: unknown;
  readonly expected?: unknown;
  readonly actual?: unknown;
  readonly reason?: string | null;
  readonly error?: ErrorDetail | null;
  /** The operation that raised, or on the virtual clock deadlocked, which `reason` then names. */
  readonly op_index?: number | null;
  readonly partial_output?: readonly unknown[];
  readonly stdout?: string | null;
  readonly note?: string | null;
  readonly time_limit_ms?: number;
  readonly time_limit_basis?: string | null;
  readonly hang_guard_ms?: number;
  readonly exit_code?: number;
  readonly stderr?: string | null;
}

export interface CaseStart {
  readonly type: "case_start";
  readonly id: string;
  readonly visible: boolean;
  readonly level: number | null;
  readonly oracle?: true;
  readonly seed?: number;
  readonly n?: number;
}

export interface TestStart {
  readonly type: "test_start";
  readonly id: string;
}

/** A project test's result, as `cases` of `cstudy test --json` on a project holds it. */
export interface TestResult {
  readonly type: "test_result";
  readonly id: string;
  readonly status: CaseStatus;
  readonly duration_ns: number;
  readonly origin: "level" | "starter" | "yours";
  readonly level: number | null;
  readonly message?: string;
  readonly expected?: unknown;
  readonly actual?: unknown;
  readonly error?: ErrorDetail;
  readonly stdout?: string;
}

export interface StressRunStart {
  readonly type: "stress_run_start";
  readonly id: string;
  readonly variant: string;
  readonly run: number;
  readonly seed: number;
  /** `cstudy submit` on a project: the stress case's level. */
  readonly level?: number;
}

export interface StressRun {
  readonly type: "stress_run";
  readonly id: string;
  readonly variant: string;
  readonly run: number;
  readonly seed: number;
  readonly status: CaseStatus;
  readonly duration_ns: number;
  readonly reasons: readonly string[];
  readonly level?: number;
}

export interface StressResult {
  readonly type: "stress_result";
  readonly id: string;
  readonly variant: string;
  readonly status: CaseStatus;
  readonly runs: number;
  readonly runs_passed: number;
  readonly median_ms: number | null;
  readonly failures: readonly { readonly run: number; readonly seed: number; readonly status: string; readonly reasons: readonly string[] }[];
  readonly level?: number;
}

/** Where code does not load, build or type-check (docs/specs/cli.md#diagnostics). */
export interface Diagnostic {
  readonly type: "diagnostic";
  readonly source: "load" | "typecheck" | "build";
  readonly severity: "error" | "warning" | "info";
  readonly file: string | null;
  readonly line: number | null;
  readonly column: number | null;
  readonly code: string | null;
  readonly message: string;
}

export interface LevelResult {
  readonly type: "level_result";
  readonly status: "pass" | "fail";
  readonly level: number;
  readonly total: number;
  readonly passed: number;
  readonly visible_total: number;
  readonly visible_passed: number;
  readonly hidden_total: number;
  readonly hidden_passed: number;
}

export interface LevelUnlocked {
  readonly type: "level_unlocked";
  readonly level: number;
  readonly title: string;
  readonly methods: readonly string[];
  readonly tests: { readonly path: string; readonly count: number } | null;
  readonly statement: string;
}

export interface PerfResult {
  readonly type: "perf_result";
  readonly verdict: string | null;
  readonly confidence: string | null;
  readonly text: string;
  readonly warnings: readonly string[];
  readonly wrong_answer: string | null;
}

export interface RunSummary {
  readonly duration_s?: number;
  readonly load_error?: ErrorDetail | null;
}

export interface RunEnd {
  readonly type: "run_end";
  readonly outcome: "passed" | "failed" | "build_failed" | "load_failed" | "error" | "interrupted";
  readonly exit_code: number;
  readonly message: string | null;
  readonly summary: RunSummary | null;
}

export type RunEvent =
  | RunStart
  | Output
  | Build
  | CaseStart
  | CaseResult
  | TestStart
  | TestResult
  | StressRunStart
  | StressRun
  | StressResult
  | Diagnostic
  | LevelResult
  | LevelUnlocked
  | PerfResult
  | RunEnd;

/** The server's last message on a stream, once the child exited (docs/specs/web-ui.md#server-sent-events). */
export interface Closed {
  readonly exit_code: number;
  readonly signal: string | null;
  readonly stderr: readonly string[];
}

/** Every message name of a run's stream, which `EventSource` needs one by one. */
export const RUN_EVENT_TYPES: readonly RunEvent["type"][] = [
  "run_start",
  "output",
  "build",
  "case_start",
  "case_result",
  "case_revised",
  "test_start",
  "test_result",
  "stress_run_start",
  "stress_run",
  "stress_result",
  "diagnostic",
  "level_result",
  "level_unlocked",
  "perf_result",
  "run_end",
];
