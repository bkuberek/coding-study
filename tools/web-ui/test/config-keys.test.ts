import assert from "node:assert/strict";
import { test } from "node:test";

import { changedKeys, type ConfigKey, shownValue, sectionsOf, typedValue } from "../src/page/config-keys.ts";

function key(fields: Partial<ConfigKey>): ConfigKey {
  return {
    name: "bench.reps",
    label: "Repetitions per size",
    section: "benchmarks",
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

test("the keys group by their section, each where it first shows, whatever their table", () => {
  const keys = [
    key({ name: "default_lang", section: "general" }),
    key({ name: "bench.reps" }),
    key({ name: "done.auto_commit", section: "general" }),
  ];
  assert.deepEqual(
    sectionsOf(keys).map(([section, members]) => [section, members.map((member) => member.name)]),
    [
      ["general", ["default_lang", "done.auto_commit"]],
      ["benchmarks", ["bench.reps"]],
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

test("only the keys whose field differs from how it was drawn change", () => {
  const same = key({ name: "bench.reps" });
  const other = key({ name: "bench.memory", kind: "boolean", value: true });
  assert.deepEqual(
    changedKeys([
      [same, 7, 7],
      [other, false, true],
    ]),
    { "bench.memory": false },
  );
});

test("a list in another order than the file's is no change", () => {
  const tracks = key({ name: "next.tracks", kind: "choices", value: ["lld", "dsa"] });
  assert.deepEqual(changedKeys([[tracks, ["dsa", "lld"], ["dsa", "lld"]]]), {});
});

test("a field changed back is no change", () => {
  assert.deepEqual(changedKeys([[key({}), 7, 7]]), {});
});

test("a reserved key never changes", () => {
  const reserved = key({ name: "done.auto_commit", kind: "boolean", value: false, reserved: true });
  assert.deepEqual(changedKeys([[reserved, true, false]]), {});
});
