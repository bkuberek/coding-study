import assert from "node:assert/strict";
import { test } from "node:test";

import {
  applicableOptions,
  DEFAULT_OPTIONS,
  parseCases,
  type RunContext,
  runBody,
  runCommand,
  type RunOptionsState,
} from "../src/page/run-options.ts";

const TWO_SUM: RunContext = { slug: "two-sum", kind: "function", language: "python", levels: null, oracle: true };
const BANK: RunContext = { slug: "bank", kind: "project", language: "python", levels: { unlocked: 2, last: 4 }, oracle: false };
const QUEUE: RunContext = { slug: "queue", kind: "concurrent", language: "java", levels: null, oracle: false };

function options(change: Partial<RunOptionsState>): RunOptionsState {
  return { ...DEFAULT_OPTIONS, ...change };
}

test("a function problem with an oracle takes cases, stress, seed, a time limit and perf", () => {
  assert.deepEqual([...applicableOptions(TWO_SUM)].sort(), ["cases", "perf", "seed", "stress", "time_limit"]);
});

test("a TypeScript attempt also takes the type check", () => {
  assert.ok(applicableOptions({ ...TWO_SUM, language: "typescript" }).has("typecheck"));
});

test("a function problem without an oracle takes no stress", () => {
  assert.equal(applicableOptions({ ...TWO_SUM, oracle: false }).has("stress"), false);
});

test("a project takes a level and cases only", () => {
  assert.deepEqual([...applicableOptions(BANK)].sort(), ["cases", "level"]);
});

test("a concurrent problem takes stress but no perf", () => {
  const applicable = applicableOptions(QUEUE);
  assert.deepEqual([applicable.has("stress"), applicable.has("perf")], [true, false]);
});

test("a run's body sends what is set and applies", () => {
  const body = runBody(7, "test", options({ cases: ["ex1"], stress: 30, level: 2 }), TWO_SUM);
  assert.deepEqual(body, { attempt_id: 7, command: "test", cases: ["ex1"], stress: 30 });
});

test("a submission sends its level only", () => {
  const body = runBody(7, "submit", options({ cases: ["ex1"], level: 1 }), BANK);
  assert.deepEqual(body, { attempt_id: 7, command: "submit", level: 1 });
});

test("perf is left out with cases, which it never runs with", () => {
  const body = runBody(7, "test", options({ cases: ["ex1"], perf: true }), TWO_SUM);
  assert.equal("perf" in body, false);
});

test("the type check follows the preference unless it is set", () => {
  const body = runBody(7, "test", DEFAULT_OPTIONS, { ...TWO_SUM, language: "typescript" });
  assert.equal("typecheck" in body, false);
});

test("the command names the attempt's language for a single-file problem", () => {
  assert.equal(runCommand("test", DEFAULT_OPTIONS, TWO_SUM), "cstudy test two-sum --lang python");
});

test("the command names every option it runs with", () => {
  const command = runCommand("test", options({ cases: ["ex1", "h2"], stress: 30, seed: 14, time_limit: "5x", perf: true }), TWO_SUM);
  assert.equal(command, "cstudy test two-sum --lang python --case ex1 --case h2 --stress 30 --seed 14 --time-limit=5x");
});

test("a project's command has no language", () => {
  assert.equal(runCommand("submit", options({ level: 1 }), BANK), "cstudy submit bank --level 1");
});

test("time limits switched off say so", () => {
  assert.equal(runCommand("test", options({ time_limit: false }), TWO_SUM), "cstudy test two-sum --lang python --no-time-limit");
});

test("case ids are read from commas and spaces", () => {
  assert.deepEqual(parseCases(" ex1, h2  tests/test_a.py::test_b ,"), ["ex1", "h2", "tests/test_a.py::test_b"]);
});
