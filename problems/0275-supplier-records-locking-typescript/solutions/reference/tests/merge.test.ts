// Every way through the merge decision, without a request.

import assert from "node:assert/strict";
import { test } from "node:test";

import { decideMerge } from "../src/model/merge.ts";
import type { Supplier } from "../src/model/supplier.ts";

const CURRENT: Supplier = {
  id: "S-1",
  name: "Placeholder Parts",
  contactEmail: "orders@parts.example",
  notes: "",
  minOrderCents: 1000,
  maxOrderCents: 50000,
  status: "active",
  version: 3,
};
const notesChangedAtThree = (field: string) => (field === "notes" ? 3 : 1);

test("at the current version, only the result's rules matter", () => {
  assert.equal(decideMerge(CURRENT, 3, { status: "paused" }, notesChangedAtThree).kind, "apply");
  assert.equal(decideMerge(CURRENT, 3, { maxOrderCents: 1 }, notesChangedAtThree).kind, "invalid");
});

test("a stale change merges when nobody touched its field", () => {
  assert.equal(decideMerge(CURRENT, 1, { name: "New" }, notesChangedAtThree).kind, "apply");
});

test("a stale change conflicts on a field changed since it read", () => {
  assert.deepEqual(decideMerge(CURRENT, 2, { notes: "x", name: "New" }, notesChangedAtThree), {
    kind: "conflict",
    conflicts: ["notes"],
  });
});

test("a field changed at the version it read is not a conflict", () => {
  assert.equal(decideMerge(CURRENT, 3, { notes: "x" }, notesChangedAtThree).kind, "apply");
});

test("status never merges", () => {
  assert.deepEqual(decideMerge(CURRENT, 2, { status: "paused" }, notesChangedAtThree), {
    kind: "conflict",
    conflicts: ["status"],
  });
});

test("a merged result that breaks a rule across fields is a conflict", () => {
  assert.deepEqual(decideMerge(CURRENT, 1, { maxOrderCents: 1 }, notesChangedAtThree), {
    kind: "conflict",
    conflicts: ["maxOrderCents", "minOrderCents"],
  });
});

test("a value already there is no change at all", () => {
  assert.equal(decideMerge(CURRENT, 1, { notes: "", status: "active" }, notesChangedAtThree).kind, "nothing");
});

test("a version from the future conflicts on everything it changes", () => {
  assert.deepEqual(decideMerge(CURRENT, 9, { notes: "x" }, () => 1), {
    kind: "conflict",
    conflicts: ["notes"],
  });
});
