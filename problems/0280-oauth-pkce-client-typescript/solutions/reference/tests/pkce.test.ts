import assert from "node:assert/strict";
import { test } from "node:test";

import { challengeOf, randomValue } from "../src/pkce.ts";

test("the S256 challenge of RFC 7636's example verifier", () => {
  assert.equal(
    challengeOf("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
    "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
  );
});

test("a random value is a verifier the provider accepts: 43 base64url characters", () => {
  assert.match(randomValue(), /^[A-Za-z0-9_-]{43}$/);
});

test("two random values differ", () => {
  assert.notEqual(randomValue(), randomValue());
});
