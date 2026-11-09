import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { NOW, deliver, orderView, resetProvider, setScenario } from "./provider.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;

afterEach(resetProvider);

function eventBody(order: string, sequence: number, type: string): string {
  return JSON.stringify({
    id: `evt_${order}_${sequence}`,
    type,
    order,
    sequence,
    amount: 1200,
    currency: "EUR",
    created: NOW - 100,
  });
}

async function stateOf(order: string): Promise<unknown> {
  return (await orderView(order)).json();
}

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a signed event moves its order", async () => {
  const response = await deliver(eventBody("ord_t1", 1, "payment.succeeded"));

  assert.equal(response.status, 200);
  assert.deepEqual(await stateOf("ord_t1"), { order: "ord_t1", state: "succeeded", sequence: 1 });
});

test("a delivery the provider did not sign is refused", async () => {
  const body = eventBody("ord_t2", 1, "payment.succeeded");

  const response = await deliver(body, { signature: "0".repeat(64) });

  assert.equal(response.status, 401);
});

test("the provider's retry is a duplicate", async () => {
  const body = eventBody("ord_t3", 1, "payment.succeeded");
  await deliver(body, { timestamp: NOW - 60 });

  const response = await deliver(body);

  assert.deepEqual(await response.json(), { outcome: "duplicate" });
});

test("a refund that arrives first is applied after the payment the provider supplies", async () => {
  const response = await deliver(eventBody("ord_9001", 2, "payment.refunded"));

  assert.equal(response.status, 200);
  assert.deepEqual(await stateOf("ord_9001"), { order: "ord_9001", state: "refunded", sequence: 2 });
});

test("a gap the provider cannot fill is answered 503, for it to deliver again", async () => {
  await setScenario("outage");

  const response = await deliver(eventBody("ord_t4", 2, "payment.refunded"));

  assert.equal(response.status, 503);
  assert.equal((await orderView("ord_t4")).status, 404);
});
