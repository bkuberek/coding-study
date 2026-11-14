// The relay on its own, with a publisher that fails on cue.

import assert from "node:assert/strict";
import { test } from "node:test";

import { FakeBroker } from "../src/adapters/fakeBroker.ts";
import { MemoryDatabase, MemoryOutbox } from "../src/adapters/memoryDatabase.ts";
import { Relay } from "../src/core/relay.ts";

function pending(aggregateIds: string[]) {
  const database = new MemoryDatabase();
  const outbox = new MemoryOutbox(database);
  const broker = new FakeBroker();
  aggregateIds.forEach((aggregateId, index) => {
    outbox.append({ aggregateId, sequence: index + 1, type: "rental.reserved", state: "reserved" });
  });
  return { broker, relay: new Relay(database, outbox, broker), outbox };
}

test("a failed rental waits and another rental overtakes it", () => {
  const { broker, relay } = pending(["R-1", "R-1", "R-2"]);
  broker.refuseNext("R-1", 1);
  assert.equal(relay.run(10), 1);
  assert.deepEqual(broker.log().map((event) => event.id), ["evt-3"]);
  assert.equal(relay.run(10), 2);
  assert.deepEqual(broker.log().map((event) => event.id), ["evt-3", "evt-1", "evt-2"]);
});

test("rows held back take no attempt", () => {
  const { broker, relay } = pending(["R-1", "R-1", "R-1", "R-2"]);
  broker.refuseNext("R-1", 1);
  assert.equal(relay.run(2), 1);
  assert.deepEqual(broker.log().map((event) => event.id), ["evt-4"]);
});
