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

test("finishing waits for the answer to a read that went out before it, so the server takes that read first", async () => {
  const ending = new AttemptEnding();
  let answer = () => {};
  void ending.reading(new Promise<void>((resolve) => (answer = resolve)));
  let begun = false;
  const finishing = ending.finishing().then(() => (begun = true));

  await new Promise((resolve) => setTimeout(resolve, 0));
  const beforeTheAnswer = begun;
  answer();
  await finishing;

  assert.deepEqual([beforeTheAnswer, begun], [false, true]);
});

test("finishing goes ahead once a read that went out fails", async () => {
  const ending = new AttemptEnding();
  ending.reading(Promise.reject(new Error("offline"))).catch(() => {});

  await ending.finishing();
});

test("finishing with no read out goes ahead at once", async () => {
  const ending = new AttemptEnding();
  const answered = ending.reading(Promise.resolve("status"));

  assert.deepEqual(await Promise.all([answered, ending.finishing()]), ["status", undefined]);
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
