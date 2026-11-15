import assert from "node:assert/strict";
import { test } from "node:test";

import { selfGraded } from "../src/page/kinds.ts";

test("system design and code review problems are graded by the person", () => {
  assert.deepEqual(["system-design", "code-review"].map(selfGraded), [true, true]);
});

test("every kind checked by tests is not", () => {
  assert.deepEqual(["function", "design", "progressive", "concurrent", "project"].map(selfGraded), [false, false, false, false, false]);
});
