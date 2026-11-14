import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

function as(key: string): RequestInit {
  return { headers: { Authorization: `Bearer ${key}` } };
}

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a request without a key is refused", async () => {
  const response = await fetch(`${app}/projects`);

  assert.equal(response.status, 401);
});

test("a key nobody holds is refused", async () => {
  const response = await fetch(`${app}/projects`, as("key-nobody"));

  assert.equal(response.status, 401);
});

test("a key the baseline seeds lists projects", async () => {
  const response = await fetch(`${app}/projects`, as("key-ada"));

  assert.equal(response.status, 200);
});
