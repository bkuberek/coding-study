/**
 * The API documents the page reads (docs/specs/web-ui.md#endpoints). Those a command also prints
 * are that command's `--json` documents (docs/specs/cli.md); only the fields the page uses are typed.
 */

import type { JdkRange, SelectedJdk } from "./jdk.ts";

export type Theme = "system" | "light" | "dark";

export interface Session {
  readonly api: number;
  readonly cstudy: string;
  readonly workspace: string;
  readonly default_lang: string;
  readonly languages: readonly string[];
  readonly tracks: readonly string[];
  readonly kinds: readonly string[];
  readonly domains: readonly string[];
  readonly job_roles: readonly string[];
  readonly scopes: readonly string[];
  readonly patterns: readonly string[];
  /** The JDK `cstudy` selects in the server's environment, or null when none is found. */
  readonly selected_jdk: SelectedJdk | null;
}

export interface Preferences {
  readonly format: 1;
  readonly vim: boolean;
  readonly run_on_save: boolean;
  readonly typecheck: boolean;
  readonly theme: Theme;
  readonly code_intelligence: boolean;
  /** Stored as set; it applies only while `code_intelligence` is on (`autocompleteApplies`). */
  readonly autocomplete: boolean;
  /** What the Problems view's table shows (`shownColumns`). */
  readonly problem_columns: readonly string[];
}

/** One language of `GET /api/v1/code-intelligence/languages`. */
export interface LanguageState {
  readonly language: string;
  /** Null for a language with no server yet. */
  readonly server: string | null;
  readonly version: string | null;
  readonly state: "installed" | "not_installed" | "not_available";
  /** `basedpyright 1.40.2`, `not installed: run cstudy doctor --fix` or `not available yet`. */
  readonly detail: string;
  readonly idle_s: number | null;
}

export interface LanguageStates {
  readonly languages: readonly LanguageState[];
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
  /** What the entry is about, and who it is for; both empty on a problem of your own that leaves them out. */
  readonly domains: readonly string[];
  readonly job_roles: readonly string[];
  /** How big the thing you work on is; null likewise. */
  readonly scope: string | null;
  readonly languages: readonly string[];
  readonly content: string;
  readonly source: string;
  readonly status: string;
  readonly due_on: string | null;
  readonly in_progress: readonly AttemptRef[];
  /** The releases its Java and Kotlin run on; null without either. */
  readonly jdk: JdkRange | null;
}

export interface ProblemList {
  readonly today: string;
  readonly entries: readonly ListEntry[];
  readonly selected_jdk: SelectedJdk | null;
  /** Under the Set filter: the set, and the slugs the catalog no longer has. */
  readonly set?: { readonly name: string; readonly missing: readonly string[] };
}

/** How far a set has come, in `cstudy set list --json` and `cstudy set show --json`. */
export interface SetStanding {
  readonly passed: number;
  /** The entries the catalog has. */
  readonly total: number;
  readonly missing: readonly string[];
}

export interface SetSummary extends SetStanding {
  readonly name: string;
  readonly description: string | null;
  readonly slugs: readonly string[];
}

export interface SetList {
  readonly sets: readonly SetSummary[];
}

export interface SetRow {
  readonly position: number;
  readonly slug: string;
  readonly passed: boolean;
  readonly missing: boolean;
  /** The entry of `cstudy list --json`; null for a slug the catalog no longer has. */
  readonly entry: ListEntry | null;
}

export interface SetDocument extends SetStanding {
  readonly name: string;
  readonly description: string | null;
  readonly today: string;
  readonly rows: readonly SetRow[];
}

/** `cstudy next --json`; a resume also names its attempt and the other attempts in progress. */
export type NextPick =
  | { readonly pick: null; readonly message: string }
  | {
      readonly pick: "resume" | "review" | "new";
      readonly slug: string;
      readonly title: string;
      readonly kind: string;
      readonly difficulty: string;
      readonly group: string;
      readonly reason: string;
      readonly language: string | null;
      readonly start: string;
      readonly attempt_id?: number;
      readonly also_open?: readonly { readonly attempt_id: number; readonly slug: string; readonly language: string | null }[];
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

/** Where the files of an attempt that is over come from (docs/specs/web-ui.md#past-attempt-files). */
export type FilesSource = "archive" | "current" | "missing";

/** `GET /api/v1/attempts/{id}/past-files`. */
export interface PastFilesDocument {
  readonly source: FilesSource;
  /** Relative to the workspace root; null when the files are missing. */
  readonly root: string | null;
  readonly entries: readonly { readonly path: string; readonly size: number }[];
}

/** `GET /api/v1/attempts/{id}/past-files/{path}`. */
export interface PastFileDocument {
  readonly path: string;
  readonly source: "archive" | "current";
  readonly size: number;
  /** Null when the file is not UTF-8 text or exceeds 1 MiB. */
  readonly text: string | null;
}

/** `POST /api/v1/attempts/{id}/hints`. */
export type HintResult =
  | { readonly hint: { readonly number: number; readonly total: number } & Rendered }
  | { readonly locked_until_level: number }
  | { readonly exhausted: true };

/** `POST /api/v1/attempts/{id}/done`: the values of the lines `cstudy done` prints. */
export interface DoneDocument {
  readonly slug: string;
  readonly language: string | null;
  readonly status: string;
  readonly levels_finished: number | null;
  readonly solve_s: number;
  readonly rating: string | null;
  readonly grade: string | null;
  readonly caps: readonly string[];
  readonly hints_used: number;
  readonly next_review: { readonly due_on: string; readonly in_days: number; readonly ease: number };
}

/** `POST /api/v1/problems/{slug}/solution`. */
export interface SolutionDocument extends Rendered {
  readonly slug: string;
  readonly kind: string;
  readonly language: string | null;
  readonly approaches: readonly string[];
  readonly marked_attempt_id: number | null;
}

export interface MockAttempt {
  readonly attempt_id: number;
  readonly slug: string;
  readonly title: string;
  readonly difficulty: string;
  readonly kind: string;
  readonly language: string | null;
}

/** `GET /api/v1/mock`. */
export type MockState =
  | { readonly running: false }
  | {
      readonly running: true;
      readonly ends_at: string;
      readonly remaining_s: number;
      readonly attempts: readonly MockAttempt[];
      readonly locked: readonly string[];
    };

/** `POST /api/v1/mock`. */
export interface StartedMock {
  readonly minutes: number;
  readonly count: number;
  readonly language: string;
  readonly ends_at: string | null;
  readonly problems: readonly (MockAttempt & {
    readonly group: string;
    readonly reason: string;
    readonly file: string;
    readonly statement: string;
  })[];
  readonly message: string | null;
}

export interface StatsGroup {
  readonly group: string;
  readonly problems: number;
  readonly attempted: number;
  readonly passed: number;
  readonly mastered: number;
  readonly recent_attempts: number;
  readonly recent_passed: number;
  readonly pass_rate: number | null;
  readonly median_solve_s: number | null;
  readonly weakness: number;
}

/** `cstudy stats --json`. */
export interface StatsDocument {
  readonly today: string;
  readonly by: string;
  readonly since: string | null;
  readonly groups: readonly StatsGroup[];
  readonly attempts: { readonly finished: number; readonly last_7_days: number; readonly streak_days: number };
  readonly reviews: { readonly due_today: number; readonly overdue: number };
  readonly bench: Readonly<Record<string, number>>;
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

export interface AboutLink {
  readonly label: string;
  readonly url: string;
}

export interface AboutCredit {
  readonly name: string;
  readonly version: string;
  readonly license: string;
}

/** `GET /api/v1/about`: what `cstudy about` prints, and its credits. */
export interface About {
  readonly version: string;
  readonly license: string;
  readonly website: AboutLink;
  readonly links: readonly AboutLink[];
  readonly sponsor: readonly AboutLink[];
  readonly credits: readonly { readonly title: string; readonly credits: readonly AboutCredit[] }[];
}

/** `GET /api/v1/about/licenses`. */
export interface AboutLicenses {
  readonly text: string;
}
