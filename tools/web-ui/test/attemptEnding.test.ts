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

test("an ended attempt holds every read", () => {
  const ending = new AttemptEnding();

  ending.end(() => {});

  assert.deepEqual([ending.ended, ending.holds()], [true, true]);
});

test("a live attempt holds no read", () => {
  const ending = new AttemptEnding();

  assert.deepEqual([ending.ended, ending.holds()], [false, false]);
});

test("reads wait while this tab finishes the attempt", () => {
  const ending = new AttemptEnding();

  ending.finishing();

  assert.equal(ending.holds(), true);
});

test("a finish that failed lets reads go on, and says whether one was held back", () => {
  const ending = new AttemptEnding();
  ending.finishing();
  ending.holds();

  assert.deepEqual([ending.failed(), ending.holds()], [true, false]);
});

test("a finish that failed with no read held back says so", () => {
  const ending = new AttemptEnding();
  ending.finishing();

  assert.equal(ending.failed(), false);
});

test("a finish that succeeded shows the attempt ended once, even after reads came meanwhile", () => {
  const ending = new AttemptEnding();
  let shown = 0;
  ending.finishing();
  ending.holds();

  ending.end(() => shown++);
  ending.end(() => shown++);

  assert.deepEqual([shown, ending.failed()], [1, false]);
});
