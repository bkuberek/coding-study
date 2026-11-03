/**
 * A language server's published diagnostics as lint markers
 * (docs/specs/web-ui.md#live-diagnostics): severities, the classes that fade unused code and
 * strike deprecated code through, and the source label the tooltip names.
 */

import type { Diagnostic } from "@codemirror/lint";
import type { Text } from "@codemirror/state";

import { documentLine } from "../positions.ts";

export interface Position {
  readonly line: number;
  readonly character: number;
}

/** The part of an LSP `Diagnostic` the page reads; every string is shown as text. */
export interface PublishedDiagnostic {
  readonly range: { readonly start: Position; readonly end: Position };
  readonly message: string;
  /** 1 error, 2 warning, 3 information, 4 hint; an error when absent. */
  readonly severity?: 1 | 2 | 3 | 4 | undefined;
  readonly code?: string | number | { readonly value: string | number } | undefined;
  readonly source?: string | undefined;
  /** 1 Unnecessary, 2 Deprecated. */
  readonly tags?: readonly number[] | undefined;
}

export const UNNECESSARY_CLASS = "cstudy-unnecessary";
export const DEPRECATED_CLASS = "cstudy-deprecated";

const SEVERITIES = ["error", "warning", "info", "hint"] as const;
const TAG_CLASSES: Readonly<Record<number, string>> = { 1: UNNECESSARY_CLASS, 2: DEPRECATED_CLASS };

/** `basedpyright reportUndefinedVariable`, `ts 2304`, or whichever of the two the server sent. */
export function diagnosticLabel(found: Pick<PublishedDiagnostic, "source" | "code">): string {
  const code = typeof found.code === "object" ? found.code.value : found.code;
  return [found.source, code]
    .filter((part) => part !== undefined && part !== "")
    .join(" ");
}

/** The markers of a publication; `offsetOf` turns an LSP position into an offset of the document. */
export function liveDiagnostics(published: readonly PublishedDiagnostic[], offsetOf: (position: Position) => number): Diagnostic[] {
  return published.map((found) => {
    const start = offsetOf(found.range.start);
    const end = offsetOf(found.range.end);
    const label = diagnosticLabel(found);
    const markClass = (found.tags ?? []).flatMap((tag) => TAG_CLASSES[tag] ?? []).join(" ");
    return {
      from: Math.min(start, end),
      to: Math.max(start, end),
      severity: SEVERITIES[(found.severity ?? 1) - 1] ?? "error",
      message: found.message,
      ...(label === "" ? {} : { source: label }),
      ...(markClass === "" ? {} : { markClass }),
    };
  });
}

/**
 * The offset of an LSP position (0-based line, UTF-16 character), kept inside the document: a
 * server may answer for a version of the text the page has since changed.
 */
export function lspOffset(doc: Text, position: { readonly line: number; readonly character: number }): number {
  const line = documentLine(doc, position.line + 1);
  return line.from + Math.min(Math.max(position.character, 0), line.length);
}
