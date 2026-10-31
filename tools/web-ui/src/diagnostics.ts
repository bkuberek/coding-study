import type { Diagnostic } from "@codemirror/lint";
import type { Line, Text } from "@codemirror/state";

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

/**
 * The lint markers for a document. A diagnostic marks its line from its column to the end, or the
 * whole line without a usable column; one past the end of a document edited since the run marks the
 * last line, and one without a line marks nothing, since it belongs to no position.
 */
export function lintDiagnostics(doc: Text, diagnostics: readonly FileDiagnostic[]): Diagnostic[] {
  return diagnostics.flatMap((diagnostic) => {
    if (diagnostic.line === null) return [];
    const line = documentLine(doc, diagnostic.line);
    const marker: Diagnostic = {
      from: markerStart(line, diagnostic.column),
      to: line.to,
      severity: diagnostic.severity,
      message: diagnostic.message,
    };
    const label = diagnostic.code ?? diagnostic.source;
    return [label ? { ...marker, source: label } : marker];
  });
}

function markerStart(line: Line, column: number | null): number {
  if (column === null) return line.from;
  const start = line.from + Math.max(column, 1) - 1;
  return start < line.to ? start : line.from;
}
