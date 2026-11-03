import assert from "node:assert/strict";
import { test } from "node:test";

import { Text } from "@codemirror/state";

import type { Diagnostic } from "@codemirror/lint";

import { neighbouringRange } from "../src/diagnostic-navigation.ts";
import { countDiagnostics, type FileDiagnostic, lintDiagnostics, mergeDiagnostics } from "../src/diagnostics.ts";

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

test("a marker is labelled as the last run's, with the diagnostic's code", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({ code: "TS2304", source: "typecheck" })]);
  assert.equal(marker?.source, "last run · TS2304");
});

test("a marker without a code is labelled as the last run's, with the diagnostic's source", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({ code: null, source: "load" })]);
  assert.equal(marker?.source, "last run · load");
});

test("a marker without a code or a source is labelled as the last run's", () => {
  const [marker] = lintDiagnostics(DOC, [diagnostic({})]);
  assert.equal(marker?.source, "last run");
});

function live(fields: Partial<Diagnostic>): Diagnostic {
  return { from: 26, to: 33, severity: "error", message: "name 'balance' is not defined", source: "basedpyright reportUndefinedVariable", ...fields };
}

test("a run diagnostic and a live one on the same line with the same message show once", () => {
  const run = lintDiagnostics(DOC, [diagnostic({})]);
  assert.equal(mergeDiagnostics(DOC, run, [live({})]).length, 1);
});

test("the live diagnostic is the one that shows, with its source", () => {
  const run = lintDiagnostics(DOC, [diagnostic({})]);
  assert.equal(mergeDiagnostics(DOC, run, [live({})])[0]?.source, "basedpyright reportUndefinedVariable");
});

test("the same message on another line shows twice", () => {
  const run = lintDiagnostics(DOC, [diagnostic({ line: 1, column: 1 })]);
  assert.equal(mergeDiagnostics(DOC, run, [live({})]).length, 2);
});

test("another message on the same line shows twice", () => {
  const run = lintDiagnostics(DOC, [diagnostic({})]);
  assert.equal(mergeDiagnostics(DOC, run, [live({ message: "balance is possibly unbound" })]).length, 2);
});

test("a run diagnostic stays when no live diagnostic repeats it", () => {
  const run = lintDiagnostics(DOC, [diagnostic({})]);
  assert.deepEqual(mergeDiagnostics(DOC, run, []), run);
});

test("a live diagnostic stays when the run has none", () => {
  assert.deepEqual(mergeDiagnostics(DOC, [], [live({})]), [live({})]);
});

test("two live diagnostics with one message on one line both show", () => {
  const twice = [live({}), live({ from: 20, to: 25 })];
  assert.equal(mergeDiagnostics(DOC, [], twice).length, 2);
});

test("the counts are the errors, warnings and information, and leave hints out", () => {
  const found = [live({}), live({}), live({ severity: "warning" }), live({ severity: "info" }), live({ severity: "hint" })];
  assert.deepEqual(countDiagnostics(found), { errors: 2, warnings: 1, infos: 1 });
});

test("no diagnostics count as zero of each", () => {
  assert.deepEqual(countDiagnostics([]), { errors: 0, warnings: 0, infos: 0 });
});

const RANGES = [
  { from: 10, to: 14 },
  { from: 30, to: 35 },
  { from: 50, to: 52 },
];

test("the next diagnostic starts after the selection", () => {
  assert.deepEqual(neighbouringRange(RANGES, { from: 10, to: 14 }, true), { from: 30, to: 35 });
});

test("the next diagnostic from a cursor between two is the later one", () => {
  assert.deepEqual(neighbouringRange(RANGES, { from: 20, to: 20 }, true), { from: 30, to: 35 });
});

test("after the last diagnostic the next one is the first", () => {
  assert.deepEqual(neighbouringRange(RANGES, { from: 50, to: 52 }, true), { from: 10, to: 14 });
});

test("the previous diagnostic starts before the selection", () => {
  assert.deepEqual(neighbouringRange(RANGES, { from: 30, to: 35 }, false), { from: 10, to: 14 });
});

test("before the first diagnostic the previous one is the last", () => {
  assert.deepEqual(neighbouringRange(RANGES, { from: 10, to: 14 }, false), { from: 50, to: 52 });
});

test("a single diagnostic that is already selected has no neighbour", () => {
  assert.equal(neighbouringRange([{ from: 10, to: 14 }], { from: 10, to: 14 }, true), null);
});

test("no diagnostics have no neighbour", () => {
  assert.equal(neighbouringRange([], { from: 0, to: 0 }, true), null);
});

test("the ranges may come in any order", () => {
  assert.deepEqual(neighbouringRange([RANGES[2]!, RANGES[0]!, RANGES[1]!], { from: 10, to: 14 }, true), { from: 30, to: 35 });
});
