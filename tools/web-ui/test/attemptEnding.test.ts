import assert from "node:assert/strict";
import { test } from "node:test";

import { AttemptEnding } from "../src/page/attemptEnding.ts";

test("an attempt that ended is shown ended once, however many reads find it so", () => {
  const ending = new AttemptEnding();
  let shown = 0;
  const show = () => shown++;

  ending.end(show);
  ending.end(show);

  assert.equal(shown, 1);
});

test("an ended attempt says so", () => {
  const ending = new AttemptEnding();

  ending.end(() => {});

  assert.equal(ending.ended, true);
});

test("a live attempt does not", () => {
  assert.equal(new AttemptEnding().ended, false);
});
