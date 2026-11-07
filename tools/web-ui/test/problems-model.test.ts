import assert from "node:assert/strict";
import { test } from "node:test";

import { activeFilters, canHide, counted, countWords, DEFAULT_COLUMNS, matchesSearch, shownColumns, withColumn } from "../src/page/problems-model.ts";

const TWO_SUM = { slug: "two-sum", title: "Two Sum" };
const LRU = { slug: "lru-cache", title: "LRU Cache" };

test("a search finds a word of the slug", () => {
  assert.equal(matchesSearch(LRU, "cache"), true);
});

test("a search finds what only the title holds", () => {
  assert.equal(matchesSearch(TWO_SUM, "two sum"), true);
});

test("a search ignores case and the spaces around it", () => {
  assert.equal(matchesSearch(LRU, "  lru C "), true);
});

test("an empty search matches everything", () => {
  assert.equal(matchesSearch(TWO_SUM, "   "), true);
});

test("a search leaves out what neither holds", () => {
  assert.equal(matchesSearch(TWO_SUM, "lru"), false);
});

test("the active filters follow the route's order, without the search", () => {
  assert.deepEqual(activeFilters({ search: "two", domain: "backend", lang: "go" }), [
    { key: "lang", value: "go", words: "lang: go" },
    { key: "domain", value: "backend", words: "domain: backend" },
  ]);
});

test("a status filter reads in words", () => {
  assert.deepEqual(activeFilters({ status: "in_progress" }), [{ key: "status", value: "in_progress", words: "status: in progress" }]);
});

test("no filter is no chip", () => {
  assert.deepEqual(activeFilters({}), []);
});

test("the count says how many of the whole list show", () => {
  assert.equal(countWords(8, 292), "8 of 292");
});

test("without the whole list the count says only what shows", () => {
  assert.equal(countWords(8, null), "8");
});

test("the columns show in the table's order, whatever order they were chosen in", () => {
  assert.deepEqual(shownColumns(["status", "domain", "problem", "id"]), ["id", "problem", "domain", "status"]);
});

test("problem and status always show", () => {
  assert.deepEqual(shownColumns(["id"]), ["id", "problem", "status"]);
});

test("a column the page does not know is left out", () => {
  assert.deepEqual(shownColumns(["problem", "status", "price"]), ["problem", "status"]);
});

test("ticking a column adds it in the table's order", () => {
  assert.deepEqual(withColumn(DEFAULT_COLUMNS, "kind", true), ["id", "problem", "difficulty", "pattern", "kind", "status", "due", "languages", "sets"]);
});

test("unticking a column takes it out", () => {
  assert.deepEqual(withColumn(["problem", "status", "id"], "id", false), ["problem", "status"]);
});

test("problem and status cannot be hidden, and the others can", () => {
  assert.deepEqual([canHide("problem"), canHide("status"), canHide("id"), canHide("sets")], [false, false, true, true]);
});

test("a count of one has no plural", () => {
  assert.deepEqual([counted(1, "problem"), counted(0, "item"), counted(8, "problem")], ["1 problem", "0 items", "8 problems"]);
});
