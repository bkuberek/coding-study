import assert from "node:assert/strict";
import { test } from "node:test";

import { caseLines } from "../src/page/results-format.ts";
import { headerText, RunModel, resultsView, STATUS_WORDS, type ViewItem } from "../src/page/results-model.ts";
import type { CaseResult, Planned, RunEvent, RunStart, StressRun } from "../src/page/run-events.ts";

const PLANNED: Planned = { cases: 16, visible: 2, hidden: 13, generated: 1, oracle_inputs: 0, stress: null };

function start(fields: Partial<RunStart> = {}): RunStart {
  return {
    type: "run_start",
    command: "test",
    slug: "two-sum",
    language: "python",
    attempt_id: 1,
    mode: "new",
    levels: null,
    kind: "function",
    timer: null,
    time_limit: null,
    planned: PLANNED,
    ...fields,
  };
}

function result(id: string, fields: Partial<CaseResult> = {}): CaseResult {
  return { type: "case_result", id, visible: false, generated: false, status: "pass", duration_ns: 1000, level: null, ...fields };
}

function oracle(seed: number, n: number, status: CaseResult["status"]): CaseResult {
  return result(`oracle-${seed}`, { oracle: true, seed, n, status });
}

function stressRun(run: number, status: StressRun["status"]): StressRun {
  return { type: "stress_run", id: "s1", variant: "virtual", run, seed: 1000 + run, status, duration_ns: 1, reasons: status === "pass" ? [] : ["lost an update"] };
}

function played(...events: RunEvent[]): RunModel {
  const model = new RunModel();
  for (const event of [start(), ...events]) model.apply(event);
  return model;
}

function shown(model: RunModel, showAll = false): string[] {
  return resultsView(model, showAll).items.map(describe);
}

function describe(item: ViewItem): string {
  switch (item.kind) {
    case "case":
    case "test":
      return `${item.row.status} ${item.row.id}`;
    case "count":
      return `${STATUS_WORDS[item.status]} ${item.text}`;
    case "more":
      return item.text;
    case "file":
      return `file ${item.path}`;
    case "stress":
      return `stress ${item.group.id} ${item.group.variant} ${item.group.runs.join(",")}${item.group.level === null ? "" : ` level ${item.group.level}`}`;
    case "level":
      return `level ${item.result.level} ${item.result.status}`;
  }
}

// the header

test("a single-file run's header counts its cases as the report does", () => {
  assert.equal(headerText(start()), "two-sum · python · 16 cases (2 visible, 13 hidden, 1 generated)");
});

test("the header names the time limit and the timer", () => {
  const header = headerText(start({ time_limit: "5x", timer: { elapsed_s: 751, limit_s: 1500 } }));
  assert.equal(header, "two-sum · python · 16 cases (2 visible, 13 hidden, 1 generated) · time limit 5x · timer 12:31 / 25:00");
});

test("the header counts oracle inputs", () => {
  const header = headerText(start({ planned: { ...PLANNED, oracle_inputs: 30 } }));
  assert.equal(header, "two-sum · python · 16 cases (2 visible, 13 hidden, 1 generated) · 30 oracle inputs");
});

test("the header counts stress runs, a single variant in the singular", () => {
  const planned = { ...PLANNED, stress: { cases: 2, variants: 1, runs: 3 } };
  assert.equal(headerText(start({ planned })).split(" · ").at(-1), "2 stress × 1 variant × 3 runs");
});

test("a project test run's header names its levels", () => {
  const header = headerText(start({ slug: "bank", kind: "project", planned: null, levels: { up_to: 2, unlocked: 2, last: 4 } }));
  assert.equal(header, "bank · python · levels 1-2 of 4");
});

test("a submission's header says so", () => {
  const header = headerText(start({ command: "submit", slug: "bank", kind: "project", planned: null, levels: { up_to: 1, unlocked: 1, last: 4 } }));
  assert.equal(header, "bank · python · submit level 1 of 4");
});

// cases

test("a case that started is running, apart from the rows", () => {
  const model = played({ type: "case_start", id: "ex1", visible: true, level: null });
  assert.deepEqual([shown(model), resultsView(model, false).running], [[], ["ex1"]]);
});

test("a visible case shows with its status", () => {
  assert.deepEqual(shown(played(result("ex1", { visible: true }))), ["pass ex1"]);
});

test("passing hidden cases collapse into a count", () => {
  assert.deepEqual(shown(played(result("h1"), result("h2"))), ["PASS 2 hidden cases"]);
});

test("one passing hidden case counts in the singular", () => {
  assert.deepEqual(shown(played(result("h1"))), ["PASS 1 hidden case"]);
});

test("show all lists the passing hidden cases", () => {
  assert.deepEqual(shown(played(result("h1"), result("h2")), true), ["pass h1", "pass h2"]);
});

test("a failing hidden case shows", () => {
  assert.deepEqual(shown(played(result("h1", { status: "fail" }), result("h2"))), ["fail h1", "PASS 1 hidden case"]);
});

test("a revision gives a case its time-limit verdict", () => {
  const model = played(result("g1", { generated: true }), { ...result("g1"), type: "case_revised", status: "tle", time_limit_ms: 95 });
  assert.deepEqual(shown(model), ["tle g1"]);
});

test("a case on the virtual clock that deadlocked is a STALLED row that names the operation and the virtual time", () => {
  const stalled = result("h4", {
    status: "stalled",
    level: 2,
    input: { ops: ["MessageLog", "@spawn", "@advance", "@join"], args: [[30000], ["r1", "receive", 5000], [2000], ["r1"]] },
    op_index: 3,
    reason: "op 3 (@join r1): deadlock at 2000 ms",
  });
  assert.deepEqual(shown(played(stalled)), ["stalled h4"]);
  assert.deepEqual(caseLines(stalled), [
    ["input", 'ops ["MessageLog", "@spawn", "@advance", "@join"]  args [[30000], ["r1", "receive", 5000], [2000], ["r1"]]'],
    ["reason", "op 3 (@join r1): deadlock at 2000 ms"],
  ]);
});

test("a stalled case counts in the summary as the report counts it", () => {
  const model = played(result("h4", { status: "stalled", op_index: 1, reason: "op 1 (hold): deadlock at 0 ms" }), {
    type: "run_end",
    outcome: "failed",
    exit_code: 1,
    message: null,
    summary: null,
  });
  assert.equal(resultsView(model, false).summary?.text, "0/1 passed · 1 stalled");
});

test("a progressive case keeps its level", () => {
  const model = played(result("ex1", { visible: true, level: 2 }));
  const [item] = resultsView(model, false).items;
  assert.equal(item?.kind === "case" ? item.row.level : null, 2);
});

// oracle inputs

test("failing oracle inputs show smallest n first, three of them", () => {
  const model = played(oracle(1, 5, "fail"), oracle(2, 9, "fail"), oracle(3, 4, "fail"), oracle(4, 30, "fail"), oracle(5, 2, "pass"));
  assert.deepEqual(shown(model), ["fail oracle-3", "fail oracle-1", "fail oracle-2", "1 more oracle input did not pass", "PASS 1 oracle input"]);
});

test("show all lists every oracle input in seed order", () => {
  const model = played(oracle(1, 5, "fail"), oracle(2, 2, "pass"));
  assert.deepEqual(shown(model, true), ["fail oracle-1", "pass oracle-2"]);
});

test("oracle inputs follow the problem's cases", () => {
  const model = played(oracle(1, 5, "fail"), result("ex1", { visible: true }));
  assert.deepEqual(shown(model), ["pass ex1", "fail oracle-1"]);
});

// stress runs

test("a stress case's runs fill in as they end", () => {
  const model = played(
    { type: "stress_run_start", id: "s1", variant: "virtual", run: 0, seed: 1000 },
    stressRun(0, "pass"),
    { type: "stress_run_start", id: "s1", variant: "virtual", run: 1, seed: 1001 },
  );
  assert.deepEqual(shown(model), ["stress s1 virtual pass,running"]);
});

test("a stress case's verdict comes with its result", () => {
  const model = played(stressRun(0, "fail"), {
    type: "stress_result",
    id: "s1",
    variant: "virtual",
    status: "fail",
    runs: 1,
    runs_passed: 0,
    median_ms: null,
    failures: [{ run: 0, seed: 1000, status: "fail", reasons: ["lost an update"] }],
  });
  const [item] = resultsView(model, false).items;
  assert.equal(item?.kind === "stress" ? item.group.result?.status : null, "fail");
});

// project tests

test("a project's tests group under their files", () => {
  const model = played(
    { type: "test_result", id: "tests/test_level_1.py::test_ex1", status: "pass", duration_ns: 1, origin: "level", level: 1 },
    { type: "test_result", id: "tests/test_level_1.py::test_ex2", status: "fail", duration_ns: 1, origin: "level", level: 1 },
    { type: "test_result", id: "tests/test_mine.py::test_x", status: "pass", duration_ns: 1, origin: "yours", level: null },
  );
  assert.deepEqual(shown(model), [
    "file tests/test_level_1.py",
    "pass tests/test_level_1.py::test_ex1",
    "fail tests/test_level_1.py::test_ex2",
    "file tests/test_mine.py",
    "pass tests/test_mine.py::test_x",
  ]);
});

test("a test that started is running", () => {
  const model = played({ type: "test_start", id: "tests/test_level_1.py::test_ex1" });
  assert.deepEqual(resultsView(model, false).running, ["tests/test_level_1.py::test_ex1"]);
});

// levels and the summary

test("a submission's level tallies follow its cases", () => {
  const model = played(result("ex1", { visible: true, level: 1 }), {
    type: "level_result",
    status: "pass",
    level: 1,
    total: 5,
    passed: 5,
    visible_total: 2,
    visible_passed: 2,
    hidden_total: 3,
    hidden_passed: 3,
  });
  assert.deepEqual(shown(model), ["pass ex1", "level 1 pass"]);
});

test("a passing run's summary counts and times it", () => {
  const model = played(result("ex1", { visible: true }), result("h1"), {
    type: "run_end",
    outcome: "passed",
    exit_code: 0,
    message: null,
    summary: { duration_s: 0.94 },
  });
  assert.deepEqual(resultsView(model, false).summary, { tone: "ok", text: "2/2 passed · total 0.9s · all passed", notes: [] });
});

test("a failing run's summary counts each kind of failure as the report does", () => {
  const model = played(result("h1", { status: "fail" }), result("h2", { status: "error" }), result("h3", { status: "error" }), result("g1"), {
    type: "run_end",
    outcome: "failed",
    exit_code: 1,
    message: null,
    summary: { duration_s: 2.6 },
  });
  assert.equal(resultsView(model, false).summary?.text, "1/4 passed · 1 failed · 2 errors · total 2.6s");
});

test("a submission's summary counts the level tallies", () => {
  const model = played(
    { type: "level_result", status: "fail", level: 1, total: 5, passed: 4, visible_total: 2, visible_passed: 2, hidden_total: 3, hidden_passed: 2 },
    { type: "run_end", outcome: "failed", exit_code: 1, message: null, summary: { duration_s: 1.4 } },
  );
  assert.equal(resultsView(model, false).summary?.text, "4/5 passed · 1 failed · total 1.4s");
});

test("a passing concurrent run says a pass is not a proof", () => {
  const model = played(stressRun(0, "pass"), { type: "run_end", outcome: "passed", exit_code: 0, message: null, summary: { duration_s: 1 } });
  assert.deepEqual(resultsView(model, false).summary?.notes, ["stress runs found no race (not a proof of thread safety)"]);
});

test("an interrupted run says so", () => {
  const model = played({ type: "run_end", outcome: "interrupted", exit_code: 130, message: null, summary: null });
  assert.deepEqual(resultsView(model, false).summary, { tone: "warn", text: "interrupted", notes: [] });
});

test("a run that stopped with an error gives its message", () => {
  const model = played({ type: "run_end", outcome: "error", exit_code: 4, message: "pytest is missing", summary: null });
  assert.deepEqual(resultsView(model, false).summary, { tone: "fail", text: "error: pytest is missing", notes: [] });
});

test("code that did not load gives its error", () => {
  const model = played({
    type: "run_end",
    outcome: "load_failed",
    exit_code: 2,
    message: null,
    summary: { duration_s: 0.3, load_error: { type: "SyntaxError", message: "invalid syntax" } },
  });
  assert.deepEqual(resultsView(model, false).summary, { tone: "fail", text: "LOAD FAILED", notes: ["SyntaxError: invalid syntax"] });
});

test("a child that ended without run_end shows its exit and its last error lines", () => {
  const model = new RunModel();
  model.close({ exit_code: 3, signal: null, stderr: ["error: level 3 is locked"] });
  assert.deepEqual(resultsView(model, false).summary, { tone: "fail", text: "cstudy exited 3", notes: ["error: level 3 is locked"] });
});

test("a child a signal ended names the signal", () => {
  const model = played();
  model.close({ exit_code: 137, signal: "SIGKILL", stderr: [] });
  assert.equal(resultsView(model, false).summary?.text, "cstudy was stopped by SIGKILL");
});

// progress and the rest

test("progress counts results against the plan", () => {
  assert.deepEqual(resultsView(played(result("ex1"), result("ex2")), false).progress, { done: 2, planned: 16 });
});

test("a project run's progress has no plan", () => {
  const model = new RunModel();
  model.apply(start({ kind: "project", planned: null }));
  assert.equal(resultsView(model, false).progress.planned, null);
});

test("diagnostics are kept in order", () => {
  const model = played(
    { type: "diagnostic", source: "load", severity: "error", file: "bank/bank.py", line: 3, column: null, code: "SyntaxError", message: "invalid syntax" },
  );
  assert.deepEqual(model.diagnostics.map((found) => found.line), [3]);
});

test("the latest output notice is the run's status line", () => {
  const model = played({ type: "output", text: "computing expected values" });
  assert.equal(resultsView(model, false).notice, "computing expected values");
});

test("the notice clears once results come", () => {
  const model = played({ type: "output", text: "computing expected values" }, result("ex1"));
  assert.equal(resultsView(model, false).notice, null);
});

// a project's stress cases in a submission

function submission(...events: RunEvent[]): RunModel {
  const model = new RunModel();
  const submitting = start({ command: "submit", kind: "project", planned: null, levels: { up_to: 2, unlocked: 2, last: 2 } });
  for (const event of [submitting, ...events]) model.apply(event);
  return model;
}

function leveledRun(id: string, level: number, run: number): RunEvent {
  return { type: "stress_run", id, variant: "thread", run, seed: 1000 + run, status: "pass", duration_ns: 1, reasons: [], level };
}

test("a project's stress case keeps its level", () => {
  const model = submission({ type: "stress_run_start", id: "s1", variant: "thread", run: 0, seed: 1000, level: 2 });
  assert.deepEqual(shown(model), ["stress s1 thread running level 2"]);
});

test("a submission draws each stress case inside its level's group", () => {
  const model = submission(
    result("ex1", { visible: true, level: 1 }),
    result("ex2", { visible: true, level: 2 }),
    result("h2", { level: 2, status: "fail" }),
    leveledRun("s1", 2, 0),
    result("h1", { level: 1, status: "fail" }),
  );
  assert.deepEqual(shown(model), ["pass ex1", "fail h1", "pass ex2", "fail h2", "stress s1 thread pass level 2"]);
});

test("a submission without stress cases keeps its rows in run order", () => {
  const model = submission(result("ex1", { visible: true, level: 1 }), result("ex2", { visible: true, level: 2 }), result("h1", { level: 1, status: "fail" }));
  assert.deepEqual(shown(model), ["pass ex1", "pass ex2", "fail h1"]);
});
