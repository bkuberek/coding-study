/**
 * Which file of the tree a run's diagnostic marks (docs/specs/web-ui.md#file-api-rules): its
 * `file` is relative to the project folder for a project, which is the tree's root, and to the
 * workspace root otherwise, from which the page strips the attempt's root.
 */

import type { Diagnostic } from "./run-events.ts";

/** The tree path the diagnostic marks, or null for one without a file of the attempt. */
export function diagnosticPath(file: string | null, kind: string, root: string): string | null {
  if (file === null) return null;
  if (kind === "project") return file;
  const prefix = `${root.replace(/\/$/, "")}/`;
  return file.startsWith(prefix) ? file.slice(prefix.length) : null;
}

/** The diagnostics of each file they mark, in the run's order. */
export function diagnosticsByPath(diagnostics: readonly Diagnostic[], kind: string, root: string): Map<string, Diagnostic[]> {
  const byPath = new Map<string, Diagnostic[]>();
  for (const diagnostic of diagnostics) {
    const path = diagnosticPath(diagnostic.file, kind, root);
    if (path === null) continue;
    byPath.set(path, [...(byPath.get(path) ?? []), diagnostic]);
  }
  return byPath;
}
