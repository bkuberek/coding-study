import assert from "node:assert/strict";
import { test } from "node:test";

import { Text } from "@codemirror/state";

import { diagnosticLabel, liveDiagnostics, lspOffset, type PublishedDiagnostic } from "../src/code-intelligence/live-diagnostics.ts";

// Line 1 spans 0-14, line 2 spans 15-33, line 3 is empty at 34.
const DOC = Text.of(["def deposit():", "    return balance", ""]);

// A position is its line times 100 plus its character, so every offset is easy to read.
const offsetOf = (position: { line: number; character: number }): number => position.line * 100 + position.character;

function published(fields: Partial<PublishedDiagnostic>): PublishedDiagnostic {
  return {
    range: { start: { line: 1, character: 4 }, end: { line: 1, character: 11 } },
    message: '"balance" is not defined',
    severity: 1,
    source: "basedpyright",
    code: "reportUndefinedVariable",
    ...fields,
  };
}

function only(fields: Partial<PublishedDiagnostic>) {
  const [found] = liveDiagnostics([published(fields)], offsetOf);
  assert.ok(found !== undefined);
  return found;
}

test("a diagnostic marks its range", () => {
  const found = only({});
  assert.deepEqual([found.from, found.to], [104, 111]);
});

test("the severities are error, warning, information and hint", () => {
  assert.deepEqual([1, 2, 3, 4].map((severity) => only({ severity: severity as 1 }).severity), ["error", "warning", "info", "hint"]);
});

test("a diagnostic without a severity is an error", () => {
  assert.equal(only({ severity: undefined }).severity, "error");
});

test("the message stays text", () => {
  assert.equal(only({ message: "<b>x</b>" }).message, "<b>x</b>");
});

test("the source and the code label the diagnostic", () => {
  assert.equal(only({}).source, "basedpyright reportUndefinedVariable");
});

test("a numeric code is part of the label", () => {
  assert.equal(only({ source: "ts", code: 2304 }).source, "ts 2304");
});

test("a code with a link is labelled by its value", () => {
  assert.equal(only({ source: "rustc", code: { value: "E0433", target: "https://example.org" } as never }).source, "rustc E0433");
});

test("a diagnostic with a source and no code is labelled by the source", () => {
  assert.equal(only({ code: undefined }).source, "basedpyright");
});

test("a diagnostic with a code and no source is labelled by the code", () => {
  assert.equal(only({ source: undefined, code: 6133 }).source, "6133");
});

test("a diagnostic with neither has no label", () => {
  assert.equal("source" in only({ source: undefined, code: undefined }), false);
});

test("Unnecessary fades the text", () => {
  assert.equal(only({ severity: 4, tags: [1] }).markClass, "cstudy-unnecessary");
});

test("Deprecated strikes the text through", () => {
  assert.equal(only({ severity: 2, tags: [2] }).markClass, "cstudy-deprecated");
});

test("both tags give both classes", () => {
  assert.equal(only({ tags: [1, 2] }).markClass, "cstudy-unnecessary cstudy-deprecated");
});

test("no tag gives no class", () => {
  assert.equal("markClass" in only({}), false);
});

test("an unknown tag gives no class", () => {
  assert.equal("markClass" in only({ tags: [9] }), false);
});

test("a range that ends before it starts is put in order", () => {
  const found = only({ range: { start: { line: 2, character: 0 }, end: { line: 1, character: 0 } } });
  assert.deepEqual([found.from, found.to], [100, 200]);
});

test("every diagnostic of a publication is converted, in order", () => {
  const found = liveDiagnostics([published({ message: "a" }), published({ message: "b" })], offsetOf);
  assert.deepEqual(
    found.map((one) => one.message),
    ["a", "b"],
  );
});

test("a label is built from the source and the code", () => {
  assert.equal(diagnosticLabel({ source: "ts", code: 2304 }), "ts 2304");
});

test("an LSP position is the offset of its 0-based line and character", () => {
  assert.equal(lspOffset(DOC, { line: 1, character: 4 }), 19);
});

test("an LSP character past the end of its line is the end of the line", () => {
  assert.equal(lspOffset(DOC, { line: 0, character: 99 }), 14);
});

test("an LSP line past the last is the end of the last line", () => {
  assert.equal(lspOffset(DOC, { line: 9, character: 2 }), 34);
});

test("a negative LSP position is the start of the document", () => {
  assert.equal(lspOffset(DOC, { line: -1, character: -3 }), 0);
});
