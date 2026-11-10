import assert from "node:assert/strict";
import { test } from "node:test";

import { lifetimeOf } from "../src/cacheControl.ts";

test("max-age is how long a price is fresh", () => {
  assert.deepEqual(lifetimeOf("public, max-age=60"), { freshS: 60, staleS: 0 });
});

test("a price with no Cache-Control is fresh for 30 s", () => {
  assert.deepEqual(lifetimeOf(null), { freshS: 30, staleS: 0 });
});

test("no-store keeps nothing", () => {
  assert.equal(lifetimeOf("no-store"), null);
});

test("max-age=0 keeps nothing", () => {
  assert.equal(lifetimeOf("max-age=0"), null);
});

test("stale-while-revalidate is how long a price may be shown after", () => {
  assert.deepEqual(lifetimeOf("Max-Age=1,stale-while-revalidate=30"), { freshS: 1, staleS: 30 });
});

test("a max-age that is no whole number is no max-age", () => {
  assert.deepEqual(lifetimeOf("max-age=1.5"), { freshS: 30, staleS: 0 });
});
