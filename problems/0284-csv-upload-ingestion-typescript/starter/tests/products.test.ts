import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a product no delivery brought is unknown", async () => {
  const response = await fetch(`${app}/products/NEVER-DELIVERED`);

  assert.equal(response.status, 404);
});
