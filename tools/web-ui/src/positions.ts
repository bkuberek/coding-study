import type { Line, Text } from "@codemirror/state";

/**
 * The line with a 1-based number, or the first or last line for a number outside the document:
 * `cstudy` reports positions in the file as it was when the run read it, and it may since be shorter.
 */
export function documentLine(doc: Text, number: number): Line {
  return doc.line(Math.min(Math.max(number, 1), doc.lines));
}

/** The position of a 1-based line and column, kept inside the document and inside the line. */
export function cursorPosition(doc: Text, line: number, column: number | null): number {
  const target = documentLine(doc, line);
  return Math.min(target.from + Math.max((column ?? 1) - 1, 0), target.to);
}
