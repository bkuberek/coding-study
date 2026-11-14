import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("an enqueued job waits in its queue", async () => {
  const response = await fetch(`${app}/queues/test-reports/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "test-waits", tenant: "acme", payload: { report: "sales" } }),
  });
  const job = (await response.json()) as { status: string };

  assert.equal(job.status, "queued");
});

test("a job the first version enqueued is still there", async () => {
  const response = await fetch(`${app}/jobs/inv-1001`);

  assert.equal(response.status, 200);
});
