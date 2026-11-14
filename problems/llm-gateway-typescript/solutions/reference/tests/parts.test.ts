import assert from "node:assert/strict";
import { test } from "node:test";

import { TeamLedger } from "../src/ledger.ts";
import { waitBeforeRetry } from "../src/primary.ts";
import { parseEvent, serverSentEvents } from "../src/sse.ts";

function bodyOf(...reads: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const read of reads) {
        controller.enqueue(encoder.encode(read));
      }
      controller.close();
    },
  });
}

async function eventsOf(body: ReadableStream<Uint8Array>): Promise<string[]> {
  const found: string[] = [];
  for await (const { event, data } of serverSentEvents(body)) {
    found.push(`${event}:${data}`);
  }
  return found;
}

test("a 429 waits as long as it says, up to 2 s", () => {
  assert.equal(waitBeforeRetry(429, "2"), 2000);
  assert.equal(waitBeforeRetry(429, "3"), null);
});

test("a 429 with no Retry-After waits half a second", () => {
  assert.equal(waitBeforeRetry(429, null), 500);
});

test("a 5xx is not asked again", () => {
  assert.equal(waitBeforeRetry(503, null), null);
});

test("an event's name and its data lines", () => {
  assert.deepEqual(parseEvent("event: usage\ndata: {\ndata: }"), { event: "usage", data: "{\n}" });
});

test("an event split across reads arrives whole, and two in one read arrive apart", async () => {
  const body = bodyOf("data: one\n", "\ndata: two\n\ndata: thr", "ee\n\n");

  assert.deepEqual(await eventsOf(body), ["message:one", "message:two", "message:three"]);
});

test("a budget caps the limit at what remains, and refuses when nothing does", () => {
  const ledger = new TeamLedger();
  ledger.setBudget("tests-cap", 20);
  ledger.record("tests-cap", "brisk-1", { prompt_tokens: 5, completion_tokens: 4 });

  assert.equal(ledger.limitFor("tests-cap", 256), 11);
  ledger.record("tests-cap", "brisk-1", { prompt_tokens: 9, completion_tokens: 4 });
  assert.equal(ledger.limitFor("tests-cap", 256), null);
});

test("each answer is priced by its own model", () => {
  const ledger = new TeamLedger();
  ledger.record("tests-cost", "brisk-1", { prompt_tokens: 5, completion_tokens: 4 });
  ledger.record("tests-cost", "steady-2", { prompt_tokens: 5, completion_tokens: 3 });

  assert.equal(ledger.usageOf("tests-cost").cost_micros, 34 + 60);
});
