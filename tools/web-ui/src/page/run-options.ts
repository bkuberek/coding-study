/**
 * The options of a run (docs/specs/web-ui.md#run-options): which ones an attempt's kind takes, the
 * request that starts the run, and the `cstudy` command it is, which the page shows beside its
 * buttons so each one names the command it runs.
 */

export type RunCommandName = "test" | "submit";
export type OptionName = "level" | "cases" | "typecheck" | "stress" | "seed" | "time_limit" | "perf";

export interface RunOptionsState {
  readonly level: number | null;
  readonly cases: readonly string[];
  /** Null: the `typecheck` preference. */
  readonly typecheck: boolean | null;
  readonly stress: number | null;
  readonly seed: number | null;
  /** Null: the configuration's; true or false: on or off; a value such as `5x` or `1500ms`. */
  readonly time_limit: boolean | string | null;
  readonly perf: boolean;
}

export const DEFAULT_OPTIONS: RunOptionsState = {
  level: null,
  cases: [],
  typecheck: null,
  stress: null,
  seed: null,
  time_limit: null,
  perf: false,
};

/** What the options depend on: the attempt and its problem. */
export interface RunContext {
  readonly slug: string;
  readonly kind: string;
  readonly language: string | null;
  readonly levels: { readonly unlocked: number; readonly last: number } | null;
  /** Whether `--stress N` adds oracle inputs to a function or design problem. */
  readonly oracle: boolean;
  /** The `typecheck` preference. */
  readonly typecheck?: boolean;
  /** A service project, whose `cstudy test` takes no flag and whose `cstudy submit` takes a level. */
  readonly service?: boolean;
}

const SINGLE_FILE_WITH_PERF = new Set(["function", "design"]);

/** The options `cstudy test` takes for the attempt's kind and language. */
export function applicableOptions(context: RunContext): ReadonlySet<OptionName> {
  if (context.service) return new Set(["level"]);
  const names: OptionName[] = ["cases"];
  if (context.kind === "progressive" || context.kind === "project") names.push("level");
  if (context.language === "typescript") names.push("typecheck");
  if (context.kind === "concurrent" || (SINGLE_FILE_WITH_PERF.has(context.kind) && context.oracle)) names.push("stress", "seed");
  if (context.kind !== "project") names.push("time_limit");
  if (SINGLE_FILE_WITH_PERF.has(context.kind)) names.push("perf");
  return new Set(names);
}

/** The body of `POST /api/v1/runs`: the options that are set and that the command takes. */
export function runBody(attemptId: number, command: RunCommandName, options: RunOptionsState, context: RunContext): Record<string, unknown> {
  return { attempt_id: attemptId, command, ...sentOptions(command, options, context) };
}

/** `cstudy test two-sum --lang python --stress 30`: the command the run is. */
export function runCommand(command: RunCommandName, options: RunOptionsState, context: RunContext): string {
  const sent = sentOptions(command, options, context);
  const typecheck = (sent.typecheck ?? context.typecheck ?? false) && context.language === "typescript" && !context.service;
  const words = [
    "cstudy",
    command,
    context.slug,
    ...(context.kind === "project" || context.language === null ? [] : ["--lang", context.language]),
    ...(sent.level === undefined ? [] : ["--level", String(sent.level)]),
    ...(sent.cases ?? []).flatMap((id) => ["--case", id]),
    ...(typecheck ? ["--typecheck"] : []),
    ...(sent.stress === undefined ? [] : ["--stress", String(sent.stress)]),
    ...(sent.seed === undefined ? [] : ["--seed", String(sent.seed)]),
    ...timeLimitWords(sent.time_limit),
    ...(sent.perf ? ["--perf"] : []),
  ];
  return words.join(" ");
}

/** Case ids typed in one field, separated by commas or spaces. */
export function parseCases(text: string): string[] {
  return text.split(/[\s,]+/).filter((id) => id !== "");
}

function sentOptions(command: RunCommandName, options: RunOptionsState, context: RunContext): Partial<RunOptionsState> {
  const applicable = applicableOptions(context);
  const sent: { -readonly [Name in keyof RunOptionsState]?: RunOptionsState[Name] } = {};
  if (context.service && command === "test") return sent;
  if (applicable.has("level") && options.level !== null) sent.level = options.level;
  if (command === "submit") return sent;
  if (options.cases.length) sent.cases = options.cases;
  if (applicable.has("typecheck") && options.typecheck !== null) sent.typecheck = options.typecheck;
  if (applicable.has("stress") && options.stress !== null) sent.stress = options.stress;
  if (applicable.has("seed") && options.seed !== null && (options.stress !== null || context.kind === "concurrent")) sent.seed = options.seed;
  if (applicable.has("time_limit") && options.time_limit !== null) sent.time_limit = options.time_limit;
  if (applicable.has("perf") && options.perf && !options.cases.length) sent.perf = true;
  return sent;
}

function timeLimitWords(value: boolean | string | null | undefined): string[] {
  if (value === undefined || value === null) return [];
  if (value === true) return ["--time-limit"];
  if (value === false) return ["--no-time-limit"];
  return [`--time-limit=${value}`];
}
