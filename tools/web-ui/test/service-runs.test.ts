import assert from "node:assert/strict";
import { test } from "node:test";

import { RunModel, resultsView, stackText, type ViewItem } from "../src/page/results-model.ts";
import type { Output, RunEvent, RunStart, StackState, TestResult } from "../src/page/run-events.ts";
import { applicableOptions, DEFAULT_OPTIONS, runBody, runCommand, type RunContext, type RunOptionsState } from "../src/page/run-options.ts";

const ROOMS: RunContext = { slug: "rooms", kind: "project", language: "typescript", levels: { unlocked: 2, last: 3 }, oracle: false, typecheck: true, service: true };

function options(change: Partial<RunOptionsState>): RunOptionsState {
  return { ...DEFAULT_OPTIONS, ...change };
}

function start(): RunStart {
  return { type: "run_start", command: "test", slug: "rooms", language: "typescript", attempt_id: 1, mode: "new", levels: { up_to: 2, unlocked: 2, last: 3 }, kind: "project", planned: null };
}

function stack(state: StackState, startup_s?: number): Output {
  return { type: "output", text: `the stack: ${state}`, stack: state, ...(startup_s === undefined ? {} : { startup_s }) };
}

function commandTest(fields: Partial<TestResult> = {}): TestResult {
  return { type: "test_result", id: "commands.test", status: "pass", duration_ns: 400_000_000, origin: "starter", level: null, ...fields };
}

function played(...events: RunEvent[]): RunModel {
  const model = new RunModel();
  for (const event of [start(), ...events]) model.apply(event);
  return model;
}

function described(item: ViewItem): string {
  return item.kind === "file" ? `file ${item.path}` : item.kind;
}

// the run options

test("a service project's test takes no option", () => {
  assert.deepEqual([...applicableOptions(ROOMS)], ["level"]);
});

test("a service project's test sends no level, case or type check", () => {
  const body = runBody(1, "test", options({ level: 1, cases: ["v1"], typecheck: true }), ROOMS);
  assert.deepEqual(body, { attempt_id: 1, command: "test" });
});

test("a service project's submission takes its level", () => {
  assert.deepEqual(runBody(1, "submit", options({ level: 1 }), ROOMS), { attempt_id: 1, command: "submit", level: 1 });
});

test("a service project's test command has no flag, whatever the type check preference", () => {
  assert.equal(runCommand("test", DEFAULT_OPTIONS, ROOMS), "cstudy test rooms");
});

// the stack

test("the stack follows each stage a notice names", () => {
  const model = played(stack("starting"), stack("ready", 2.4));
  assert.equal(model.stack?.state, "ready");
});

test("ready keeps the startup, which nothing counts", () => {
  assert.equal(stackText(played(stack("starting"), stack("ready", 2.4)).stack!), "ready after 2.4 s, not counted");
});

test("a stack that went down after a run says so and keeps its startup", () => {
  const model = played(stack("ready", 2.4), stack("stopped"));
  assert.equal(stackText(model.stack!), "down · it was ready after 2.4 s, not counted");
});

test("a stack that failed stays failed once it is down", () => {
  const model = played(stack("starting"), stack("failed"), stack("stopped"));
  assert.deepEqual([model.stack?.state, stackText(model.stack!)], ["failed", "did not become ready · down"]);
});

test("a notice without a stage keeps the stack where it was", () => {
  const model = played(stack("pulling"), { type: "output", text: "pulled 40 MB" });
  assert.equal(model.stack?.state, "pulling");
});

test("a run that is not a service project's has no stack", () => {
  assert.equal(played({ type: "output", text: "warming Gradle daemon ..." }).stack, null);
});

// commands.test

test("commands.test is a row of its own, with no file heading", () => {
  assert.deepEqual(resultsView(played(commandTest()), false).items.map(described), ["test"]);
});
