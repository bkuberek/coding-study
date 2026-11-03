import assert from "node:assert/strict";
import { test } from "node:test";

import { addsCursor } from "../src/setup.ts";

const NONE = { altKey: false, shiftKey: false, metaKey: false, ctrlKey: false };

test("Alt-Shift-click adds a cursor", () => {
  assert.equal(addsCursor({ ...NONE, altKey: true, shiftKey: true }), true);
});

test("Alt-Shift-click adds a cursor whatever else is held", () => {
  assert.equal(addsCursor({ altKey: true, shiftKey: true, metaKey: true, ctrlKey: true }), true);
});

test("Cmd-click does not add a cursor", () => {
  assert.equal(addsCursor({ ...NONE, metaKey: true }), false);
});

test("Ctrl-click does not add a cursor", () => {
  assert.equal(addsCursor({ ...NONE, ctrlKey: true }), false);
});

test("Alt alone, as rectangular selection starts, does not add a cursor", () => {
  assert.equal(addsCursor({ ...NONE, altKey: true }), false);
});

test("Shift alone, which extends the selection, does not add a cursor", () => {
  assert.equal(addsCursor({ ...NONE, shiftKey: true }), false);
});

test("a plain click does not add a cursor", () => {
  assert.equal(addsCursor(NONE), false);
});
