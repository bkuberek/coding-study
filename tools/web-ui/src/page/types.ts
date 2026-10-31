/**
 * The API documents the page reads (docs/specs/web-ui.md#endpoints). Those a command also prints
 * are that command's `--json` documents (docs/specs/cli.md); only the fields the page uses are typed.
 */

export type Theme = "system" | "light" | "dark";

export interface Session {
  readonly api: number;
  readonly cstudy: string;
  readonly workspace: string;
  readonly default_lang: string;
  readonly languages: readonly string[];
  readonly tracks: readonly string[];
  readonly kinds: readonly string[];
}

export interface Preferences {
  readonly format: 1;
  readonly vim: boolean;
  readonly run_on_save: boolean;
  readonly typecheck: boolean;
  readonly theme: Theme;
}

export interface AttemptRef {
  readonly attempt_id: number;
  readonly language: string | null;
  readonly mode: string;
}

/** An entry of `cstudy list --json`. */
export interface ListEntry {
  readonly id: string | null;
  readonly slug: string;
  readonly title: string;
  readonly track: string;
  readonly kind: string;
  readonly difficulty: string;
  readonly patterns: readonly string[];
  readonly languages: readonly string[];
  readonly content: string;
  readonly source: string;
  readonly status: string;
  readonly due_on: string | null;
  readonly in_progress: readonly AttemptRef[];
}

export interface ProblemList {
  readonly today: string;
  readonly entries: readonly ListEntry[];
}

/** `cstudy next --json`. */
export type NextPick =
  | { readonly pick: null; readonly message: string }
  | {
      readonly pick: "review" | "new";
      readonly slug: string;
      readonly title: string;
      readonly kind: string;
      readonly difficulty: string;
      readonly group: string;
      readonly reason: string;
      readonly language: string | null;
      readonly start: string;
    };

export interface Approach {
  readonly id: string;
  readonly name: string;
  readonly role: string;
}

export interface ProblemDocument extends ListEntry {
  readonly approaches: readonly Approach[];
  readonly broken: readonly string[];
  readonly levels: { readonly last: number } | null;
  readonly hints_total: number;
  readonly bench: boolean;
  readonly oracle: boolean;
}

export interface Rendered {
  readonly markdown: string;
  readonly html: string;
}

export interface TestRun {
  readonly ran_at: string;
  readonly total: number;
  readonly passed: number;
  readonly duration_ms: number;
}

export interface Submission {
  readonly submitted_at: string;
  readonly total: number;
  readonly passed: number;
}

export interface BenchRun {
  readonly ran_at: string;
  readonly verdict: string;
}

export interface PastAttempt {
  readonly attempt_id: number;
  readonly language: string | null;
  readonly mode: string;
  readonly status: string;
  readonly started_at: string;
  readonly solve_s: number | null;
  readonly rating: string | null;
  readonly grade: string | null;
  readonly hints_used: number;
  readonly solution_revealed: boolean;
  readonly test_runs: readonly TestRun[];
  readonly submissions: readonly Submission[];
  readonly bench_runs: readonly BenchRun[];
}

/** `cstudy history --json`. */
export interface History {
  readonly status: string;
  readonly schedule: {
    readonly due_on: string;
    readonly interval_days: number;
    readonly ease: number;
    readonly reps: number;
    readonly lapses: number;
  } | null;
  readonly attempts: readonly PastAttempt[];
}

/** `cstudy status --json`. */
export interface AttemptStatus {
  readonly slug: string;
  readonly kind: string;
  readonly track: string;
  readonly language: string | null;
  readonly attempt_id: number;
  readonly mode: string;
  readonly started_at: string;
  readonly file: string | null;
  readonly hints: { readonly used: number; readonly total: number; readonly locked_until_level: number | null };
  readonly solution_revealed: boolean;
  readonly levels: {
    readonly unlocked: number;
    readonly last: number;
    readonly titles: readonly string[];
  } | null;
  readonly timer: { readonly elapsed_s: number; readonly limit_s: number } | null;
  readonly last_test_run: { readonly total: number; readonly passed: number; readonly ran_at: string } | null;
  readonly next: string;
}

export interface TreeEntry {
  readonly path: string;
  readonly origin: string;
  readonly level: number | null;
  readonly state: string | null;
  readonly size: number | null;
  readonly editable: boolean;
}

export interface Tree {
  readonly root: string;
  readonly entries: readonly TreeEntry[];
}

export interface FileDocument {
  readonly path: string;
  readonly text: string | null;
  readonly sha256: string;
  readonly origin: string;
  readonly level: number | null;
  readonly state: string | null;
  readonly editable: boolean;
}

export interface Check {
  readonly name: string;
  readonly status: "ok" | "warn" | "fail";
  readonly detail: string;
  readonly fix: string | null;
}

/** `cstudy doctor --json`. */
export interface Doctor {
  readonly workspace: string | null;
  readonly passed: boolean;
  readonly checks: readonly Check[];
}
