import assert from "node:assert/strict";
import { test } from "node:test";

import { languageName, languageRow, segmentOf } from "../src/page/intelligence-status.ts";

const PYTHON = { language: "python", server: "basedpyright" };

test("a starting session names its language and server", () => {
  assert.equal(segmentOf({ kind: "session", ...PYTHON, state: { kind: "starting" } }).text, "python · basedpyright · starting");
});

test("a ready session says ready", () => {
  assert.equal(segmentOf({ kind: "session", ...PYTHON, state: { kind: "ready" } }).text, "python · basedpyright · ready");
});

test("a reconnecting session says so with an ellipsis", () => {
  assert.equal(segmentOf({ kind: "session", ...PYTHON, state: { kind: "reconnecting" } }).text, "python · basedpyright · reconnecting…");
});

test("a stopped session offers Restart and names why", () => {
  const segment = segmentOf({ kind: "session", ...PYTHON, state: { kind: "stopped", why: "exit 1", reason: "exit 1: boom" } });
  assert.deepEqual([segment.text, segment.action, segment.title], ["python · basedpyright · stopped: exit 1", "restart", "exit 1: boom"]);
});

test("a stopped session with no reason says only stopped", () => {
  const segment = segmentOf({ kind: "session", ...PYTHON, state: { kind: "stopped", why: "", reason: "" } });
  assert.deepEqual([segment.text, segment.action], ["python · basedpyright · stopped", "restart"]);
});

test("a language whose server is not installed links to Health", () => {
  const segment = segmentOf({ kind: "not-installed", language: "python", server: "basedpyright" });
  assert.deepEqual([segment.text, segment.action], ["no code intelligence for Python: basedpyright is not installed", "health"]);
});

test("a language with no server yet says so", () => {
  const segment = segmentOf({ kind: "no-server", language: "go" });
  assert.deepEqual([segment.text, segment.action], ["no code intelligence for Go yet", null]);
});

test("the other states have no action", () => {
  for (const kind of ["starting", "ready", "reconnecting"] as const) {
    assert.equal(segmentOf({ kind: "session", ...PYTHON, state: { kind } }).action, null);
  }
});

test("languages have their display names", () => {
  assert.deepEqual(["python", "typescript", "go", "rust", "java", "kotlin"].map(languageName), [
    "Python",
    "TypeScript",
    "Go",
    "Rust",
    "Java",
    "Kotlin",
  ]);
});

test("a language the page does not know keeps its name", () => {
  assert.equal(languageName("zig"), "zig");
});

const STATE = {
  language: "python",
  server: "basedpyright",
  version: "1.40.2",
  state: "installed",
  detail: "basedpyright 1.40.2",
  idle_s: 60,
} as const;

test("an installed language's row names its server and version", () => {
  assert.deepEqual(languageRow(STATE), { name: "Python", detail: "basedpyright 1.40.2", health: false });
});

test("a language that is not installed links to the Health view", () => {
  const row = languageRow({ ...STATE, language: "typescript", state: "not_installed", detail: "not installed: run cstudy doctor --fix" });
  assert.deepEqual(row, { name: "TypeScript", detail: "not installed: run cstudy doctor --fix", health: true });
});

test("a language with no server yet does not link", () => {
  const row = languageRow({ language: "go", server: null, version: null, state: "not_available", detail: "not available yet", idle_s: null });
  assert.deepEqual(row, { name: "Go", detail: "not available yet", health: false });
});
