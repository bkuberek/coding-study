import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { beforeEach, test } from "node:test";

import { requestsTo, resetMocks } from "./mockControl.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const secret = "starter-secret-0123456789";

function post(path: string, body: unknown): Promise<Response> {
  return fetch(`${app}${path}`, {
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

test("a valid endpoint is registered as given", async () => {
  const url = "https://starter-1.shop.test/events";

  const response = await post("/endpoints", { id: "starter-1", url, secret });

  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), {
    id: "starter-1",
    url,
    status: "active",
    consecutive_failures: 0,
  });
});

test("a delivery reaches the customer's server, signed with the endpoint's secret", async () => {
  const event = { id: "evt_1", type: "invoice.paid" };
  const body = JSON.stringify(event);
  await post("/endpoints", { id: "starter-2", url: "https://starter-2.shop.test/events", secret });

  const response = await post("/deliveries", { endpoints: ["starter-2"], event });

  assert.equal(response.status, 200);
  const [received] = await requestsTo("customer-hooks");
  assert.equal(received?.body, body);
  assert.equal(
    received?.headers["x-webhook-signature"],
    `sha256=${createHmac("sha256", secret).update(body).digest("hex")}`,
  );
});

test("a URL whose scheme is not http or https is refused", async () => {
  const url = "ftp://starter-3.shop.test/events";

  const response = await post("/endpoints", { id: "starter-3", url, secret });

  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: "invalid_url" });
});
