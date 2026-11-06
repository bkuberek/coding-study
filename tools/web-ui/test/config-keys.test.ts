import assert from "node:assert/strict";
import { test } from "node:test";

import { changedKeys, type ConfigKey, shownValue, tablesOf, typedValue } from "../src/page/config-keys.ts";

function key(fields: Partial<ConfigKey>): ConfigKey {
  return {
    name: "bench.reps",
    kind: "integer",
    value: 7,
    default: 7,
    set: false,
    help: "",
    applies: "",
    choices: [],
    example: null,
    reserved: false,
    ...fields,
  };
}

test("the keys group by their table, the top-level ones first", () => {
  const keys = [key({ name: "default_lang" }), key({ name: "bench.reps" }), key({ name: "bench.memory" })];
  assert.deepEqual(
    tablesOf(keys).map(([table, members]) => [table, members.map((member) => member.name)]),
    [
      ["", ["default_lang"]],
      ["bench", ["bench.reps", "bench.memory"]],
    ],
  );
});

test("an integer field reads as a number", () => {
  assert.equal(typedValue(key({}), " 12 "), 12);
});

test("an integer field holding words stays text, for the server to refuse by name", () => {
  assert.equal(typedValue(key({}), "many"), "many");
});

test("an empty field is null, which returns the key to its default", () => {
  assert.equal(typedValue(key({ kind: "text" }), "  "), null);
});

test("a text field reads as text, also when it looks like a number", () => {
  assert.equal(typedValue(key({ kind: "text" }), " 15 "), "15");
});

test("a value is shown as the file would hold it", () => {
  assert.deepEqual(
    [true, 7, "go", ["dsa", "lld"], null].map(shownValue),
    ["true", "7", "go", "dsa, lld", "unset"],
  );
});

test("only the keys whose field differs from the value in force change", () => {
  const same = key({ name: "bench.reps" });
  const other = key({ name: "bench.memory", kind: "boolean", value: true });
  assert.deepEqual(
    changedKeys([
      [same, 7],
      [other, false],
    ]),
    { "bench.memory": false },
  );
});

test("a list that holds the same choices has not changed", () => {
  const tracks = key({ name: "next.tracks", kind: "choices", value: ["dsa", "lld"] });
  assert.deepEqual(changedKeys([[tracks, ["dsa", "lld"]]]), {});
});

test("a reserved key never changes", () => {
  const reserved = key({ name: "done.auto_commit", kind: "boolean", value: false, reserved: true });
  assert.deepEqual(changedKeys([[reserved, true]]), {});
});
