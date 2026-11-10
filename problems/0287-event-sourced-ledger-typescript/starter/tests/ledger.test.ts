import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("an account's events come from the store in version order", async () => {
  const response = await fetch(`${app}/accounts/ben/events`);
  const listed = (await response.json()) as { version: number }[];

  assert.deepEqual(
    listed.map((event) => event.version),
    [1, 2],
  );
});

test("an account with no events is unknown", async () => {
  const response = await fetch(`${app}/accounts/nobody/events`);

  assert.equal(response.status, 404);
});
