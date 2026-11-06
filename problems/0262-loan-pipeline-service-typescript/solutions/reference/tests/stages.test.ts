// The state machine as a table: every pair of stages, so a wrong entry cannot hide.

import assert from "node:assert/strict";
import { test } from "node:test";

import { STAGES, canMove, isTerminal } from "../src/domain/stages.ts";

const LEGAL = new Set([
  "submitted>review",
  "submitted>withdrawn",
  "review>approved",
  "review>declined",
  "review>withdrawn",
  "approved>funded",
  "approved>withdrawn",
]);

test("exactly the listed moves are legal", () => {
  for (const from of STAGES) {
    for (const to of STAGES) {
      assert.equal(canMove(from, to), LEGAL.has(`${from}>${to}`), `${from} to ${to}`);
    }
  }
});

test("funded, declined and withdrawn are terminal", () => {
  assert.deepEqual(STAGES.filter(isTerminal), ["declined", "funded", "withdrawn"]);
});
