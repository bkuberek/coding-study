// Tests of the pieces the worker relies on.

import assert from "node:assert/strict";
import { test } from "node:test";

import { Extractor, ExtractionFailed } from "../src/extraction/extractor.ts";
import { Faults } from "../src/runtime/faults.ts";
import { Database } from "../src/storage/database.ts";
import { parseDelivery, MalformedDelivery } from "../src/worker/delivery.ts";

test("a transaction that throws leaves nothing behind", () => {
  const database = new Database(new Faults());
  assert.throws(() =>
    database.transaction((tables) => {
      tables.ledger.push({ documentId: "D-1", pipelineVersion: 1, pages: 1 });
      throw new Error("no");
    }),
  );
  assert.equal(
    database.read((tables) => tables.ledger.length),
    0,
  );
});

test("an extraction counts pages and words", () => {
  const extractor = new Extractor(new Faults());
  assert.deepEqual(extractor.extract("Invoice 7|Total  due"), { pages: 2, words: 4 });
});

test("a scan with a corrupt header cannot be read", () => {
  const extractor = new Extractor(new Faults());
  assert.throws(() => extractor.extract("%%Invoice 7"), ExtractionFailed);
});

test("a delivery with a text revision is malformed", () => {
  const text = JSON.stringify({
    messageId: "m-1",
    documentId: "D-1",
    revision: "1",
    pipelineVersion: 1,
    body: "Invoice 7",
    deliveryCount: 1,
  });
  assert.throws(() => parseDelivery(text), MalformedDelivery);
});
