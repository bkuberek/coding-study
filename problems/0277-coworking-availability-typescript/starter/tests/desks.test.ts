import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a day on sale answers its count", async () => {
  const response = await fetch(`${app}/desks?date=2027-03-01`);

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { date: "2027-03-01", available: 12 });
});

test("no date is a bad request", async () => {
  const response = await fetch(`${app}/desks`);

  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: "date is required" });
});
