// Tests of the routing, which every feature relies on.

import assert from "node:assert/strict";
import { test } from "node:test";

import { canonicalJson } from "../src/shared/json.ts";
import { HttpProblem } from "../src/shared/problems.ts";
import { dispatch } from "../src/shared/routing.ts";
import type { Route } from "../src/shared/routing.ts";

const ECHO: Route = {
  method: "GET",
  pattern: "/things/:id",
  handle: (request) => ({
    status: 200,
    body: {
      id: request.params.id,
      count: request.query.get("count"),
      tag: request.headers.get("x-tag"),
    },
  }),
};

test("a handler gets decoded parameters, text query values and lower-case header names", () => {
  const raw = { method: "GET", path: "/things/a%20b?count=10", headers: ["X-Tag:  blue "], body: "" };
  assert.deepEqual(dispatch([ECHO], raw).body, { id: "a b", count: "10", tag: "blue" });
});

test("an unknown path and a wrong method are different failures", () => {
  const unknown = { method: "GET", path: "/nope", headers: [], body: "" };
  const wrong = { method: "DELETE", path: "/things/1", headers: [], body: "" };
  assert.throws(
    () => dispatch([ECHO], unknown),
    (error) => error instanceof HttpProblem && error.status === 404,
  );
  assert.throws(
    () => dispatch([ECHO], wrong),
    (error) => error instanceof HttpProblem && error.status === 405,
  );
});

test("canonicalJson gives one text for one value", () => {
  assert.equal(canonicalJson({ b: 1, a: { d: 2, c: 3 } }), canonicalJson({ a: { c: 3, d: 2 }, b: 1 }));
});
