// A document is read as it is.

import assert from "node:assert/strict";
import { test } from "node:test";

import { parseDocument } from "../src/intake/document.ts";
import { FIELD_NAMES } from "../src/intake/extraction.ts";

test("a document's fields stay text", () => {
  const document = parseDocument('{"documentId":"DOC-1","fields":{"loan_amount":"$12,500.00"}}');
  assert.equal(document.fields.loan_amount, "$12,500.00");
});

test("the extraction has six fields", () => {
  assert.equal(FIELD_NAMES.length, 6);
});
