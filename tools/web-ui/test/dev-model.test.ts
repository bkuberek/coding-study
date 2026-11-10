import assert from "node:assert/strict";
import { test } from "node:test";

import { DevModel, type DevEvent, MAX_APP_LINES } from "../src/page/dev-model.ts";

const MOCKS = [{ name: "room-vendor", scenarios: ["outage", "slow"] }];

function played(...events: DevEvent[]): DevModel {
  const model = new DevModel(MOCKS);
  for (const event of events) model.apply(event);
  return model;
}

const READY: DevEvent = { type: "dev_ready", app_url: "http://127.0.0.1:56223", startup_s: 2.4, mocks: [{ name: "room-vendor", scenario: null, scenarios: ["outage"] }] };

test("before a stack, each mock server holds no scenario and offers its visible ones", () => {
  const model = new DevModel(MOCKS);
  assert.deepEqual([model.phase, model.mocks], ["idle", [{ name: "room-vendor", scenario: null, scenarios: ["outage", "slow"] }]]);
});

test("a stack starts with its first notice", () => {
  assert.equal(played({ type: "output", text: "starting the stack", stack: "starting" }).phase, "starting");
});

test("ready names where the app answers and what each mock server holds", () => {
  const model = played(READY);
  assert.deepEqual([model.phase, model.appUrl, model.mocks[0]?.scenarios], ["ready", "http://127.0.0.1:56223", ["outage"]]);
});

test("a switch the stack made shows as the scenario the mock server holds", () => {
  const model = played(READY, { type: "scenario", mock: "room-vendor", scenario: "outage", message: null });
  assert.deepEqual([model.mocks[0]?.scenario, model.refusal], ["outage", null]);
});

test("a refused switch keeps the scenario and says why", () => {
  const model = played(READY, { type: "scenario", mock: "room-vendor", scenario: null, message: "room-vendor has no visible scenario slow" });
  assert.deepEqual([model.mocks[0]?.scenario, model.refusal], [null, "room-vendor has no visible scenario slow"]);
});

test("the app's lines are kept, the newest last, up to a bound", () => {
  const lines = Array.from({ length: MAX_APP_LINES + 5 }, (_, index): DevEvent => ({ type: "app", text: `line ${index}` }));
  const model = played(READY, ...lines);
  assert.deepEqual([model.lines.length, model.lines.at(-1)], [MAX_APP_LINES, `line ${MAX_APP_LINES + 4}`]);
});

test("the end says how the stack ended and leaves no app url", () => {
  const model = played(READY, { type: "dev_end", outcome: "stopped", exit_code: 0, message: "the stack is down and its data is kept" });
  assert.deepEqual([model.phase, model.appUrl, model.end?.message], ["ended", null, "the stack is down and its data is kept"]);
});

test("an app that would not start keeps its output", () => {
  const model = played({ type: "dev_end", outcome: "load_failed", exit_code: 2, message: "your app exited", output: "boom" });
  assert.equal(model.end?.output, "boom");
});

test("a child that ended without its end says what standard error held", () => {
  const model = new DevModel(MOCKS);
  model.close({ exit_code: 3, signal: null, stderr: ["error: cstudy dev rooms is already running in process 41; stop it first"] });
  assert.equal(model.end?.message, "error: cstudy dev rooms is already running in process 41; stop it first");
});
