import assert from "node:assert/strict";
import { test } from "node:test";

import { MalformedEvent, uploadIn } from "../src/events.ts";
import { linesOf } from "../src/lines.ts";
import { checked } from "../src/rows.ts";

async function lines(...chunks: string[]): Promise<string[]> {
  const encoder = new TextEncoder();
  async function* bytes() {
    for (const chunk of chunks) {
      yield encoder.encode(chunk);
    }
  }
  const found: string[] = [];
  for await (const line of linesOf(bytes())) {
    found.push(line);
  }
  return found;
}

function event(eventName: string, key: string): string {
  return JSON.stringify({
    Records: [
      {
        eventName,
        s3: { bucket: { name: "uploads" }, object: { key, sequencer: "0A1" } },
      },
    ],
  });
}

test("a line split across two chunks comes out whole", async () => {
  assert.deepEqual(await lines("sku,desc", "ription\nA,b,1\n"), ["sku,description", "A,b,1"]);
});

test("a final line break starts no line, but an empty line before it is one", async () => {
  assert.deepEqual(await lines("a\n\n"), ["a", ""]);
});

test("Windows line endings and a byte order mark are not part of any line", async () => {
  assert.deepEqual(await lines("﻿sku\r\nA\r\n"), ["sku", "A"]);
});

test("a character whose bytes two chunks split is decoded once", async () => {
  const bytes = new TextEncoder().encode("é\n");
  async function* split() {
    yield bytes.slice(0, 1);
    yield bytes.slice(1);
  }
  const found: string[] = [];
  for await (const line of linesOf(split())) {
    found.push(line);
  }

  assert.deepEqual(found, ["é"]);
});

test("a row breaks only the first rule it breaks", () => {
  assert.equal(checked("bolt,,0"), "invalid_sku");
});

test("a quantity must be a whole number from 1 to 100000", () => {
  assert.deepEqual(
    ["0", "100001", "+5", "1.0", "007", "100000"].map((quantity) => checked(`A,b,${quantity}`)),
    [
      "invalid_quantity",
      "invalid_quantity",
      "invalid_quantity",
      "invalid_quantity",
      "invalid_quantity",
      { sku: "A", description: "b", quantity: 100000 },
    ],
  );
});

test("a description runs from 1 to 300 characters", () => {
  assert.deepEqual(
    [0, 300, 301].map((length) => checked(`A,${"d".repeat(length)},1`)),
    ["invalid_description", { sku: "A", description: "d".repeat(300), quantity: 1 }, "invalid_description"],
  );
});

test("an event's key is decoded as S3 encodes it", () => {
  assert.equal(uploadIn(event("ObjectCreated:Put", "in/north+depot/a%2Bb.csv"))?.key, "in/north depot/a+b.csv");
});

test("events that are not a finished upload hold nothing to load", () => {
  assert.deepEqual(
    [
      JSON.stringify({ Service: "Amazon S3", Event: "s3:TestEvent" }),
      event("ObjectRemoved:Delete", "in/a.csv"),
      event("ObjectCreated:Put", "in/a.csv.part"),
    ].map(uploadIn),
    [undefined, undefined, undefined],
  );
});

test("a body that is not an S3 event is malformed", () => {
  assert.throws(() => uploadIn("not json"), MalformedEvent);
});
