import assert from "node:assert/strict";
import { test } from "node:test";

import { autocompleteApplies } from "../src/page/preferences.ts";

test("autocomplete applies only while both preferences are on", () => {
  assert.equal(autocompleteApplies({ code_intelligence: true, autocomplete: true }), true);
});

test("autocomplete does not apply while code intelligence is off, whatever its stored value", () => {
  assert.equal(autocompleteApplies({ code_intelligence: false, autocomplete: true }), false);
});

test("autocomplete does not apply while it is off, with code intelligence on", () => {
  assert.equal(autocompleteApplies({ code_intelligence: true, autocomplete: false }), false);
});

test("autocomplete does not apply at the defaults", () => {
  assert.equal(autocompleteApplies({ code_intelligence: false, autocomplete: false }), false);
});
