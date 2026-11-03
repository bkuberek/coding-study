/**
 * The editor's diagnostics (docs/specs/web-ui.md#live-diagnostics): two sources, the last run's
 * and the language server's, that together are the file's one lint set. `@codemirror/lsp-client`'s
 * `serverDiagnostics()` is not used because it replaces the whole set.
 */
import { type Diagnostic, openLintPanel, setDiagnostics } from "@codemirror/lint";
import { type EditorState, type Extension, type Line, StateEffect, StateField, type Text, type TransactionSpec } from "@codemirror/state";
import type { Command, EditorView, KeyBinding } from "@codemirror/view";

import { documentLine } from "./positions.ts";

/**
 * A diagnostic as `cstudy` reports it for one file: the `diagnostic` event of
 * schemas/events.schema.json, with 1-based line and column.
 */
export interface FileDiagnostic {
  readonly severity: "error" | "warning" | "info";
  readonly line: number | null;
  readonly column: number | null;
  readonly message: string;
  readonly code?: string | null;
  readonly source?: string;
}

/** How many diagnostics of each severity a file shows; hints are not counted. */
export interface DiagnosticCounts {
  readonly errors: number;
  readonly warnings: number;
  readonly infos: number;
}

const LAST_RUN = "last run";

/**
 * The lint markers for a document. A diagnostic marks its line from its column to the end, or the
 * whole line without a usable column; one past the end of a document edited since the run marks the
 * last line, and one without a line marks nothing, since it belongs to no position.
 */
export function lintDiagnostics(doc: Text, diagnostics: readonly FileDiagnostic[]): Diagnostic[] {
  return diagnostics.flatMap((diagnostic) => {
    if (diagnostic.line === null) return [];
    const line = documentLine(doc, diagnostic.line);
    const detail = diagnostic.code ?? diagnostic.source;
    return [
      {
        from: markerStart(line, diagnostic.column),
        to: line.to,
        severity: diagnostic.severity,
        message: diagnostic.message,
        source: detail ? `${LAST_RUN} · ${detail}` : LAST_RUN,
      },
    ];
  });
}

function markerStart(line: Line, column: number | null): number {
  if (column === null) return line.from;
  const start = line.from + Math.max(column, 1) - 1;
  return start < line.to ? start : line.from;
}

/**
 * The run's diagnostics and the server's as one set: a run diagnostic that a live one repeats, on
 * the same line with the same message, is left out, since the live one says more.
 */
export function mergeDiagnostics(doc: Text, run: readonly Diagnostic[], live: readonly Diagnostic[]): Diagnostic[] {
  const seen = new Set(live.map((diagnostic) => repeatKey(doc, diagnostic)));
  return [...run.filter((diagnostic) => !seen.has(repeatKey(doc, diagnostic))), ...live];
}

function repeatKey(doc: Text, diagnostic: Diagnostic): string {
  return `${doc.lineAt(Math.min(diagnostic.from, doc.length)).number}\n${diagnostic.message}`;
}

export function countDiagnostics(diagnostics: readonly Diagnostic[]): DiagnosticCounts {
  const count = (severity: Diagnostic["severity"]): number => diagnostics.filter((found) => found.severity === severity).length;
  return { errors: count("error"), warnings: count("warning"), infos: count("info") };
}

const setRun = StateEffect.define<readonly Diagnostic[]>();
const setLive = StateEffect.define<readonly Diagnostic[]>();

interface Sources {
  readonly run: readonly Diagnostic[];
  readonly live: readonly Diagnostic[];
  readonly counts: DiagnosticCounts;
}

const NONE: Sources = { run: [], live: [], counts: { errors: 0, warnings: 0, infos: 0 } };

/** Each source's diagnostics, kept in step with the text, and the counts of the merged set. */
const sources = StateField.define<Sources>({
  create: () => NONE,
  update(value, transaction) {
    let { run, live, counts } = value;
    if (transaction.docChanged) {
      run = mapped(run, transaction.changes);
      live = mapped(live, transaction.changes);
    }
    for (const effect of transaction.effects) {
      if (effect.is(setRun)) run = effect.value;
      else if (effect.is(setLive)) live = effect.value;
      else continue;
      counts = countDiagnostics(mergeDiagnostics(transaction.newDoc, run, live));
    }
    return { run, live, counts };
  },
});

function mapped(diagnostics: readonly Diagnostic[], changes: { mapPos(pos: number, assoc?: number): number }): Diagnostic[] {
  return diagnostics.map((diagnostic) => {
    const from = changes.mapPos(diagnostic.from, 1);
    return { ...diagnostic, from, to: Math.max(from, changes.mapPos(diagnostic.to, -1)) };
  });
}

/** The state field behind the two sources: the editor includes it once. */
export const diagnosticSources: Extension = sources;

/** The change that makes `diagnostics` the last run's, keeping the server's. */
export function runDiagnosticsSpec(state: EditorState, diagnostics: readonly FileDiagnostic[]): TransactionSpec {
  return replacing(state, setRun, lintDiagnostics(state.doc, diagnostics));
}

/** The change that makes `diagnostics` the server's, keeping the last run's. */
export function liveDiagnosticsSpec(state: EditorState, diagnostics: readonly Diagnostic[]): TransactionSpec {
  return replacing(state, setLive, diagnostics);
}

function replacing(state: EditorState, effect: typeof setRun, diagnostics: readonly Diagnostic[]): TransactionSpec {
  const current = state.field(sources);
  const run = effect === setRun ? diagnostics : current.run;
  const live = effect === setLive ? diagnostics : current.live;
  const merged = mergeDiagnostics(state.doc, run, live);
  return { effects: [effect.of(diagnostics), ...(setDiagnostics(state, merged).effects as StateEffect<unknown>[])] };
}

/** What the file shows now, errors, warnings and information after the merge. */
export function diagnosticCounts(state: EditorState): DiagnosticCounts {
  return state.field(sources).counts;
}

/** Whether a transaction replaced either source, so the counts may differ. */
export function replacedDiagnostics(transactions: readonly { effects: readonly StateEffect<unknown>[] }[]): boolean {
  return transactions.some((transaction) => transaction.effects.some((effect) => effect.is(setRun) || effect.is(setLive)));
}

/** Runs the navigation command named, fetching its module the first time a key needs it. */
function lazily(name: "selectNextDiagnostic" | "selectPreviousDiagnostic" | "cursorToNextDiagnostic" | "cursorToPreviousDiagnostic"): Command {
  return (view: EditorView): boolean => {
    void import("./diagnostic-navigation.ts").then((module) => module[name](view));
    return true;
  };
}

/** F8 and Shift-F8 go to the next and previous diagnostic and skip hints; Cmd or Ctrl-Shift-M lists them all. */
export const diagnosticKeymap: readonly KeyBinding[] = [
  { key: "Mod-Shift-m", run: openLintPanel, preventDefault: true },
  { key: "F8", run: lazily("selectNextDiagnostic") },
  { key: "Shift-F8", run: lazily("selectPreviousDiagnostic") },
];

/** Vim's `]d` and `[d`: a selection in normal mode would turn into visual mode, so they only move the cursor. */
export const cursorToNextDiagnostic: Command = lazily("cursorToNextDiagnostic");
export const cursorToPreviousDiagnostic: Command = lazily("cursorToPreviousDiagnostic");
