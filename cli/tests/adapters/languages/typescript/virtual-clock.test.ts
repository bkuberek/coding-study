// The virtual clock of runners/typescript/lib/virtual-clock.ts, run by
// test_typescript_virtual_clock.py with `node --test`, as a project's tests run it.

import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { setTimeout as sleepImported } from "node:timers/promises";

import {
  DeadlockError,
  startClock,
  virtualClock,
} from "../../../../../runners/typescript/lib/virtual-clock.ts";

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

test("the clock starts at zero", (t) => {
  assert.equal(virtualClock(t).now(), 0);
});

test("a chain of sleeps sees each sleep's own time", async (t) => {
  const clock = virtualClock(t);
  const stamps: number[] = [];
  const chain = async (): Promise<void> => {
    for (let step = 0; step < 3; step++) {
      await sleep(10);
      stamps.push(Date.now());
    }
  };
  const done = chain();
  await clock.advance(30);
  await clock.wait(done);
  assert.deepEqual(stamps, [10, 20, 30]);
});

test("a static import of timers/promises is on the clock", async (t) => {
  const clock = virtualClock(t);
  const started = performance.now();
  await clock.wait(sleepImported(3_600_000));
  assert.equal(clock.now(), 3_600_000);
  assert.ok(performance.now() - started < 1000);
});

test("advance fires each timer due on the way at its own time", async (t) => {
  const clock = virtualClock(t);
  const log: string[] = [];
  setTimeout(() => log.push(`late@${Date.now()}`), 30);
  setTimeout(() => log.push(`early@${Date.now()}`), 10);
  await clock.advance(20);
  log.push(`advanced@${clock.now()}`);
  await clock.advance(20);
  assert.deepEqual(log, ["early@10", "advanced@20", "late@30"]);
});

test("an interval fires at each of its times", async (t) => {
  const clock = virtualClock(t);
  const ticks: number[] = [];
  const id = setInterval(() => ticks.push(Date.now()), 15);
  await clock.advance(50);
  clearInterval(id);
  assert.deepEqual(ticks, [15, 30, 45]);
});

test("a cleared timer neither fires nor keeps the clock waiting", async (t) => {
  const clock = virtualClock(t);
  const fired: string[] = [];
  clearTimeout(setTimeout(() => fired.push("cleared"), 5));
  await assert.rejects(clock.wait(new Promise(() => {})), DeadlockError);
  assert.deepEqual([fired, clock.now()], [[], 0]);
});

test("wait moves the clock until the promise settles", async (t) => {
  const clock = virtualClock(t);
  const answer = async (): Promise<string> => {
    await sleep(250);
    return `answered@${Date.now()}`;
  };
  assert.equal(await clock.wait(answer()), "answered@250");
});

test("wait rethrows what the promise rejects with", async (t) => {
  const clock = virtualClock(t);
  const fails = async (): Promise<never> => {
    await sleep(5);
    throw new Error("failed late");
  };
  await assert.rejects(clock.wait(fails()), /failed late/);
});

test("a wait that nothing can end is a deadlock at the virtual time", async (t) => {
  const clock = virtualClock(t);
  await clock.advance(2000);
  const error = await clock.wait(new Promise(() => {})).catch((e) => e);
  assert.ok(error instanceof DeadlockError);
  assert.equal(error.milliseconds, 2000);
  assert.equal(
    error.message,
    "deadlock: every task waits and no timer is due, at 2000 ms",
  );
});

test("settle lets promise continuations run without moving the clock", async (t) => {
  const clock = virtualClock(t);
  const log: string[] = [];
  void Promise.resolve().then(() => log.push("continued"));
  await clock.settle();
  assert.deepEqual([log, clock.now()], [["continued"], 0]);
});

test("timers due at the same instant fire in the order they were set", async (t) => {
  const clock = virtualClock(t);
  const order: string[] = [];
  for (const name of "abcd") {
    setTimeout(() => order.push(name), 10);
  }
  await clock.advance(10);
  assert.equal(order.join(""), "abcd");
});

test("a clock started and stopped again restores the real timers", async () => {
  const real = globalThis.setTimeout;
  for (let round = 0; round < 3; round++) {
    const clock = startClock(mock.timers);
    assert.notEqual(globalThis.setTimeout, real);
    await clock.advance(5);
    assert.equal(clock.now(), 5);
    clock.stop();
  }
  assert.equal(globalThis.setTimeout, real);
  assert.ok(Date.now() > 1_000_000_000_000);
});

test("a thousand instants take little real time", async (t) => {
  const clock = virtualClock(t);
  let ticks = 0;
  const id = setInterval(() => {
    ticks++;
  }, 10);
  const started = performance.now();
  await clock.advance(10_000);
  clearInterval(id);
  assert.equal(ticks, 1000);
  assert.ok(performance.now() - started < 2000);
});
