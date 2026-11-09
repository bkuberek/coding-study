/**
 * The status bar's code-intelligence segment (docs/specs/web-ui.md#status-bar), as text: what the
 * active file's session is doing, or why it has none.
 */

import type { DiagnosticCounts } from "../diagnostics.ts";
import type { SessionState } from "./intelligence-state.ts";
import type { LanguageState } from "./types.ts";

export type FileIntelligence =
  | { readonly kind: "session"; readonly language: string; readonly server: string; readonly state: SessionState }
  | { readonly kind: "not-installed"; readonly language: string; readonly server: string }
  /** Installed, but the selected JDK is not one the server runs on: `detail` says which it needs. */
  | { readonly kind: "needs-jdk"; readonly language: string; readonly detail: string }
  /** Its build's last day has passed, as an early-access build stops: `detail` says since when and what to do. */
  | { readonly kind: "unusable"; readonly language: string; readonly detail: string }
  /** Its vendor's license is not accepted, so it is not downloaded: `detail` names the command that accepts it. */
  | { readonly kind: "license"; readonly language: string; readonly server: string; readonly detail: string }
  | { readonly kind: "no-server"; readonly language: string }
  /** The attempt has none whatever its language's server: `no_code_intelligence` of its status. */
  | { readonly kind: "withheld"; readonly reason: string };

export interface Segment {
  readonly text: string;
  /** The control after the text, if any: Restart for a stopped session, a link to Health. */
  readonly action: "restart" | "health" | null;
  /** The whole reason of a stopped session, for the tooltip. */
  readonly title: string;
  /** `starting`, `ready`, `reconnecting`, `stopped`, `not-installed`, `needs-jdk`, `no-server` or `withheld`. */
  readonly state: string;
}

const NAMES: Readonly<Record<string, string>> = {
  python: "Python",
  typescript: "TypeScript",
  java: "Java",
  kotlin: "Kotlin",
  go: "Go",
  rust: "Rust",
};

/** Why an attempt has no code intelligence, by the reason its status gives. */
const WITHHELD: Readonly<Record<string, string>> = {
  service_project: "code intelligence for service projects comes later",
};
const WITHHELD_UNKNOWN = "no code intelligence for this attempt";

export function languageName(language: string): string {
  return NAMES[language] ?? language;
}

/** `2 errors · 1 warning`: the severities that have some, errors first; nothing when none has. */
export function countsText(counts: DiagnosticCounts): string {
  return [
    plural(counts.errors, "error", "errors"),
    plural(counts.warnings, "warning", "warnings"),
    plural(counts.infos, "info", "infos"),
  ]
    .filter((part) => part !== "")
    .join(" · ");
}

function plural(count: number, one: string, many: string): string {
  if (count === 0) return "";
  return `${count} ${count === 1 ? one : many}`;
}

export function segmentOf(found: FileIntelligence, counts?: DiagnosticCounts): Segment {
  switch (found.kind) {
    case "no-server":
      return { text: `no code intelligence for ${languageName(found.language)} yet`, action: null, title: "", state: "no-server" };
    case "not-installed":
      return {
        text: `no code intelligence for ${languageName(found.language)}: ${found.server} is not installed`,
        action: "health",
        title: "",
        state: "not-installed",
      };
    case "needs-jdk":
      return { text: `no code intelligence for ${languageName(found.language)}: ${found.detail}`, action: "health", title: "", state: "needs-jdk" };
    case "unusable":
      return { text: `no code intelligence for ${languageName(found.language)}: ${found.detail}`, action: "health", title: "", state: "unusable" };
    case "license":
      return {
        text: `no code intelligence for ${languageName(found.language)}: ${found.server}'s license is not accepted`,
        action: "health",
        title: found.detail,
        state: "license",
      };
    case "withheld":
      return { text: WITHHELD[found.reason] ?? WITHHELD_UNKNOWN, action: null, title: "", state: "withheld" };
    case "session":
      return sessionSegment(found, counts);
  }
}

function sessionSegment(found: Extract<FileIntelligence, { kind: "session" }>, counts?: DiagnosticCounts): Segment {
  const head = `${found.language} · ${found.server} · `;
  const { state } = found;
  switch (state.kind) {
    case "starting":
      return { text: `${head}starting`, action: null, title: "", state: "starting" };
    case "ready":
      return { text: `${head}ready${readyCounts(counts)}`, action: null, title: "", state: "ready" };
    case "reconnecting":
      return { text: `${head}reconnecting…`, action: null, title: "", state: "reconnecting" };
    case "stopped":
      return { text: `${head}stopped${state.why ? `: ${state.why}` : ""}`, action: "restart", title: state.reason, state: "stopped" };
  }
}

function readyCounts(counts: DiagnosticCounts | undefined): string {
  const text = counts === undefined ? "" : countsText(counts);
  return text === "" ? "" : ` · ${text}`;
}

export interface LanguageRow {
  readonly name: string;
  readonly detail: string;
  /** Whether the detail links to the Health view, where `cstudy doctor --fix` installs the server. */
  readonly health: boolean;
}

/** One line of the Settings view's list of languages (docs/specs/web-ui.md#settings-view). */
export function languageRow(state: LanguageState): LanguageRow {
  const health = state.state !== "installed" && state.state !== "not_available";
  return { name: languageName(state.language), detail: state.detail, health };
}
