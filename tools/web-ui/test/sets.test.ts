import assert from "node:assert/strict";
import { test } from "node:test";

import { membershipLabel, membershipWords, setsHolding } from "../src/page/setControl.ts";
import { movesOf, setNameIssue, standingWords } from "../src/page/sets-model.ts";

const SETS = [
  { name: "backend-loop", description: null, slugs: ["two-sum", "lru-cache"], passed: 0, total: 2, missing: [] },
  { name: "data-loop", description: "Later", slugs: ["two-sum"], passed: 1, total: 1, missing: [] },
  { name: "empty", description: null, slugs: [], passed: 0, total: 0, missing: [] },
];

test("a problem may be in several sets", () => {
  assert.deepEqual(setsHolding(SETS, "two-sum"), ["backend-loop", "data-loop"]);
});

test("a problem in no set is in none", () => {
  assert.deepEqual(setsHolding(SETS, "url-shortener"), []);
});

test("the control of a problem in no set offers to add it", () => {
  assert.equal(membershipLabel([]), "+ set");
});

test("the control of a problem in one set names it", () => {
  assert.equal(membershipLabel(["backend-loop"]), "backend-loop");
});

test("the control of a problem in several names the first and counts the others", () => {
  assert.equal(membershipLabel(["backend-loop", "data-loop", "empty"]), "backend-loop +2");
});

test("assistive technology hears every set", () => {
  assert.equal(membershipWords("two-sum", ["backend-loop", "data-loop"]), "two-sum is in backend-loop and data-loop: change its sets");
});

test("assistive technology hears when there is none", () => {
  assert.equal(membershipWords("two-sum", []), "two-sum is in no set: add it to one");
});

test("assistive technology hears three sets in a list", () => {
  assert.equal(membershipWords("two-sum", ["a", "b", "c"]), "two-sum is in a, b and c: change its sets");
});

test("a kebab-case slug can name a set", () => {
  assert.equal(setNameIssue("backend-loop"), null);
});

test("an empty name asks for one", () => {
  assert.equal(setNameIssue(""), "name the set");
});

test("anything else says what to use", () => {
  assert.equal(setNameIssue("Backend Loop"), "use lowercase letters, digits and hyphens, starting with a letter, such as backend-loop");
});

test("a name too long is refused", () => {
  assert.notEqual(setNameIssue("a".repeat(65)), null);
});

test("the standing is passed of total", () => {
  assert.equal(standingWords({ passed: 1, total: 3, missing: [] }), "1 of 3 passed");
});

test("the standing counts what the catalog lost", () => {
  assert.equal(standingWords({ passed: 1, total: 3, missing: ["gone"] }), "1 of 3 passed · 1 missing");
});

test("the first row moves down only", () => {
  assert.deepEqual(movesOf(1, 3), { up: null, down: 2 });
});

test("a row in the middle moves both ways", () => {
  assert.deepEqual(movesOf(2, 3), { up: 1, down: 3 });
});

test("the last row moves up only", () => {
  assert.deepEqual(movesOf(3, 3), { up: 2, down: null });
});

test("a row on its own does not move", () => {
  assert.deepEqual(movesOf(1, 1), { up: null, down: null });
});
