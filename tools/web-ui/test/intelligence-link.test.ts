import assert from "node:assert/strict";
import { test } from "node:test";

import { decide } from "../src/page/intelligence.ts";
import type { LanguageState } from "../src/page/types.ts";

const STATES: readonly LanguageState[] = [
  { language: "python", server: "basedpyright", version: "1.40.2", state: "installed", detail: "basedpyright 1.40.2", idle_s: 60 },
  { language: "typescript", server: "typescript-language-server", version: "6.0.3", state: "not_installed", detail: "not installed: run cstudy doctor --fix", idle_s: 60 },
  { language: "go", server: null, version: null, state: "not_available", detail: "not available yet", idle_s: null },
];

test("a Python file of a Python attempt with its server installed attaches", () => {
  assert.deepEqual(decide("a.py", "python", STATES), { kind: "attach", language: "python", server: "basedpyright", idleS: 60 });
});

test("a TypeScript file whose server is not installed says so", () => {
  assert.deepEqual(decide("a.ts", "typescript", STATES), { kind: "show", found: { kind: "not-installed", language: "typescript", server: "typescript-language-server" } });
});

test("a JavaScript file goes to the TypeScript server", () => {
  assert.equal(decide("a.js", "typescript", STATES).kind, "show");
});

test("a Go file says that there is no server yet", () => {
  assert.deepEqual(decide("a.go", "go", STATES), { kind: "show", found: { kind: "no-server", language: "go" } });
});

test("a Markdown file works as it does without code intelligence", () => {
  assert.deepEqual(decide("notes.md", "python", STATES), { kind: "none" });
});

test("a file of another language than the attempt's is left alone", () => {
  assert.deepEqual(decide("a.ts", "python", STATES), { kind: "none" });
});

test("an attempt with no language, as an item has, is left alone", () => {
  assert.deepEqual(decide("a.py", null, STATES), { kind: "none" });
});

test("a language the list does not know is left alone", () => {
  assert.deepEqual(decide("a.rs", "rust", STATES), { kind: "none" });
});

test("a file that could have a server waits for the list", () => {
  assert.deepEqual(decide("a.py", "python", null), { kind: "waiting" });
});

test("a file that could not have one does not wait for the list", () => {
  assert.deepEqual(decide("notes.md", "python", null), { kind: "none" });
});
