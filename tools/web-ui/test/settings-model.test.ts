import assert from "node:assert/strict";
import { test } from "node:test";

import { changesText, saveLines } from "../src/page/settings-model.ts";

test("one change reads in the singular", () => {
  assert.equal(changesText(1), "1 change");
});

test("more changes read in the plural", () => {
  assert.equal(changesText(3), "3 changes");
});

test("a store with no change says nothing", () => {
  assert.deepEqual(saveLines(null, null), []);
});

test("a saved store says what it saved", () => {
  assert.deepEqual(saveLines({ saved: "saved: bench.reps applies at the next bench" }, null), [
    { text: "config.toml saved: bench.reps applies at the next bench", failed: false },
  ]);
});

test("a store that failed says which, and the other its own result", () => {
  assert.deepEqual(saveLines({ error: "bench.reps: expected a positive integer" }, { saved: "saved in preferences.json" }), [
    { text: "config.toml not saved: bench.reps: expected a positive integer", failed: true },
    { text: "preferences saved in preferences.json", failed: false },
  ]);
});

test("the other way round, the preferences say they failed", () => {
  assert.deepEqual(saveLines({ saved: "unchanged" }, { error: "no room" }), [
    { text: "config.toml unchanged", failed: false },
    { text: "preferences not saved: no room", failed: true },
  ]);
});
