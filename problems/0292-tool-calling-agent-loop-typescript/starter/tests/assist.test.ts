import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { requestsTo, resetMocks } from "./mockControl.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;

function ask(body: unknown): Promise<Response> {
  return fetch(`${app}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

beforeEach(resetMocks);

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a request without a known role is refused", async () => {
  const response = await ask({ role: "visitor", question: "Where is order A-1042?" });

  assert.equal(response.status, 400);
});

test("a question about an order is answered from the order", async () => {
  const response = await ask({
    role: "support",
    question: "Where is order A-1042? The customer says it hasn't arrived yet.",
  });

  assert.equal(response.status, 200);
  const result = (await response.json()) as { answer: string };
  assert.match(result.answer, /PX-55102/);
  assert.equal((await requestsTo("orders")).length, 1);
});
