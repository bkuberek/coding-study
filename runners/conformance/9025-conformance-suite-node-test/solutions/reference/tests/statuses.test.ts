// One test per outcome of a suite job, in the order the runner meets them: a pass, a hang that
// the hang guard ends, an assertion failure, an exit that ends the runner, an exception and output.
// After each hang or exit the suite restarts with the tests reported so far left out.

import assert from "node:assert/strict";
import { test } from "node:test";

import { Probe } from "../src/probe.ts";

test("passes", () => {
  assert.equal(new Probe().ping(), "pong");
});

test("hangs", () => {
  while (true) {}
});

test("fails an assertion", () => {
  assert.equal(new Probe().ping(), "ping");
});

test("ends the process", () => {
  // The runner turns process.exit into an error; a signal ends the process for certain.
  process.kill(process.pid, "SIGKILL");
});

test("raises", () => {
  throw new Error("conformance failure");
});

test("prints", () => {
  console.log("conformance output");
});
