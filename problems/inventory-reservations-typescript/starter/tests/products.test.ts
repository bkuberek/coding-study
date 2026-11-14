import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a product shows the stock the baseline gives it", async () => {
  const response = await fetch(`${app}/products/chair`);

  assert.deepEqual(await response.json(), { sku: "chair", name: "Office chair", available: 40 });
});

test("a product nobody sells is unknown", async () => {
  const response = await fetch(`${app}/products/sofa`);

  assert.equal(response.status, 404);
});
