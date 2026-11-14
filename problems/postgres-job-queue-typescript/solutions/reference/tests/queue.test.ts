import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

type Claimed = { id: string; attempt: number };

function post(path: string, body: object): Promise<Response> {
  return fetch(`${app}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function enqueue(queue: string, id: string, settings: object = {}): Promise<Response> {
  return post(`/queues/${queue}/jobs`, { id, tenant: "acme", payload: { report: id }, ...settings });
}

async function claimed(queue: string, visibilitySeconds?: number): Promise<Claimed> {
  const response = await post(`/queues/${queue}/claim`, { visibility_seconds: visibilitySeconds });
  return (await response.json()) as Claimed;
}

test("claims at once take each job once", async () => {
  for (const id of ["test-burst-1", "test-burst-2", "test-burst-3"]) {
    await enqueue("test-burst", id);
  }

  const answers = await Promise.all(
    Array.from({ length: 8 }, () => post("/queues/test-burst/claim", {})),
  );
  const taken = await Promise.all(
    answers.filter((answer) => answer.status === 200).map((answer) => answer.json()),
  );

  assert.deepEqual(taken.map((job) => (job as Claimed).id).sort(), [
    "test-burst-1",
    "test-burst-2",
    "test-burst-3",
  ]);
});

test("a complete from a claim that ran out is refused", async () => {
  await enqueue("test-late", "test-late-1");
  const first = await claimed("test-late", 0);
  await claimed("test-late");

  const late = await post(`/jobs/${first.id}/complete`, { attempt: first.attempt });

  assert.equal(late.status, 409);
});

test("a job that fails every attempt ends in the dead letters", async () => {
  await enqueue("test-dead", "test-dead-1", { max_attempts: 2, backoff_seconds: 0 });
  for (let tries = 0; tries < 2; tries += 1) {
    const job = await claimed("test-dead");
    await post(`/jobs/${job.id}/fail`, { attempt: job.attempt, error: "broken template" });
  }

  const response = await fetch(`${app}/queues/test-dead/dead-letters`);

  assert.deepEqual(await response.json(), [
    {
      id: "test-dead-1",
      tenant: "acme",
      payload: { report: "test-dead-1" },
      attempts: 2,
      error: "broken template",
    },
  ]);
});

test("a higher priority is claimed first", async () => {
  await enqueue("test-priority", "test-low", { priority: 1 });
  await enqueue("test-priority", "test-high", { priority: 9 });

  assert.equal((await claimed("test-priority")).id, "test-high");
});
