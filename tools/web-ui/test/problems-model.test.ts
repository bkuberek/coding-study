import assert from "node:assert/strict";
import { test } from "node:test";

import { matchesSearch } from "../src/page/problems-model.ts";

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
