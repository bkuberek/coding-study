import assert from "node:assert/strict";
import { test } from "node:test";

import { workKey } from "../src/worker/workKey.ts";

test("the same text at the same version is the same work", () => {
  assert.equal(workKey("Invoice 7", 1), workKey("Invoice 7", 1));
});

test("a version bump is new work", () => {
  assert.notEqual(workKey("Invoice 7", 1), workKey("Invoice 7", 2));
});

test("the two parts cannot run together", () => {
  assert.notEqual(workKey("Form-1", 2), workKey("Form-", 12));
  assert.notEqual(workKey("2-Form", 1), workKey("-Form", 12));
});
