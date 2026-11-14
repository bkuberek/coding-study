// Tests of the HTTP plumbing, which every route relies on.

import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError } from "../src/errors.ts";
import { stableStringify } from "../src/http/json.ts";
import { Router } from "../src/http/router.ts";

test("stableStringify sorts keys at every depth and keeps array order", () => {
  const value = { b: 1, a: [{ d: 2, c: 3 }, null] };
  assert.equal(stableStringify(value), '{"a":[{"c":3,"d":2},null],"b":1}');
});

test("the router passes path parameters and query values as decoded strings", () => {
  const router = new Router();
  router.add("GET", "/things/:id", (context) => ({
    status: 200,
    body: { id: context.params.id, count: context.query.get("count") },
  }));
  const response = router.dispatch("GET", "/things/a%20b?count=10", "");
  assert.deepEqual(response.body, { id: "a b", count: "10" });
});

test("the router tells an unknown path from a wrong method", () => {
  const router = new Router();
  router.add("GET", "/things", () => ({ status: 200, body: {} }));
  assert.throws(
    () => router.dispatch("GET", "/nope", ""),
    (error) => error instanceof ApiError && error.status === 404,
  );
  assert.throws(
    () => router.dispatch("DELETE", "/things", ""),
    (error) => error instanceof ApiError && error.status === 405,
  );
});
