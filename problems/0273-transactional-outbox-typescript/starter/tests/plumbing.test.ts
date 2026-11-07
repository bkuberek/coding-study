// Tests of the pieces the desk relies on.

import assert from "node:assert/strict";
import { test } from "node:test";

import { FakeBroker } from "../src/adapters/fakeBroker.ts";
import { PublishFailed } from "../src/core/ports.ts";
import { nextState } from "../src/core/rental.ts";

const EVENT = { id: "evt-1", aggregateId: "R-1", sequence: 1, type: "rental.reserved", state: "reserved" };

test("a rental moves only along the table", () => {
  assert.equal(nextState("reserve", null), "reserved");
  assert.equal(nextState("pickup", "reserved"), "out");
  assert.equal(nextState("pickup", "out"), null);
  assert.equal(nextState("constructor", null), null);
});

test("a refused message is not delivered", () => {
  const broker = new FakeBroker();
  broker.refuseNext("R-1", 1);
  assert.throws(() => broker.publish(EVENT), PublishFailed);
  assert.deepEqual(broker.log(), []);
});

test("a lost confirmation looks like a refusal, and the message was delivered", () => {
  const broker = new FakeBroker();
  broker.loseNextAck("R-1");
  assert.throws(() => broker.publish(EVENT), PublishFailed);
  assert.deepEqual(broker.log(), [EVENT]);
});
