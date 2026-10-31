import assert from "node:assert/strict";
import { test } from "node:test";

import { Text } from "@codemirror/state";

import { type FileDiagnostic, lintDiagnostics } from "../src/diagnostics.ts";

// Line 1 spans 0-14, line 2 spans 15-33, line 3 is empty at 34.
const DOC = Text.of(["def deposit():", "    return balance", ""]);

function diagnostic(fields: Partial<FileDiagnostic>): FileDiagnostic {
  return { severity: "error", line: 2, column: 12, message: "name 'balance' is not defined", ...fields };
}

function range(fields: Partial<FileDiagnostic>): [number, number] | undefined {
  const marker = lintDiagnostics(DOC, [diagnostic(fields)])[0];
  return marker && [marker.from, marker.to];
}

test("a diagnostic marks its line from its column to the end", () => {
  assert.deepEqual(range({}), [26, 33]);
});

test("a diagnostic without a column marks its whole line", () => {
  assert.deepEqual(range({ column: null }), [15, 33]);
});

test("a column past the end of the line marks the whole line", () => {
  assert.deepEqual(range({ column: 40 }), [15, 33]);
});

test("a line past the end of the document marks the last line", () => {
  assert.deepEqual(range({ line: 9, column: null }), [34, 34]);
});

test("a diagnostic on an empty line marks the line's start", () => {
  assert.deepEqual(range({ line: 3, column: 1 }), [34, 34]);
});

test("a diagnostic without a line marks nothing", () => {
  assert.deepEqual(lintDiagnostics(DOC, [diagnostic({ line: null })]), []);
});

test("every diagnostic with a line gets a marker", () => {
  const markers = lintDiagnostics(DOC, [diagnostic({ line: 1 }), diagnostic({ line: 2 })]);
  assert.equal(markers.length, 2);
});

test("a marker keeps the severity", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({ severity: "warning" })]);
  assert.equal(marker?.severity, "warning");
});

test("a marker keeps the message", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({})]);
  assert.equal(marker?.message, "name 'balance' is not defined");
});

test("a marker is labelled with the diagnostic's code", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({ code: "TS2304", source: "typecheck" })]);
  assert.equal(marker?.source, "TS2304");
});

test("a marker without a code is labelled with the diagnostic's source", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({ code: null, source: "load" })]);
  assert.equal(marker?.source, "load");
});

test("a marker without a code or a source has no label", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({})]);
  assert.equal(marker !== undefined && "source" in marker, false);
});
