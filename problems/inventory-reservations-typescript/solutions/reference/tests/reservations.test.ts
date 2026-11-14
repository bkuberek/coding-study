import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

type Item = { sku: string; quantity: number; warehouse?: string };

function reserve(order: string, items: Item[], holdSeconds?: number): Promise<Response> {
  return fetch(`${app}/reservations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order, items, hold_seconds: holdSeconds }),
  });
}

async function available(sku: string): Promise<number> {
  const response = await fetch(`${app}/products/${sku}`);
  const body = (await response.json()) as { available: number };
  return body.available;
}

test("a reservation holds stock and a release gives it back", async () => {
  const before = await available("mug");

  await reserve("test-mugs", [{ sku: "mug", quantity: 2 }]);
  const held = await available("mug");
  await fetch(`${app}/reservations/test-mugs`, { method: "DELETE" });

  assert.deepEqual([held, await available("mug")], [before - 2, before]);
});

test("checkouts at once never take more than is left", async () => {
  const left = await available("lamp");

  const answers = await Promise.all(
    Array.from({ length: 10 }, (_, index) =>
      reserve(`test-lamp-${index}`, [{ sku: "lamp", quantity: 1 }]),
    ),
  );

  assert.equal(answers.filter((answer) => answer.status === 201).length, left);
});

test("a hold that ran out gives its stock back", async () => {
  const before = await available("chair");

  await reserve("test-gone", [{ sku: "chair", quantity: 3 }], 0);

  assert.equal(await available("chair"), before);
});
