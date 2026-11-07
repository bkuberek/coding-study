// How the scripted vendor behaves, on the virtual clock.

import assert from "node:assert/strict";
import { test } from "node:test";

import { ScriptedJitter } from "../src/timing/jitter.ts";
import { ConnectionReset, ScriptedVendor } from "../src/vendor/scriptedVendor.ts";
import { virtualClock } from "./virtual-clock.ts";

const GET = { method: "GET", path: "/rates", idempotencyKey: "" };

test("a step answers after its latency, with any Retry-After as text", async (t) => {
  const clock = virtualClock(t);
  const vendor = new ScriptedVendor();
  vendor.script(["429 30 retry-after=2"]);
  assert.deepEqual(await clock.wait(vendor.send(GET)), { status: 429, retryAfter: "2" });
  assert.equal(clock.now(), 30);
});

test("the log has when each attempt started, and any key", async (t) => {
  const clock = virtualClock(t);
  const vendor = new ScriptedVendor();
  await clock.wait(vendor.send(GET));
  await clock.wait(vendor.send({ method: "POST", path: "/orders", idempotencyKey: "k1" }));
  assert.deepEqual(vendor.attemptLog(), ["0 GET /rates", "10 POST /orders key=k1"]);
});

test("a reset rejects after its latency", async (t) => {
  const clock = virtualClock(t);
  const vendor = new ScriptedVendor();
  vendor.script(["reset 5"]);
  await assert.rejects(clock.wait(vendor.send(GET)), ConnectionReset);
  assert.equal(clock.now(), 5);
});

test("a jitter source gives what was scripted, then 1", () => {
  const jitter = new ScriptedJitter();
  jitter.script([0.25]);
  assert.equal(jitter.next(), 0.25);
  assert.equal(jitter.next(), 1);
});
