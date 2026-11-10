import assert from "node:assert/strict";
import { test } from "node:test";

import { closeOutcome, RECONNECT_DELAYS_MS, retryDelay } from "../src/page/intelligence-state.ts";

test("the page's own close ends the session without a status", () => {
  assert.deepEqual(closeOutcome(1000, ""), { kind: "gone" });
});

test("cstudy serve stopping stops the session with no reason", () => {
  assert.deepEqual(closeOutcome(1001, "cstudy serve is stopping"), { kind: "stopped", why: "", reason: "cstudy serve is stopping" });
});

test("a binary message, a bad CSRF message and a message over 4 MiB stop the session", () => {
  for (const code of [1003, 1008, 1009]) assert.equal(closeOutcome(code, "x").kind, "stopped");
});

test("a server that exited says its exit code, not its last line", () => {
  assert.deepEqual(closeOutcome(4002, "exit 1: Error: Cannot find module 'x'"), {
    kind: "stopped",
    why: "exit 1",
    reason: "exit 1: Error: Cannot find module 'x'",
  });
});

test("a server that could not start says so", () => {
  assert.equal((closeOutcome(4002, "cannot start: node not found") as { why: string }).why, "cannot start");
});

test("a server that wrote output that is not LSP says so", () => {
  assert.equal((closeOutcome(4002, "bad output: a message without Content-Length") as { why: string }).why, "bad output");
});

test("a server that stopped reading its input says it is stuck", () => {
  const reason = "stuck: the server does not read its input";
  assert.deepEqual(closeOutcome(4002, reason), { kind: "stopped", why: "stuck", reason });
});

test("a message of the server over 4 MiB says it is bad output", () => {
  assert.equal((closeOutcome(4002, "bad output: a message over 4 MiB") as { why: string }).why, "bad output");
});

test("a page that read none of the server's messages is stopped with no cause", () => {
  const reason = "the page does not read the server's messages";
  assert.deepEqual(closeOutcome(1008, reason), { kind: "stopped", why: "", reason });
});

test("a fifth server says how many run", () => {
  const reason = "at most 4 code intelligence sessions run at once; close one in another tab";
  assert.deepEqual(closeOutcome(4003, reason), { kind: "stopped", why: "4 sessions running", reason });
});

test("Docker that does not answer waits for it calmly, with the reason as its cause", () => {
  assert.deepEqual(closeOutcome(4004, "Docker is not running"), { kind: "needs-docker", why: "Docker is not running", reason: "Docker is not running" });
});

test("a sidecar image that is not here says the image is needed", () => {
  const reason = "needs the node image: docker pull node:24-slim@sha256:01d5";
  assert.deepEqual(closeOutcome(4004, reason), { kind: "needs-docker", why: "needs the node image", reason });
});

test("a dropped connection and a refused handshake are tried again", () => {
  assert.deepEqual(closeOutcome(1006, ""), { kind: "retry" });
});

test("any other code is tried again", () => {
  assert.deepEqual(closeOutcome(1011, "oops"), { kind: "retry" });
});

test("the delays between tries are 1, 2 and 5 seconds", () => {
  assert.deepEqual(RECONNECT_DELAYS_MS, [1000, 2000, 5000]);
});

test("the fourth failure in a row gives up", () => {
  assert.deepEqual([0, 1, 2, 3].map(retryDelay), [1000, 2000, 5000, null]);
});
