import assert from "node:assert/strict";
import { test } from "node:test";

import { isOpen } from "../src/accounts.ts";

test("an account with a balance is open", () => {
  assert.equal(isOpen(new Map([["ivy", 0]]), "ivy"), true);
});
