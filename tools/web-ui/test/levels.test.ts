import assert from "node:assert/strict";
import { test } from "node:test";

import { bestLine, goalLines, pastStatus, ratingRule } from "../src/page/levels.ts";
import type { History } from "../src/page/types.ts";

const LEVELS: NonNullable<History["levels"]> = {
  last: 4,
  mastered: 2,
  languages: [
    { language: "python", best: 2, last_time: 2, try_level: 3 },
    { language: "kotlin", best: 4, last_time: 4, try_level: null },
    { language: "go", best: null, last_time: null, try_level: null },
  ],
};

test("a pass below the last level reads through which, as cstudy history writes it", () => {
  assert.equal(pastStatus({ status: "passed", levels_passed: 2, levels_total: 4 }), "passed through level 2 of 4");
});

test("a pass of every level reads passed", () => {
  assert.equal(pastStatus({ status: "passed", levels_passed: 4, levels_total: 4 }), "passed");
});

test("an attempt without levels reads its status", () => {
  assert.equal(pastStatus({ status: "failed", levels_passed: null, levels_total: null }), "failed");
});

test("a failed attempt reads failed whatever levels it passed", () => {
  assert.equal(pastStatus({ status: "failed", levels_passed: 2, levels_total: 4 }), "failed");
});

test("the best line names each language passed, as cstudy history does", () => {
  assert.equal(bestLine(LEVELS), "python through level 2 of 4 · kotlin through level 4 of 4");
});

test("without a pass, or without levels, there is no best line", () => {
  assert.equal(bestLine({ last: 4, mastered: 0, languages: [] }), null);
  assert.equal(bestLine(null), null);
});

test("each language with a level to try has its goal", () => {
  assert.deepEqual(goalLines(LEVELS), ["python: last time: through level 2 of 4; try level 3"]);
});

test("a problem without levels has no goal", () => {
  assert.deepEqual(goalLines(null), []);
});

const STATUS = { kind: "progressive", mode: "new", levels: { unlocked: 2, last: 4 } };

test("a rating of a problem with levels needs level 1, and passes through the levels passed", () => {
  assert.equal(
    ratingRule(STATUS),
    "a rating needs the latest run to pass every case of level 1 at least, and passes the attempt through the levels it passed; giving up grades again",
  );
});

test("a project's rating reads its latest submission", () => {
  assert.match(ratingRule({ ...STATUS, kind: "project" }), /^a rating needs the latest submission of every unlocked level to pass level 1/);
});

test("a mock still needs every case, as before level passes", () => {
  assert.equal(ratingRule({ ...STATUS, mode: "mock" }), "a rating needs the latest run to pass every case; giving up grades again");
});

test("a problem without levels needs every case", () => {
  assert.equal(ratingRule({ kind: "function", mode: "new", levels: null }), "a rating needs the latest run to pass every case; giving up grades again");
});

test("an item takes a rating only", () => {
  assert.equal(ratingRule({ kind: "item", mode: "new", levels: null }), "an item takes a rating only, graded by it alone");
});
