import assert from "node:assert/strict";
import { test } from "node:test";

import { Text } from "@codemirror/state";

import { cursorPosition, documentLine } from "../src/positions.ts";

// Line 1 spans 0-14, line 2 spans 15-33, line 3 is empty at 34.
const DOC = Text.of(["def deposit():", "    return balance", ""]);

test("a line inside the document is that line", () => {
  assert.equal(documentLine(DOC, 2).from, 15);
});

test("a line before the first is the first", () => {
  assert.equal(documentLine(DOC, 0).number, 1);
});

test("a line past the last is the last", () => {
  assert.equal(documentLine(DOC, 9).number, 3);
});

test("a line and column is that character", () => {
  assert.equal(cursorPosition(DOC, 2, 12), 26);
});

test("a line without a column is its start", () => {
  assert.equal(cursorPosition(DOC, 2, null), 15);
});

test("a column past the end of the line is the line's end", () => {
  assert.equal(cursorPosition(DOC, 1, 40), 14);
});

test("a column before the first is the line's start", () => {
  assert.equal(cursorPosition(DOC, 2, 0), 15);
});

test("a line past the document is on the last line", () => {
  assert.equal(cursorPosition(DOC, 9, 5), 34);
});
