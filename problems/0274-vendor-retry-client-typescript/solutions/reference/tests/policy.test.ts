// The table of verdicts, without a clock.

import assert from "node:assert/strict";
import { test } from "node:test";

import { backoffDelay, retryAfterDelay, verdictOf } from "../src/retry/policy.ts";
import type { AttemptResult } from "../src/retry/policy.ts";

const answer = (status: number, retryAfter: string | null = null): AttemptResult => ({
  kind: "answer",
  status,
  retryAfter,
});
const GET = { method: "GET", path: "/rates", idempotencyKey: "" };
const POST = { method: "POST", path: "/orders", idempotencyKey: "" };
const KEYED = { method: "POST", path: "/orders", idempotencyKey: "k1" };

test("a repeatable request retries a server failure, and a bare POST cannot know", () => {
  assert.equal(verdictOf(answer(503), GET), "retry");
  assert.equal(verdictOf(answer(503), KEYED), "retry");
  assert.equal(verdictOf(answer(503), POST), "unknown");
});

test("a 429 and a reset never did the work, so anything may retry them", () => {
  assert.equal(verdictOf(answer(429), POST), "retry");
  assert.equal(verdictOf({ kind: "reset", status: null, retryAfter: null }, POST), "retry");
});

test("anything else is final", () => {
  assert.equal(verdictOf(answer(404), GET), "rejected");
  assert.equal(verdictOf(answer(501), GET), "rejected");
  assert.equal(verdictOf(answer(204), POST), "ok");
});

test("the backoff doubles, caps, then takes its fraction", () => {
  assert.equal(backoffDelay(1, 1), 100);
  assert.equal(backoffDelay(4, 1), 800);
  assert.equal(backoffDelay(5, 1), 1000);
  assert.equal(backoffDelay(5, 0.5), 500);
  assert.equal(backoffDelay(1, 0.999), 99);
});

test("Retry-After counts seconds, on a 429 or a 503, and only as a whole number", () => {
  assert.equal(retryAfterDelay(answer(429, "2")), 2000);
  assert.equal(retryAfterDelay(answer(503, "0")), 0);
  assert.equal(retryAfterDelay(answer(404, "2")), null);
  assert.equal(retryAfterDelay(answer(429, "-1")), null);
  assert.equal(retryAfterDelay(answer(429, "1.5")), null);
  assert.equal(retryAfterDelay(answer(429, "soon")), null);
});
