import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

function priceFor(client: string): Promise<Response> {
  return fetch(`${app}/prices/lamp`, { headers: { "X-Api-Key": client } });
}

test("a client's sixth request within a second waits a second", async () => {
  const client = `limits-${randomUUID().slice(0, 8)}`;
  for (let sent = 0; sent < 5; sent += 1) {
    await priceFor(client);
  }

  const refused = await priceFor(client);

  assert.equal(refused.headers.get("retry-after"), "1");
});

test("a burst of ten lets five through", async () => {
  const client = `limits-${randomUUID().slice(0, 8)}`;

  const answers = await Promise.all(Array.from({ length: 10 }, () => priceFor(client)));

  assert.equal(answers.filter((answer) => answer.status === 200).length, 5);
});

test("a key with a space in it is no key", async () => {
  const response = await priceFor("my key");

  assert.equal(response.status, 401);
});
