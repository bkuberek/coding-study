import assert from "node:assert/strict";
import { test } from "node:test";

import { deliver, orderView } from "./provider.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a signed event moves its order", async () => {
  const body = JSON.stringify({
    id: "evt_t1",
    type: "payment.succeeded",
    order: "ord_t1",
    sequence: 1,
    amount: 1200,
    currency: "EUR",
    created: 1803902000,
  });

  const response = await deliver(body);

  assert.equal(response.status, 200);
  assert.deepEqual(await (await orderView("ord_t1")).json(), {
    order: "ord_t1",
    state: "succeeded",
    sequence: 1,
  });
});

test("a delivery the provider did not sign is refused", async () => {
  const body = JSON.stringify({
    id: "evt_t2",
    type: "payment.succeeded",
    order: "ord_t2",
    sequence: 1,
    amount: 1200,
    currency: "EUR",
    created: 1803902000,
  });

  const response = await deliver(body, { signature: "0".repeat(64) });

  assert.equal(response.status, 401);
});
