/**
 * The status bar's code-intelligence segment (docs/specs/web-ui.md#status-bar), as text: what the
 * active file's session is doing, or why it has none.
 */

import type { SessionState } from "./intelligence-state.ts";
import type { LanguageState } from "./types.ts";

export type FileIntelligence =
  | { readonly kind: "session"; readonly language: string; readonly server: string; readonly state: SessionState }
  | { readonly kind: "not-installed"; readonly language: string; readonly server: string }
  | { readonly kind: "no-server"; readonly language: string };

export interface Segment {
  readonly text: string;
  /** The control after the text, if any: Restart for a stopped session, a link to Health. */
  readonly action: "restart" | "health" | null;
  /** The whole reason of a stopped session, for the tooltip. */
  readonly title: string;
  /** `starting`, `ready`, `reconnecting`, `stopped`, `not-installed` or `no-server`. */
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

export function languageName(language: string): string {
  return NAMES[language] ?? language;
}

export function segmentOf(found: FileIntelligence): Segment {
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
    case "session":
      return sessionSegment(found);
  }
}

function sessionSegment(found: Extract<FileIntelligence, { kind: "session" }>): Segment {
  const head = `${found.language} · ${found.server} · `;
  const { state } = found;
  switch (state.kind) {
    case "starting":
      return { text: `${head}starting`, action: null, title: "", state: "starting" };
    case "ready":
      return { text: `${head}ready`, action: null, title: "", state: "ready" };
    case "reconnecting":
      return { text: `${head}reconnecting…`, action: null, title: "", state: "reconnecting" };
    case "stopped":
      return { text: `${head}stopped${state.why ? `: ${state.why}` : ""}`, action: "restart", title: state.reason, state: "stopped" };
  }
}

export interface LanguageRow {
  readonly name: string;
  readonly detail: string;
  /** Whether the detail links to the Health view, where `cstudy doctor --fix` installs the server. */
  readonly health: boolean;
}

/** One line of the Settings view's list of languages (docs/specs/web-ui.md#settings-view). */
export function languageRow(state: LanguageState): LanguageRow {
  return { name: languageName(state.language), detail: state.detail, health: state.state === "not_installed" };
}
