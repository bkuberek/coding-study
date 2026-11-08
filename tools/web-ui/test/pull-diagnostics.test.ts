import assert from "node:assert/strict";
import { test } from "node:test";

import { pullParams, pulledItems, pullsDiagnostics, retriggers } from "../src/code-intelligence/pull.ts";

const URI = "file:///ws/rust/practice/two_sum.rs";
const ITEM = { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, message: "unused variable" };

test("a server that declares a diagnostic provider is asked for diagnostics", () => {
  assert.equal(pullsDiagnostics({ diagnosticProvider: { interFileDependencies: true, workspaceDiagnostics: false } }), true);
});

test("a server that only publishes is not asked", () => {
  assert.deepEqual([pullsDiagnostics({}), pullsDiagnostics(null)], [false, false]);
});

test("the request names the file and the provider's identifier", () => {
  assert.deepEqual(pullParams(URI, { identifier: "rust-analyzer" }), { textDocument: { uri: URI }, identifier: "rust-analyzer" });
});

test("a provider without an identifier is asked for the file alone", () => {
  assert.deepEqual(pullParams(URI, true), { textDocument: { uri: URI } });
});

test("a full report's items are the file's diagnostics", () => {
  assert.deepEqual(pulledItems({ kind: "full", items: [ITEM] }), [ITEM]);
});

test("an unchanged report, or no report, changes nothing", () => {
  assert.deepEqual([pulledItems({ kind: "unchanged", resultId: "1" }), pulledItems(null), pulledItems({ kind: "full" })], [null, null, null]);
});

test("a request the server cancelled asking to be asked again is retried", () => {
  assert.equal(retriggers({ code: -32802, message: "server cancelled the request", data: { retriggerRequest: true } }), true);
});

test("any other failure is not retried", () => {
  assert.deepEqual([retriggers({ code: -32802, data: { retriggerRequest: false } }), retriggers(new Error("Request timed out"))], [false, false]);
});
