import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { resetEngine, setScenario } from "./pricingScenario.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const client = { "X-Api-Key": "my-tests" };

beforeEach(resetEngine);

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a price comes from the engine", async () => {
  const response = await fetch(`${app}/prices/desk`, { headers: client });

  assert.deepEqual(await response.json(), { sku: "desk", amount_cents: 18900, currency: "EUR" });
});

test("a product the engine does not know is unknown", async () => {
  const response = await fetch(`${app}/prices/sofa`, { headers: client });

  assert.equal(response.status, 404);
});

test("an engine that is down is a bad gateway", async () => {
  await setScenario("outage");

  const response = await fetch(`${app}/prices/mug`, { headers: client });

  assert.equal(response.status, 502);
});
