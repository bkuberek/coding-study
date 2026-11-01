import assert from "node:assert/strict";
import { test } from "node:test";

import { textChange } from "../src/text-change.ts";

function applied(from: string, to: string): string {
  const change = textChange(from, to);
  return change === null ? from : from.slice(0, change.from) + change.insert + from.slice(change.to);
}

test("the same text is no change", () => {
  assert.equal(textChange("a\nb\n", "a\nb\n"), null);
});

test("a line changed in the middle replaces only what differs", () => {
  assert.deepEqual(textChange("one\ntwo\nthree\n", "one\nTWO\nthree\n"), { from: 4, to: 7, insert: "TWO" });
});

test("text added at the end is inserted there", () => {
  assert.deepEqual(textChange("one\n", "one\ntwo\n"), { from: 4, to: 4, insert: "two\n" });
});

test("text removed at the start is deleted there", () => {
  assert.deepEqual(textChange("one\ntwo\n", "two\n"), { from: 0, to: 4, insert: "" });
});

test("a repeated letter is changed once, not twice", () => {
  assert.deepEqual(textChange("aaa", "aa"), { from: 2, to: 3, insert: "" });
});

test("replacing the whole text gives the new text", () => {
  assert.equal(applied("class Bank:\n    pass\n", "# empty\n"), "# empty\n");
});

test("emptying the text deletes it all", () => {
  assert.deepEqual(textChange("abc", ""), { from: 0, to: 3, insert: "" });
});

test("Windows line ends read as the editor's", () => {
  assert.equal(textChange("one\ntwo\n", "one\r\ntwo\r\n"), null);
});
