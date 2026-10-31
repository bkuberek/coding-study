import assert from "node:assert/strict";
import { test } from "node:test";

import { caseFacts, caseLines, durationText, inputText, levelLine, stressFacts, testName } from "../src/page/results-format.ts";
import type { CaseRow } from "../src/page/results-model.ts";
import type { CaseResult, LevelResult } from "../src/page/run-events.ts";

function row(result: Partial<CaseResult> = {}, fields: Partial<CaseRow> = {}): CaseRow {
  const full: CaseResult = { type: "case_result", id: "h3", visible: false, generated: false, status: "fail", duration_ns: 31000, level: null, ...result };
  return { id: full.id, visible: full.visible, oracle: false, seed: null, n: null, level: full.level, status: full.status, result: full, ...fields };
}

const LEVEL: LevelResult = { type: "level_result", status: "fail", level: 2, total: 5, passed: 4, visible_total: 2, visible_passed: 2, hidden_total: 3, hidden_passed: 2 };

test("a call's duration reads in milliseconds", () => {
  assert.equal(durationText(41000), "0.04ms");
});

test("a long duration reads in seconds", () => {
  assert.equal(durationText(2_600_000_000), "2.6s");
});

test("arguments by name read as the report writes them", () => {
  assert.equal(inputText({ nums: [-3, 8, 0, 3], target: 0 }), "nums=[-3, 8, 0, 3]  target=0");
});

test("operations read as the report writes them", () => {
  assert.equal(inputText({ ops: ["Bank", "deposit"], args: [[], [1, 5]] }), 'ops ["Bank", "deposit"]  args [[], [1, 5]]');
});

test("a hidden case's facts say so", () => {
  assert.equal(caseFacts(row()), "hidden · 0.03ms");
});

test("a case's facts name its level", () => {
  assert.equal(caseFacts(row({ level: 2, visible: true, status: "pass" })), "level 2 · 0.03ms");
});

test("an oracle input's facts name its size", () => {
  assert.equal(caseFacts(row({}, { oracle: true, n: 4, seed: 14 })), "oracle · n=4");
});

test("a time-limit verdict gives the time, the limit and its basis", () => {
  const facts = caseFacts(row({ status: "tle", duration_ns: 412_000_000, time_limit_ms: 95, time_limit_basis: "5x hash-map, calibrated" }));
  assert.equal(facts, "hidden · 412ms > limit 95ms (5x hash-map, calibrated)");
});

test("a wrong answer shows its input, expected and actual", () => {
  const lines = caseLines(row({ input: { target: 0 }, expected: [0, 3], actual: [3, 3] }).result);
  assert.deepEqual(lines, [
    ["input", "target=0"],
    ["expected", "[0, 3]"],
    ["actual", "[3, 3]"],
  ]);
});

test("an exception shows its type, message and trace", () => {
  const lines = caseLines(row({ status: "error", error: { type: "KeyError", message: "7", trace: "bank.py:12 in deposit" } }).result);
  assert.deepEqual(lines, [
    ["error", "KeyError: 7"],
    ["trace", "bank.py:12 in deposit"],
  ]);
});

test("a stress case's facts count its runs and give the median", () => {
  const facts = stressFacts("virtual", { runs: 3, runs_passed: 1, median_ms: 38 });
  assert.equal(facts, "virtual · 1/3 runs passed · median 38ms");
});

test("a submission's level line counts visible and hidden cases", () => {
  assert.equal(levelLine(LEVEL, false), "4/5 (2 visible, 3 hidden)");
});

test("a mock submission's level line counts its failing hidden cases only", () => {
  assert.equal(levelLine(LEVEL, true), "4/5 (2 visible, 3 hidden) · 1 hidden case failed");
});

test("a test's name is its last part", () => {
  assert.equal(testName("tests/test_level_1.py::TestBank::test_ex1"), "TestBank::test_ex1");
});
