import assert from "node:assert/strict";
import { test } from "node:test";

import { activeFilters, countWords, matchesSearch } from "../src/page/problems-model.ts";

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
