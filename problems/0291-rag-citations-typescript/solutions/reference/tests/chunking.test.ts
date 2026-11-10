import assert from "node:assert/strict";
import { test } from "node:test";

import { chunkCount, chunksOf, wordsOf } from "../src/chunking.ts";

function numbered(count: number): string[] {
  return Array.from({ length: count }, (_, index) => `w${index + 1}`);
}

test("20 words are one chunk", () => {
  assert.deepEqual(chunksOf(numbered(20)), [numbered(20).join(" ")]);
});

test("21 words are two chunks, the second starting 5 words before the end of the first", () => {
  assert.deepEqual(chunksOf(numbered(21)), [
    numbered(20).join(" "),
    numbered(21).slice(15).join(" "),
  ]);
});

test("35 words end with the second chunk, with no third", () => {
  assert.equal(chunksOf(numbered(35)).length, 2);
});

test("the count agrees with the chunks for every length up to 200 words", () => {
  for (let count = 1; count <= 200; count += 1) {
    assert.equal(chunkCount(numbered(count)), chunksOf(numbered(count)).length, `${count} words`);
  }
});

test("any run of whitespace separates two words", () => {
  assert.deepEqual(wordsOf("  one\n\ntwo\tthree  four "), ["one", "two", "three", "four"]);
});
